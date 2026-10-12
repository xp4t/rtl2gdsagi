"""The actual native input arguments must identify the selected candidate."""
from types import SimpleNamespace
from pathlib import Path
import pytest
from rtl2gdsagi.artifacts import Artifact,ArtifactLedger
from rtl2gdsagi.checks.tools import ToolRun
from rtl2gdsagi.runner import Orchestrator

@pytest.fixture
def native_context(tmp_path):
    gds=tmp_path/"candidate.gds";gds.write_bytes(b"selected layout")
    deck=tmp_path/"approved.drc";deck.write_text("verified runset")
    orch=object.__new__(Orchestrator);orch.ledger=ArtifactLedger()
    orch.ledger.register("final_gds",gds,stage="gdsout")
    orch.cfg=SimpleNamespace(pdk=SimpleNamespace(drc_deck_path=deck,lvs_deck_path=deck))
    ctx=SimpleNamespace(work_dir=tmp_path)
    return orch,ctx,gds,deck

def invocation(gds,deck,extra=()):
    return ToolRun(argv=["klayout","-r",str(deck),"-rd",f"input={gds}",*extra],
                   returncode=0,stdout="zero markers",stderr="")

def test_stale_native_input_blocks_even_with_zero_exit_and_clean_report(native_context,tmp_path):
    orch,ctx,gds,deck=native_context
    stale=tmp_path/"stale.gds";stale.write_bytes(b"another clean layout")
    reason=orch._klayout_invocation_problem(invocation(stale,deck),ctx,"drc")
    assert reason and "consumed input" in reason

def test_identity_is_content_bound_for_identical_copies(native_context,tmp_path):
    orch,ctx,gds,deck=native_context
    copy=tmp_path/"copy.gds";copy.write_bytes(gds.read_bytes())
    assert orch._klayout_invocation_problem(invocation(copy,deck),ctx,"drc") is None

def test_duplicate_input_arguments_cannot_hide_a_stale_selection(native_context):
    orch,ctx,gds,deck=native_context
    reason=orch._klayout_invocation_problem(invocation(gds,deck,["-rd",f"input={gds}"]),ctx,"drc")
    assert reason and "exactly one input" in reason

def test_native_runset_substitution_is_detected(native_context,tmp_path):
    orch,ctx,gds,deck=native_context
    other=tmp_path/"no_compare.rb";other.write_text('puts "Netlists match"')
    reason=orch._klayout_invocation_problem(invocation(gds,other),ctx,"lvs")
    assert reason and "consumed deck" in reason

def test_directory_artifacts_rehash_contents(tmp_path):
    rtl=tmp_path/"rtl";rtl.mkdir();source=rtl/"design.v";source.write_text("assign y=a;")
    artifact=Artifact.capture("rtl_dir",rtl,"prepare",allow_dir=True)
    assert artifact.is_dir and artifact.unchanged()
    source.write_text("assign y=b;")
    assert not artifact.unchanged()
