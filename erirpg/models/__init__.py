"""
EriRPG Models - Data structures for ERI workflow.

This module provides dataclasses and enums for:
- Plans with goal-backward methodology
- Checkpoints for human-in-the-loop
- Verification results and gaps
- State and roadmap tracking
- Task execution
"""

from erirpg.models.plan import (
    Plan,
    MustHaves,
    Truth,
    Artifact,
    KeyLink,
    PlanType,
)
from erirpg.models.checkpoint import (
    Checkpoint,
    CheckpointType,
    CheckpointState,
)
from erirpg.models.gap import Gap, GapStatus
from erirpg.models.issue import Issue, IssueSeverity
from erirpg.models.task import Task, TaskType
from erirpg.models.state import State, StatePosition, StateMetrics, StateContinuity
from erirpg.models.roadmap import Roadmap, Phase, PhaseGoal
from erirpg.models.summary import Summary, TechStack
from erirpg.models.verification_models import (
    VerificationReport,
    VerificationLevel,
    TruthVerification,
    ArtifactVerification,
    LinkVerification,
)
from erirpg.models.context import Context, ContextDecision
from erirpg.models.uat import UAT, UATTest, UATDiagnosis
from erirpg.models.debug_session import DebugSession, Hypothesis

__all__ = [
    # Plan
    "Plan", "MustHaves", "Truth", "Artifact", "KeyLink", "PlanType",
    # Checkpoint
    "Checkpoint", "CheckpointType", "CheckpointState",
    # Gap
    "Gap", "GapStatus",
    # Issue
    "Issue", "IssueSeverity",
    # Task
    "Task", "TaskType",
    # State
    "State", "StatePosition", "StateMetrics", "StateContinuity",
    # Roadmap
    "Roadmap", "Phase", "PhaseGoal",
    # Summary
    "Summary", "TechStack",
    # Verification
    "VerificationReport", "VerificationLevel", "TruthVerification",
    "ArtifactVerification", "LinkVerification",
    # Context
    "Context", "ContextDecision",
    # UAT
    "UAT", "UATTest", "UATDiagnosis",
    # Debug
    "DebugSession", "Hypothesis",
]
