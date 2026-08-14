"""F3/F5: the model must not be shown knobs that do nothing.

The clean-room audit found four agent-writable fields with no rendered effect
(`routing.global_effort`, `floorplan.io_mode`, `placement.effort`,
`placement.max_displacement_um`) and one that moves an *acceptance threshold*
rather than the implementation (`placement.congestion_overflow_limit`).

Exposing a no-op invites a proposal that changes nothing and then grading the
model on the result. Exposing an acceptance threshold is worse: it lets the
subject move the bar instead of clearing it.

They are frozen (`agent_writable=False`), not deleted, so the fields keep
working for operators while staying out of the model's action space.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rtl2gdsagi.ir import SCHEMA, writable_fields
from rtl2gdsagi.safety import authorized_action_space
from rtl2gdsagi.taxonomy import FailureClass

RENDER = (Path(__file__).resolve().parent.parent / "src" / "rtl2gdsagi"
          / "render.py").read_text()

FROZEN_FOR_FIRST_RUN = [
    ("routing", "global_effort"),
    ("floorplan", "io_mode"),
    ("placement", "effort"),
    ("placement", "max_displacement_um"),
    ("placement", "congestion_overflow_limit"),
]


@pytest.mark.parametrize("section,field", FROZEN_FOR_FIRST_RUN)
def test_frozen_fields_are_not_agent_writable(section, field):
    assert field not in writable_fields(section), (
        f"{section}.{field} is still advertised to the model"
    )


@pytest.mark.parametrize("section,field", FROZEN_FOR_FIRST_RUN)
def test_frozen_fields_still_exist_for_operators(section, field):
    assert any(f.name == field for f in SCHEMA[section]), (
        f"{section}.{field} was deleted; it should be frozen, not removed"
    )


def test_every_field_offered_for_a_routing_failure_is_actually_rendered():
    """The whole point: no no-ops in the first experiment's action space."""
    space = authorized_action_space(FailureClass.ROUTING)
    assert space, "a routing failure must have some authorized surface"
    for section, fields in space.items():
        for field in fields:
            assert re.search(rf"""['"\[]{re.escape(field)}['"\]]""", RENDER), (
                f"{section}.{field} is offered to the model but never "
                "consumed by the renderer"
            )


def test_the_surface_is_not_narrowed_to_the_known_answer():
    """Blindness: several legitimate knobs, not just `droute_iters`."""
    space = authorized_action_space(FailureClass.ROUTING)
    routing = space.get("routing", {})
    assert "droute_iters" in routing
    assert len(routing) >= 3, (
        "narrowing the surface to the known remedy would overfit the model "
        f"to the answer; got {sorted(routing)}"
    )
    assert len(space) >= 2, "cross-stage knobs remain legitimately authorized"


def test_no_verification_intent_is_ever_offered():
    for failure in FailureClass:
        space = authorized_action_space(failure)
        assert "sdc" not in space and "sta" not in space
        assert "extraction" not in space
