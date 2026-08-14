"""Deck integrity, tested against two real decks on this machine.

``deck_stock_sky130.lvs`` is the PDK's own runset: it calls ``compare`` and
does ``exit(1)`` on mismatch.

``deck_unconditional_pass.lvs`` is a real runset from a completed signoff. Its
comparison section reads, verbatim:

    # KLayout's compare returns false here strictly due to top-level pin
    # mismatches (VDD/VSS global nets vs explicit pins).
    logger.info('INFO : Congratulations! Netlists match.')
    logger.info('INFO : (17,018 devices and nets verified successfully)')

There is no ``compare`` call gating those lines and the device count is a
literal. Any result_check that greps the log for "Netlists match" passes that
deck forever. These tests exist so the orchestrator cannot.
"""

from __future__ import annotations

from pathlib import Path

from rtl2gdsagi.checks.deck_guard import audit_deck

FIX = Path(__file__).parent / "fixtures" / "klayout"


def test_stock_pdk_deck_has_a_reachable_looking_failure_path():
    """The lexical signals, which are defence in depth and not trust itself.

    `trustworthy` now requires the deck's content hash to be on the approved
    list (see test_only_an_approved_deck_identity_is_trusted). These three
    flags remain useful evidence, but on their own they can be satisfied by a
    deck whose failure branch is wrapped in `if false`.
    """
    a = audit_deck(FIX / "deck_stock_sky130.lvs", kind="lvs")
    assert a.has_compare is True
    assert a.has_fail_branch is True
    assert a.has_hard_exit is True


def test_real_hardcoded_pass_deck_is_rejected():
    """The headline case: a deck that prints a verdict it never computed."""
    a = audit_deck(FIX / "deck_unconditional_pass.lvs", kind="lvs")
    assert a.trustworthy is False
    assert a.unconditional_pass_lines, "the verdict line was not located"
    joined = " ".join(a.problems)
    assert "compare" in joined or "unconditional" in joined


def test_the_two_real_decks_are_distinguished():
    """The guard must separate these two, not flag or clear both."""
    stock = audit_deck(FIX / "deck_stock_sky130.lvs", kind="lvs")
    fake = audit_deck(FIX / "deck_unconditional_pass.lvs", kind="lvs")
    assert stock.has_compare and not fake.has_compare
    assert bool(fake.unconditional_pass_lines)
    # The stock fixture is a byte-identical copy of the PDK's own runset, so it
    # is on the approved list; the hardcoded-pass deck is not, and additionally
    # fails the lexical guard.
    assert stock.trustworthy is True
    assert stock.approved_as
    assert fake.trustworthy is False


def test_only_an_approved_deck_identity_is_trusted(tmp_path):
    """A deck with every lexical signal is still refused if unrecognised.

    The counter-example that motivates this is in APPROVED_DECKS: wrapping a
    correct failure branch in `if false` satisfies every token search while
    making the failure unreachable. Reachability is a property of behaviour,
    so trust is pinned to bytes that were actually validated.
    """
    from rtl2gdsagi.checks.deck_guard import APPROVED_DECKS, deck_sha256

    p = tmp_path / "deck.lvs"
    p.write_text(
        "if ! compare\n  logger.error('ERROR : Netlists do not match')\n"
        "  exit(1)\nelse\n  logger.info('INFO : Netlists match.')\nend\n",
        encoding="utf-8",
    )
    audit = audit_deck(p, kind="lvs")
    assert audit.trustworthy is False
    assert "not an approved deck" in audit.problems[0]
    assert audit.has_compare and audit.has_fail_branch and audit.has_hard_exit

    # Approving that exact content makes it authoritative, and nothing else.
    digest = deck_sha256(p)
    APPROVED_DECKS[digest] = "test deck"
    try:
        assert audit_deck(p, kind="lvs").trustworthy is True
        # A single byte of drift revokes it.
        p.write_text(p.read_text() + "\n# one byte of drift\n", encoding="utf-8")
        assert audit_deck(p, kind="lvs").trustworthy is False
    finally:
        APPROVED_DECKS.pop(digest, None)


def test_an_unreachable_failure_branch_is_refused(tmp_path):
    """Codex's exact counter-example."""
    p = tmp_path / "unreachable.lvs"
    p.write_text(
        "if false\n  if ! compare\n    logger.error(\"Netlists don't match\")\n"
        "    exit(1)\n  end\nend\nlogger.info(\"Netlists match\")\n",
        encoding="utf-8",
    )
    assert audit_deck(p, kind="lvs").trustworthy is False


def test_missing_deck_is_not_trustworthy(tmp_path):
    a = audit_deck(tmp_path / "absent.lvs", kind="lvs")
    assert a.trustworthy is False


def test_commented_out_verdict_does_not_count_as_a_failure_branch(tmp_path):
    """A failure path that only exists in a comment is not a failure path."""
    p = tmp_path / "deck.lvs"
    p.write_text(
        "compare\n"
        "# if ! compare\n"
        "#   logger.error('ERROR : Netlists don\\'t match')\n"
        "#   exit(1)\n"
        "logger.info('INFO : Congratulations! Netlists match.')\n",
        encoding="utf-8",
    )
    a = audit_deck(p, kind="lvs")
    assert a.has_compare is True
    assert a.has_fail_branch is False
    assert a.trustworthy is False


