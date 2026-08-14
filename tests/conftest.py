"""Shared fixtures: a synthetic design and a scriptable fake toolchain.

The whole state machine runs against these, so retry / rollback / escalation
behaviour is tested deterministically without invoking a real EDA tool.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rtl2gdsagi.tools.invoker import DEFAULT_OPENLANE_IMAGE
from rtl2gdsagi.checks.tools import (
    SPEF_ANNOTATED_MARKER,
    SPEF_COVERAGE_MARKER,
    ToolRun,
)
from rtl2gdsagi.config import RunConfig
from rtl2gdsagi.pdk import PDKConfig
from rtl2gdsagi.stages import StageId, Tool

FIX = Path(__file__).parent / "fixtures" / "klayout"


def make_gds(path: Path, top: str, *, cells: tuple[str, ...] = ("INVX1",),
             dangling: tuple[str, ...] = ()) -> Path:
    """Write a structurally valid minimal GDSII.

    ``dangling`` adds SREFs to cells that are deliberately *not* defined in the
    file, which is what a pre-merge layout looks like: it references standard
    cells that still live in the PDK GDS.
    """
    import struct

    def rec(rectype: int, datatype: int, payload: bytes = b"") -> bytes:
        if len(payload) % 2:
            payload += b"\x00"
        return struct.pack(">HBB", len(payload) + 4, rectype, datatype) + payload

    def ascii_(s: str) -> bytes:
        b = s.encode("ascii")
        return b + (b"\x00" if len(b) % 2 else b"")

    stamp = struct.pack(">12h", *([0] * 12))
    out = [rec(0x00, 0x02, struct.pack(">h", 600)),      # HEADER
           rec(0x01, 0x02, stamp),                        # BGNLIB
           rec(0x02, 0x06, ascii_("LIB")),                # LIBNAME
           rec(0x03, 0x05, b"\x00" * 16)]                 # UNITS

    def boundary() -> list[bytes]:
        xy = struct.pack(">10i", 0, 0, 100, 0, 100, 100, 0, 100, 0, 0)
        return [rec(0x08, 0x00), rec(0x0D, 0x02, struct.pack(">h", 68)),
                rec(0x0E, 0x02, struct.pack(">h", 20)), rec(0x10, 0x03, xy),
                rec(0x11, 0x00)]

    for name in cells:                                    # leaf cells
        out += [rec(0x05, 0x02, stamp), rec(0x06, 0x06, ascii_(name))]
        out += boundary()
        out.append(rec(0x07, 0x00))

    out += [rec(0x05, 0x02, stamp), rec(0x06, 0x06, ascii_(top))]  # top cell
    out += boundary()
    for ref in tuple(cells) + tuple(dangling):            # SREFs
        out += [rec(0x0A, 0x00), rec(0x12, 0x06, ascii_(ref)),
                rec(0x10, 0x03, struct.pack(">2i", 0, 0)), rec(0x11, 0x00)]
    out += [rec(0x07, 0x00), rec(0x04, 0x00)]             # ENDSTR, ENDLIB

    path.write_bytes(b"".join(out))
    return path


def _fresh_copy(src: Path, dst: Path, top: str = "") -> None:
    """Copy a report fixture as a real tool would have written it.

    Two adjustments, both because the orchestrator checks things a naive
    harness would violate:

    * no mtime preservation -- ``shutil.copy2`` keeps the fixture's original
      timestamp, which makes the report look older than the GDS it describes,
      and the orchestrator correctly rejects that as stale;
    * retarget the top cell -- these fixtures came from a design whose top is
      ``top``, and a report naming a different cell than the design under test
      is correctly rejected as describing another layout.
    """
    data = src.read_bytes()
    if top:
        data = data.replace(b"<top-cell>top</top-cell>",
                            f"<top-cell>{top}</top-cell>".encode())
        data = data.replace(b"\n W(top)\n", f"\n W({top})\n".encode())
    dst.write_bytes(data)

def _approve_fixture_decks(tech: Path) -> None:
    """Register the synthetic decks + their rule inventory for the fake PDK."""
    import xml.etree.ElementTree as ET

    from rtl2gdsagi.checks import klayout_drc
    from rtl2gdsagi.checks.deck_guard import APPROVED_DECKS, deck_sha256

    drc = tech / "klayout" / "drc" / "sky130A_mr.drc"
    lvs = tech / "klayout" / "lvs" / "sky130.lvs"
    for deck, label in ((drc, "fixture DRC deck"), (lvs, "fixture LVS deck")):
        if deck.is_file():
            APPROVED_DECKS.setdefault(deck_sha256(deck), label)

    # The mock DRC report is a real captured KLayout report with 73 categories.
    report = FIX / "drc_clean_0.lyrdb"
    if drc.is_file() and report.is_file():
        names = list(klayout_drc._iter_declared(
            ET.parse(report).getroot().find("categories")))
        klayout_drc.APPROVED_INVENTORIES.setdefault(
            deck_sha256(drc),
            (len(names), klayout_drc.inventory_digest(names), "fixture DRC deck"),
        )


RTL = """\
`timescale 1ns/1ps
module widget (
    input  wire       i_clk,
    input  wire       i_rst_n,
    input  wire [7:0] i_data,
    output reg  [7:0] o_data
);
    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) o_data <= 8'h00;
        else          o_data <= i_data + 8'h01;
    end
endmodule
"""


@pytest.fixture
def design(tmp_path: Path) -> Path:
    d = tmp_path / "rtl"
    d.mkdir()
    (d / "widget.v").write_text(RTL, encoding="utf-8")
    # A self-checking testbench, so the simulation gate has something to run.
    # Without one the runner skips sim, and a suite whose happy path skips
    # simulation cannot notice that a skipped gate still certifies.
    (d / "widget_tb.v").write_text(
        "module widget_tb;\n"
        "  initial begin\n"
        "    if (1'b1) $display(\"TEST PASSED\");\n"
        "    else $display(\"TEST FAILED\");\n"
        "    $finish;\n"
        "  end\n"
        "endmodule\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def fake_pdk(tmp_path: Path) -> PDKConfig:
    """A PDK tree with real-enough files that existence checks pass."""
    root = tmp_path / "pdk" / "sky130A"
    ref = root / "libs.ref" / "sky130_fd_sc_hd"
    tech = root / "libs.tech"
    for sub in ("lib", "techlef", "lef", "gds", "verilog"):
        (ref / sub).mkdir(parents=True)
    (tech / "klayout" / "drc").mkdir(parents=True)
    (tech / "klayout" / "lvs").mkdir(parents=True)
    (tech / "netgen").mkdir(parents=True)
    (tech / "openlane").mkdir(parents=True)

    (ref / "lib" / "sky130_fd_sc_hd__tt_025C_1v80.lib").write_text("library(x){}", encoding="utf-8")
    (ref / "techlef" / "sky130_fd_sc_hd__nom.tlef").write_text("VERSION 5.7 ;", encoding="utf-8")
    # Real MACRO lines: clock_buffers() reads the LEF, and CTS refuses to run
    # without a buffer list (CTS-0055).
    (ref / "lef" / "sky130_fd_sc_hd.lef").write_text(
        "VERSION 5.7 ;\n"
        + "".join(
            f"MACRO sky130_fd_sc_hd__clkbuf_{n}\n  CLASS CORE ;\nEND "
            f"sky130_fd_sc_hd__clkbuf_{n}\n"
            for n in (1, 2, 4, 8, 16)
        )
        + "MACRO sky130_fd_sc_hd__inv_1\n  CLASS CORE ;\nEND sky130_fd_sc_hd__inv_1\n"
        + "MACRO sky130_fd_sc_hd__diode_2\n  CLASS CORE ;\nEND sky130_fd_sc_hd__diode_2\n"
        + "MACRO sky130_fd_sc_hd__tapvpwrvgnd_1\n  CLASS CORE ;\n"
          "END sky130_fd_sc_hd__tapvpwrvgnd_1\n"
        + "".join(
            f"MACRO sky130_fd_sc_hd__fill_{n}\n  CLASS CORE ;\n"
            f"END sky130_fd_sc_hd__fill_{n}\n"
            for n in (1, 2, 4, 8)
        )
        + "".join(
            f"MACRO sky130_fd_sc_hd__decap_{n}\n  CLASS CORE ;\n"
            f"END sky130_fd_sc_hd__decap_{n}\n"
            for n in (3, 6, 12)
        ),
        encoding="utf-8",
    )
    (ref / "gds" / "sky130_fd_sc_hd.gds").write_bytes(b"\x00\x06\x00\x02\x00\x07")
    (tech / "klayout" / "drc" / "sky130A_mr.drc").write_text("# drc deck", encoding="utf-8")
    (tech / "klayout" / "tech").mkdir(parents=True, exist_ok=True)
    (tech / "klayout" / "tech" / "sky130A.map").write_text(
        "li1     NET,SPNET,VIA            67  20\n"
        "li1     LEFPIN,PIN               67  16\n"
        "met1    NET,SPNET,VIA            68  20\n"
        "met2    NET,SPNET,VIA            69  20\n"
        "nwell   LEFPIN                   64  16\n",
        encoding="utf-8",
    )

    # Cell CDL for the LVS reference side. The pin ORDER here is the point:
    # it deliberately differs from any Verilog view of the same cell, which is
    # what makes positional SPICE generation get it wrong.
    (ref / "cdl").mkdir(parents=True, exist_ok=True)
    (ref / "cdl" / "sky130_fd_sc_hd.cdl").write_text(
        "\n".join(
            f".SUBCKT {name} {pins}\n"
            "MM1 Y A VGND VNB nfet_01v8 m=1 w=0.65 l=0.15\n"
            f".ENDS {name}"
            for name, pins in (
                ("sky130_fd_sc_hd__inv_1", "A VGND VNB VPB VPWR Y"),
                ("sky130_fd_sc_hd__nand2_1", "A B VGND VNB VPB VPWR Y"),
                ("sky130_fd_sc_hd__dfrtp_1", "CLK D RESET_B VGND VNB VPB VPWR Q"),
                ("sky130_fd_sc_hd__fill_1", "VGND VNB VPB VPWR"),
                ("sky130_fd_sc_hd__tapvpwrvgnd_1", "VGND VNB VPB VPWR"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    # A trustworthy LVS deck: calls compare and has a reachable failure branch.
    (tech / "klayout" / "lvs" / "sky130.lvs").write_text(
        "if ! compare\n  logger.error(\"ERROR : Netlists don't match\")\n"
        "  exit(1)\nelse\n  logger.info('INFO : Congratulations! Netlists match.')\nend\n",
        encoding="utf-8",
    )
    # Deck trust is by content identity in production (deck_guard.APPROVED_DECKS),
    # so the fixture decks must be registered explicitly, and only once every
    # deck exists. Registering here rather than shipping these hashes keeps the
    # production trust set to decks that were actually validated, and makes it
    # visible in the test tree exactly what the fake toolchain is trusted for.
    _approve_fixture_decks(tech)
    return PDKConfig.discover("sky130A", root=root)


@pytest.fixture
def cfg(design: Path, fake_pdk: PDKConfig, tmp_path: Path) -> RunConfig:
    return RunConfig(
        rtl_dir=design,
        top="widget",
        pdk=fake_pdk,
        retry_limit=3,
        run_root=tmp_path / "runs",
        mock_tools=True,
    )


# --------------------------------------------------------------------------


class FakeToolchain:
    """Produces plausible tool output and the files each stage must write.

    Reports the real pinned container image as its identity. The evidence
    contract only accepts approved tool identities, and a fake that claimed
    `container:unknown` would exercise the rejection path on every run rather
    than the path a real environment takes.

    ``fail`` maps a StageId to a list of ToolRun results used for that stage's
    first N attempts; afterwards the stage succeeds. That is how a test says
    "routing fails twice, then works".
    """

    #: Matches `Invoker.openlane_image`, which `_tool_identity` reads.
    openlane_image = DEFAULT_OPENLANE_IMAGE

    def __init__(
        self,
        orch,
        *,
        fail: dict[StageId, list[ToolRun]] | None = None,
        missing: set[Tool] | None = None,
        generation: str = "",
    ) -> None:
        self.orch = orch
        #: Distinguishes two otherwise identical mock runs as two *physical
        #: generations*. The fake is deterministic, so without this every run
        #: produces byte-identical artifacts and a hybrid-candidate test would
        #: be comparing a run against itself.
        self.generation = generation
        self.fail = {k: list(v) for k, v in (fail or {}).items()}
        self.calls: list[tuple[Tool, StageId]] = []
        self.stage_calls: dict[StageId, int] = {}
        #: Tools to report as not installed, for tests that need the skip path.
        self.missing = set(missing or ())

    #: What a simulation prints. Overridable so a test can model a testbench
    #: that runs to completion without checking anything.
    sim_stdout = "TEST PASSED\n"

    def available(self, tool: Tool) -> bool:
        # Every tool is present by default.
        #
        # This used to hardcode iverilog as missing "so the optional-skip path
        # is exercised", while the clean-run tests still asserted a clean
        # signoff -- which meant the suite's central happy-path test certified
        # a design that had never been simulated, and would not have caught a
        # regression that let automatic skips certify. Tests that want the
        # skip path now ask for it explicitly via `missing`, and assert that
        # signoff refuses.
        return tool not in self.missing

    def _stage_for(self, cwd: Path) -> StageId:
        name = cwd.name.split("_", 1)[-1]
        return StageId(name)

    def run(self, tool, argv, *, cwd, timeout_s=3600, env=None,
            log_path=None) -> ToolRun:
        sid = self._stage_for(Path(cwd))
        self.calls.append((tool, sid))
        self.stage_calls[sid] = self.stage_calls.get(sid, 0) + 1

        queued = self.fail.get(sid)
        if queued:
            return queued.pop(0)

        self._make_outputs(sid, Path(cwd))
        return ToolRun(argv=argv, returncode=0, stdout=self._stdout(sid), stderr="")

    # -- realistic artifacts -------------------------------------------------

    def _make_outputs(self, sid: StageId, cwd: Path) -> None:
        from rtl2gdsagi.stages import get_stage

        outs = self.orch._outputs_for(get_stage(sid), cwd)
        for key, path in outs.items():
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if key == "drc_report":
                _fresh_copy(FIX / "drc_clean_0.lyrdb", p, self.orch.cfg.top)
            elif key == "lvs_report":
                _fresh_copy(FIX / "lvs_match_trimmed.lvsdb", p, self.orch.cfg.top)
            elif key == "final_gds":
                # A real merged stream-out: every referenced cell is present.
                make_gds(p, self.orch.cfg.top)
            elif key.endswith("netlist"):
                # Structural Verilog, because the LVS stage converts this into
                # the SPICE reference and needs real instances to work from.
                top = self.orch.cfg.top
                p.write_text(
                    f"module {top} (i_clk, i_rst_n, i_data, o_data);\n"
                    "  input i_clk;\n  input i_rst_n;\n"
                    "  input [7:0] i_data;\n  output [7:0] o_data;\n"
                    "  sky130_fd_sc_hd__inv_1 _00_ (.A(i_data[0]), .Y(o_data[0]));\n"
                    "  sky130_fd_sc_hd__nand2_1 _01_ (.A(i_data[1]), .B(i_data[2]),\n"
                    "     .Y(o_data[1]));\n"
                    "  sky130_fd_sc_hd__dfrtp_1 _02_ (.CLK(i_clk), .D(i_data[3]),\n"
                    "     .RESET_B(i_rst_n), .Q(o_data[2]));\n"
                    "  sky130_fd_sc_hd__fill_1 FILLER_0 ();\n"
                    "  sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_0 ();\n"
                    "endmodule\n",
                    encoding="utf-8",
                )
            elif key == "pdn_def":
                # A structurally real power grid: two supplies, follow-pin
                # rails on met1, straps and a ring on met4/met5, and vias
                # tying the layers together. The placeholder this replaced
                # meant the happy path never exercised the PDN contract, and a
                # one-byte file passed the stage.
                def _net(name: str, use: str) -> str:
                    rails = "".join(
                        f"      NEW met1 480 + SHAPE FOLLOWPIN "
                        f"( 10120 {10880 + i * 5440} ) ( 38640 {10880 + i * 5440} )\n"
                        for i in range(6)
                    )
                    return (
                        f"    - {name} ( * {name} ) + USE {use}\n"
                        f"      + ROUTED met5 1600 + SHAPE STRIPE "
                        f"( 4020 12880 ) ( 44740 12880 )\n"
                        f"      NEW met4 1600 + SHAPE STRIPE "
                        f"( 12120 4780 ) ( 12120 44180 )\n"
                        f"{rails}"
                        f"      NEW met4 1600 + SHAPE RING "
                        f"( 43940 4780 ) ( 43940 44180 )\n"
                        # The full via ladder from the standard-cell rails up
                        # to the top distribution layer, which is what pdngen
                        # actually emits (`add_pdn_connect met1-met4, met4-met5`
                        # produces every intermediate transition). The immutable
                        # PDN contract requires all four per supply, so a mock
                        # with a partial ladder must fail the gate.
                        f"      NEW met1 0 + SHAPE STRIPE "
                        f"( 12120 10880 ) via2_3_1600_480_1_5_320_320\n"
                        f"      NEW met2 0 + SHAPE STRIPE "
                        f"( 12120 10880 ) via3_4_1600_480_1_4_400_400\n"
                        f"      NEW met3 0 + SHAPE STRIPE "
                        f"( 12120 10880 ) via4_5_1600_480_1_4_400_400\n"
                        f"      NEW met4 0 + SHAPE STRIPE "
                        f"( 12120 12880 ) via5_6_1600_1600_1_1_1600_1600 ;\n"
                    )
                p.write_text(
                    "VERSION 5.8 ;\n"
                    f"DESIGN {self.orch.cfg.top} ;\n"
                    "UNITS DISTANCE MICRONS 1000 ;\n"
                    "SPECIALNETS 2 ;\n"
                    + _net("VGND", "GROUND") + _net("VPWR", "POWER")
                    + "END SPECIALNETS\nEND DESIGN\n",
                    encoding="utf-8",
                )
            elif key == "spef":
                # A structurally valid SPEF for the design's nets.
                #
                # The mock previously wrote a placeholder comment, which meant
                # the happy path never exercised extraction's contract at all.
                # Real OpenRCX output names the design, declares units, and
                # carries one *D_NET per routed net -- so the fake does too,
                # keyed to the same nets the fake routed DEF declares.
                nets = self._net_names()
                # Real OpenRCX emits driver/load connections inside *CONN
                # (`*P <port> I` and `*I <inst>:<pin> I *D <cell>`). A bare
                # *CONN header describes a net that connects to nothing, and
                # the extraction gate now says so -- so the fake carries real
                # connectivity keyed to the same nets.
                body = "".join(
                    f"*D_NET *{i} 0.001\n"
                    f"*CONN\n*P {name} I\n"
                    f"*I *{i}00:A I *D sky130_fd_sc_hd__inv_1\n"
                    f"*CAP\n1 {name} 0.0005\n2 *{i}00:A 0.0005\n"
                    f"*RES\n1 {name} *{i}00:A 1.5\n*END\n"
                    for i, name in enumerate(nets, start=1)
                )
                names = "".join(f"*{i} {n}\n" for i, n in enumerate(nets, start=1))
                p.write_text(
                    '*SPEF "IEEE 1481-1998"\n'
                    f'*DESIGN "{self.orch.cfg.top}"\n'
                    "*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER []\n"
                    "*T_UNIT 1 NS\n*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*L_UNIT 1 HENRY\n\n"
                    f"*NAME_MAP\n{names}\n{body}",
                    encoding="utf-8",
                )
            elif key == "routed_def":
                nets = self._net_names()
                p.write_text(
                    "VERSION 5.8 ;\n"
                    + (f"# generation {self.generation}\n"
                       if self.generation else "")
                    + f"DESIGN {self.orch.cfg.top} ;\n"
                    "UNITS DISTANCE MICRONS 1000 ;\n"
                    f"NETS {len(nets)} ;\n"
                    + "".join(f"    - {n} ;\n" for n in nets)
                    + "END NETS\nEND DESIGN\n",
                    encoding="utf-8",
                )
            else:
                # Content must vary with the config, as a real tool's output
                # does. Byte-identical artifacts would make a re-run after a
                # config change look like a duplicate attempt to the
                # checkpoint store, which correctly refuses to repeat itself.
                p.write_text(
                    f"# {key} produced by {sid}\n"
                    f"# ir {self.orch.ir.fingerprint()}\n",
                    encoding="utf-8",
                )

    def _net_names(self) -> list[str]:
        """Signal nets the fake design has, shared by its DEF and SPEF."""
        return ["i_clk", "i_rst_n", "o_data[0]", "o_data[1]", "o_data[2]",
                "i_data[0]", "i_data[1]", "i_data[2]", "i_data[3]"]

    def _stdout(self, sid: StageId) -> str:
        if sid is StageId.SYNTHESIS:
            return (
                "=== widget ===\n   Number of cells:                 42\n"
                "   Chip area for module '\\widget': 1234.5\n"
            )
        if sid in (StageId.LEC_SYNTH, StageId.LEC_ROUTE):
            # Real EQY output shape, from a verified run of its SKY130 example.
            return ("EQY 22:42:47 [w] run: Proved equivalence of partition "
                    "'w.a' using strategy 'sat'\n"
                    "EQY 22:42:47 [w] Successfully proved equivalence of partition w.a\n"
                    "EQY 22:42:47 [w] run: Proved equivalence of partition "
                    "'w.b' using strategy 'sat'\n"
                    "EQY 22:42:47 [w] Successfully proved equivalence of partition w.b\n"
                    "EQY 22:42:47 [w] Successfully proved designs equivalent\n"
                    "EQY 22:42:47 [w] DONE (PASS, rc=0)\n")
        if sid in (StageId.STA_PRE, StageId.STA_POSTCTS, StageId.STA_SIGNOFF):
            # Signoff reads a SPEF, and the renderer emits an annotation marker
            # right after read_spef because a successful read_spef is silent.
            # Signoff additionally reports parasitic annotation. This is the
            # verbatim syntax of `report_parasitic_annotation` in the pinned
            # OpenSTA build, captured from a real reg10 run -- the gate now
            # requires it, so a mock that omits it must fail.
            marker = (
                f"{SPEF_ANNOTATED_MARKER} /run/stages/13_extraction/widget.spef\n"
                f"{SPEF_COVERAGE_MARKER}\n"
                "Found 0 unannotated drivers.\n"
                "Found 0 partially unannotated drivers.\n"
                if sid is StageId.STA_SIGNOFF else ""
            )
            return marker + (
                "=== check_setup ===\n=== setup ===\nno paths\n=== hold ===\n"
                "no paths\n=== wns/tns ===\n"
                "setup_wns 0.4200\nsetup_tns 0.0000\nhold_wns 0.1100\nhold_tns 0.0000\n"
            )
        if sid is StageId.PLACEMENT:
            return "Design area 1234.5 u^2 55.0% utilization\nTotal overflow: 0.0000\n"
        if sid is StageId.CTS:
            return "Worst clock skew: 0.05\n"
        if sid is StageId.ROUTING:
            # Captured shape from a real OpenROAD run: an '=' rather than a
            # colon, one count per optimisation iteration, and an explicit
            # completion line. The mock used to emit a colon form the tool
            # never produces, which is how a parser that matched nothing at
            # all still looked correct in the test suite.
            return (
                "[INFO DRT-0195] Start 1st optimization iteration.\n"
                "[INFO DRT-0199]   Number of violations = 12.\n"
                "[INFO DRT-0195] Start 2nd optimization iteration.\n"
                "[INFO DRT-0199]   Number of violations = 0.\n"
                "[INFO DRT-0198] Complete detail routing.\n"
                "Total number of vias = 7353.\n"
            )
        if sid is StageId.ANTENNA:
            # The exact strings OpenROAD emits, captured from a real run.
            return ("[INFO ANT-0002] Found 0 net violations.\n"
                    "[INFO ANT-0001] Found 0 pin violations.\n")
        if sid is StageId.LVS:
            return "INFO : Congratulations! Netlists match.\n"
        if sid is StageId.SIM:
            # Self-checking result, matching what the bundled testbench prints.
            return self.sim_stdout
        if sid is StageId.LINT:
            return ""
        return f"{sid} ok\n"


@pytest.fixture
def toolchain():
    return FakeToolchain
