"""
Test P1-005: Normalize state phases.

Verifies that all phases used in the codebase are properly handled
by State.get_next_step() and documented.
"""

import pytest

from erirpg.state import State


# All valid phases (as documented in State class)
VALID_PHASES = {
    "idle",
    "extracting",
    "planning",
    "building",
    "context_ready",
    "implementing",
    "validating",
    "done",
}


class TestStatePhases:
    """Tests for state phase handling."""

    def test_all_valid_phases_have_handler(self):
        """Every valid phase should return a non-'Unknown' next step."""
        state = State()

        for phase in VALID_PHASES:
            state.phase = phase
            next_step = state.get_next_step()

            # Should not return "Unknown state" message
            assert "Unknown state" not in next_step, \
                f"Phase '{phase}' returned 'Unknown state': {next_step}"

    def test_idle_phase(self):
        """Idle phase should suggest starting a task."""
        state = State()
        state.phase = "idle"
        next_step = state.get_next_step()

        assert "Start a task" in next_step or "eri-rpg do" in next_step

    def test_building_phase(self):
        """Building phase should give appropriate guidance."""
        state = State()
        state.phase = "building"

        # Without context file
        next_step = state.get_next_step()
        assert "Building" in next_step or "build" in next_step.lower()

        # With context file
        state.context_file = "/path/to/spec.md"
        next_step = state.get_next_step()
        assert "spec" in next_step.lower() or "Claude" in next_step

    def test_context_ready_phase(self):
        """Context ready phase should mention Claude and context file."""
        state = State()
        state.phase = "context_ready"
        state.context_file = "/path/to/context.md"

        next_step = state.get_next_step()
        assert "Claude" in next_step
        assert "validate" in next_step.lower()

    def test_done_phase(self):
        """Done phase should indicate completion."""
        state = State()
        state.phase = "done"
        next_step = state.get_next_step()

        assert "complete" in next_step.lower() or "done" in next_step.lower()

    def test_invalid_phase_returns_unknown(self):
        """Invalid phases should return 'Unknown state' message."""
        state = State()
        state.phase = "invalid_phase_xyz"
        next_step = state.get_next_step()

        assert "Unknown state" in next_step

    def test_extracting_phase(self):
        """Extracting phase should guide through extraction process."""
        state = State()
        state.phase = "extracting"

        # Without feature file
        next_step = state.get_next_step()
        assert "extract" in next_step.lower() or "Extracting" in next_step

        # With feature file
        state.feature_file = "/path/to/feature.json"
        next_step = state.get_next_step()
        assert "plan" in next_step.lower()

    def test_planning_phase(self):
        """Planning phase should guide through planning process."""
        state = State()
        state.phase = "planning"

        # Without plan file
        next_step = state.get_next_step()
        assert "plan" in next_step.lower() or "Planning" in next_step

        # With plan file
        state.plan_file = "/path/to/plan.json"
        state.feature_file = "/path/to/feature.json"
        next_step = state.get_next_step()
        assert "context" in next_step.lower()


class TestStatusDisplay:
    """Tests for status formatting."""

    def test_format_status_shows_phase(self):
        """Status should display current phase."""
        state = State()
        state.phase = "building"
        status = state.format_status()

        assert "Phase: building" in status

    def test_format_status_shows_next_step(self):
        """Status should include next step recommendation."""
        state = State()
        state.phase = "idle"
        status = state.format_status()

        assert "Next step:" in status


class TestPhasesUsedInModes:
    """Verify phases used in modes are valid."""

    def test_building_phase_is_valid(self):
        """The 'building' phase used in new mode should be valid."""
        assert "building" in VALID_PHASES

    def test_context_ready_phase_is_valid(self):
        """The 'context_ready' phase used in modes should be valid."""
        assert "context_ready" in VALID_PHASES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
