"""
Tests for the agent module.
"""

import os
import pytest
from datetime import datetime

from erirpg.agent import Agent, Spec, Plan, Step, StepStatus, auto_learn
from erirpg.agent.run import RunState, save_run, load_run, list_runs


class TestSpec:
    """Tests for Spec parsing."""

    def test_spec_from_goal(self):
        """Create spec from goal string."""
        spec = Spec.from_goal("implement feature X")
        assert spec.goal == "implement feature X"
        assert spec.constraints == []

    def test_spec_from_goal_with_kwargs(self):
        """Create spec with additional parameters."""
        spec = Spec.from_goal(
            "transplant X from A to B",
            source_project="A",
            target_project="B",
            constraints=["no new deps"],
        )
        assert spec.goal == "transplant X from A to B"
        assert spec.source_project == "A"
        assert spec.target_project == "B"
        assert "no new deps" in spec.constraints

    def test_spec_from_file(self, tmp_path):
        """Load spec from YAML file."""
        spec_file = tmp_path / "goal.yaml"
        spec_file.write_text("""
goal: "transplant masked_loss"
source_project: onetrainer
target_project: eritrainer
constraints:
  - no new dependencies
verification:
  - pytest
""")
        spec = Spec.from_file(str(spec_file))
        assert spec.goal == "transplant masked_loss"
        assert spec.source_project == "onetrainer"
        assert "no new dependencies" in spec.constraints
        assert "pytest" in spec.verification

    def test_spec_roundtrip(self, tmp_path):
        """Spec save and load roundtrip."""
        spec = Spec.from_goal(
            "test goal",
            constraints=["c1", "c2"],
        )
        path = str(tmp_path / "spec.yaml")
        spec.save(path)

        loaded = Spec.from_file(path)
        assert loaded.goal == spec.goal
        assert loaded.constraints == spec.constraints


class TestPlan:
    """Tests for Plan generation."""

    def test_plan_creation(self):
        """Create a plan with steps."""
        steps = [
            Step(id="s1", goal="Step 1", description="First", order=1),
            Step(id="s2", goal="Step 2", description="Second", order=2),
        ]
        plan = Plan.create("test goal", steps)

        assert plan.goal == "test goal"
        assert len(plan.steps) == 2
        assert plan.id  # Has generated ID

    def test_plan_progress(self):
        """Track plan progress."""
        steps = [
            Step(id="s1", goal="Step 1", description="", order=1),
            Step(id="s2", goal="Step 2", description="", order=2),
        ]
        plan = Plan.create("test", steps)

        # Initially 0/2
        assert plan.progress() == (0, 2)
        assert not plan.is_complete()

        # Complete first step
        steps[0].status = StepStatus.COMPLETED
        assert plan.progress() == (1, 2)

        # Complete second step
        steps[1].status = StepStatus.COMPLETED
        assert plan.progress() == (2, 2)
        assert plan.is_complete()

    def test_plan_current_step(self):
        """Get current step."""
        steps = [
            Step(id="s1", goal="Step 1", description="", order=1),
            Step(id="s2", goal="Step 2", description="", order=2),
        ]
        plan = Plan.create("test", steps)

        # First pending step
        current = plan.current_step()
        assert current.id == "s1"

        # After completing first
        steps[0].status = StepStatus.COMPLETED
        current = plan.current_step()
        assert current.id == "s2"

        # In progress takes precedence
        steps[1].status = StepStatus.IN_PROGRESS
        current = plan.current_step()
        assert current.id == "s2"


class TestAgent:
    """Tests for Agent API."""

    def test_agent_from_goal(self, tmp_path):
        """Create agent from goal string."""
        agent = Agent.from_goal(
            "implement feature X",
            project_path=str(tmp_path),
        )
        assert agent.spec.goal == "implement feature X"
        assert agent.plan is not None
        assert len(agent.plan.steps) > 0

    def test_agent_transplant_workflow(self, tmp_path):
        """Agent generates transplant workflow for transplant goals."""
        agent = Agent.from_goal(
            "transplant masked_loss from onetrainer to eritrainer",
            project_path=str(tmp_path),
        )
        # Should have analyze, plan, implement, verify steps
        step_ids = [s.id for s in agent.plan.steps]
        assert "analyze" in step_ids
        assert "implement" in step_ids

    def test_agent_fix_workflow(self, tmp_path):
        """Agent generates fix workflow for bug fix goals."""
        agent = Agent.from_goal(
            "fix the login bug",
            project_path=str(tmp_path),
        )
        step_ids = [s.id for s in agent.plan.steps]
        assert "investigate" in step_ids
        assert "fix" in step_ids

    def test_agent_step_execution(self, tmp_path):
        """Execute steps through agent."""
        agent = Agent.from_goal(
            "implement feature",
            project_path=str(tmp_path),
        )

        # Start first step
        step = agent.start_step()
        assert step is not None
        assert step.status == StepStatus.IN_PROGRESS

        # Complete step
        agent.complete_step(
            files_touched=["test.py"],
            notes="Did the thing",
            auto_learn_files=False,  # Skip auto-learn for test
        )
        assert step.status == StepStatus.COMPLETED
        assert "test.py" in step.files_touched

    def test_agent_get_context(self, tmp_path):
        """Get context for current step."""
        agent = Agent.from_goal(
            "implement feature",
            project_path=str(tmp_path),
            constraints=["no new deps"],
        )

        context = agent.get_context()
        assert "implement feature" in context
        assert "no new deps" in context

    def test_agent_progress(self, tmp_path):
        """Track agent progress."""
        agent = Agent.from_goal(
            "fix bug",
            project_path=str(tmp_path),
        )

        completed, total = agent.progress()
        assert completed == 0
        assert total > 0
        assert not agent.is_complete()


class TestAutoLearn:
    """Tests for auto-learning."""

    def test_auto_learn_creates_knowledge(self, tmp_path):
        """Auto-learn creates knowledge entries."""
        # Create a test file
        (tmp_path / "test.py").write_text("def foo(): pass")
        (tmp_path / ".eri-rpg").mkdir()

        learned = auto_learn(
            str(tmp_path),
            ["test.py"],
            "Test step goal",
        )

        assert "test.py" in learned

    def test_auto_learn_skips_missing_files(self, tmp_path):
        """Auto-learn skips files that don't exist."""
        (tmp_path / ".eri-rpg").mkdir()

        learned = auto_learn(
            str(tmp_path),
            ["nonexistent.py"],
            "Test step",
        )

        assert learned == []


class TestRunState:
    """Tests for run state persistence."""

    def test_run_state_save_load(self, tmp_path):
        """Run state roundtrip."""
        spec = Spec.from_goal("test")
        plan = Plan.create("test", [
            Step(id="s1", goal="Step 1", description="", order=1),
        ])
        run = RunState(id="test-run", spec=spec, plan=plan)

        # Save
        path = str(tmp_path / "run.json")
        run.save(path)

        # Load
        loaded = RunState.load(path)
        assert loaded.id == "test-run"
        assert loaded.spec.goal == "test"
        assert len(loaded.plan.steps) == 1

    def test_run_state_logging(self):
        """Run state logs events."""
        spec = Spec.from_goal("test")
        plan = Plan.create("test", [
            Step(id="s1", goal="Step 1", description="", order=1),
        ])
        run = RunState(id="test-run", spec=spec, plan=plan)

        run.add_log("test_event", {"key": "value"})
        assert len(run.log) == 1
        assert run.log[0]["event"] == "test_event"

    def test_run_state_report(self):
        """Generate run report."""
        spec = Spec.from_goal("test goal")
        plan = Plan.create("test goal", [
            Step(id="s1", goal="Step 1", description="", order=1),
        ])
        run = RunState(id="test-run", spec=spec, plan=plan)

        report = run.get_report()
        assert report["goal"] == "test goal"
        assert report["status"] == "in_progress"


class TestAgentResume:
    """Tests for agent resume functionality."""

    def test_agent_resume(self, tmp_path):
        """Resume an agent run."""
        # Create initial agent
        agent1 = Agent.from_goal(
            "test goal",
            project_path=str(tmp_path),
        )
        run_id = agent1._run.id

        # Start a step
        agent1.start_step()

        # Resume
        agent2 = Agent.resume(str(tmp_path), run_id)
        assert agent2 is not None
        assert agent2._run.id == run_id

        # Current step should still be in progress
        step = agent2.current_step()
        assert step.status == StepStatus.IN_PROGRESS
