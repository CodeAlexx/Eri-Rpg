"""
Research pipeline for EriRPG.

Prevents reinventing wheels by researching best practices before implementation.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class LibraryChoice:
    """A library/framework choice made during research."""
    name: str
    version: str
    role: str           # "API framework", "ORM", "Auth"
    why: str            # Reason for choosing
    alternatives: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LibraryChoice":
        return cls(**d)


@dataclass
class Pitfall:
    """A common pitfall discovered during research."""
    name: str
    why_happens: str
    how_to_avoid: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Pitfall":
        return cls(**d)


@dataclass
class ResearchFindings:
    """Complete findings from a research phase."""
    goal: str
    discovery_level: int
    summary: str                    # One sentence recommendation
    confidence: str                 # HIGH | MEDIUM | LOW
    stack: List[LibraryChoice] = field(default_factory=list)
    pitfalls: List[Pitfall] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    dont_hand_roll: List[Tuple[str, str]] = field(default_factory=list)  # (problem, solution)
    code_examples: List[Tuple[str, str]] = field(default_factory=list)   # (title, code)
    sources: List[str] = field(default_factory=list)
    researched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "discovery_level": self.discovery_level,
            "summary": self.summary,
            "confidence": self.confidence,
            "stack": [s.to_dict() for s in self.stack],
            "pitfalls": [p.to_dict() for p in self.pitfalls],
            "anti_patterns": self.anti_patterns,
            "dont_hand_roll": self.dont_hand_roll,
            "code_examples": self.code_examples,
            "sources": self.sources,
            "researched_at": self.researched_at,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchFindings":
        return cls(
            goal=d["goal"],
            discovery_level=d["discovery_level"],
            summary=d["summary"],
            confidence=d["confidence"],
            stack=[LibraryChoice.from_dict(s) for s in d.get("stack", [])],
            pitfalls=[Pitfall.from_dict(p) for p in d.get("pitfalls", [])],
            anti_patterns=d.get("anti_patterns", []),
            dont_hand_roll=[tuple(x) for x in d.get("dont_hand_roll", [])],
            code_examples=[tuple(x) for x in d.get("code_examples", [])],
            sources=d.get("sources", []),
            researched_at=d.get("researched_at", datetime.utcnow().isoformat()),
        )
    
    def to_markdown(self) -> str:
        """Generate RESEARCH.md format."""
        lines = [f"# Research: {self.goal}", ""]
        
        # Summary
        lines.extend([
            "## Summary",
            self.summary,
            f"**Confidence:** {self.confidence}",
            ""
        ])
        
        # Stack
        if self.stack:
            lines.extend(["## Stack", "| Role | Choice | Why | Rejected |", "|------|--------|-----|----------|"])
            for lib in self.stack:
                rejected = ", ".join(lib.alternatives) if lib.alternatives else "-"
                lines.append(f"| {lib.role} | {lib.name} {lib.version} | {lib.why} | {rejected} |")
            lines.append("")
        
        # Don't Hand-Roll
        if self.dont_hand_roll:
            lines.extend(["## Don't Hand-Roll", "| Problem | Use Instead |", "|---------|-------------|"])
            for problem, solution in self.dont_hand_roll:
                lines.append(f"| {problem} | {solution} |")
            lines.append("")
        
        # Pitfalls
        if self.pitfalls:
            lines.extend(["## Pitfalls", "| Pitfall | Why | Avoidance |", "|---------|-----|-----------|"])
            for p in self.pitfalls:
                lines.append(f"| {p.name} | {p.why_happens} | {p.how_to_avoid} |")
            lines.append("")
        
        # Anti-Patterns
        if self.anti_patterns:
            lines.append("## Anti-Patterns")
            for pattern in self.anti_patterns:
                lines.append(f"- {pattern}")
            lines.append("")
        
        # Code Examples
        if self.code_examples:
            lines.append("## Code Examples")
            for title, code in self.code_examples:
                lines.extend([f"### {title}", "```python", code, "```", ""])
        
        # Sources
        if self.sources:
            lines.append("## Sources")
            for source in self.sources:
                lines.append(f"- {source}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_avoid_patterns(self) -> List["AvoidPattern"]:
        """Convert findings to step-injectable AvoidPattern list."""
        from erirpg.agent.plan import AvoidPattern
        
        patterns = []
        
        # Anti-patterns
        for ap in self.anti_patterns:
            patterns.append(AvoidPattern(
                pattern=ap,
                reason="anti-pattern from research",
                source="RESEARCH.md"
            ))
        
        # Don't hand-roll
        for problem, solution in self.dont_hand_roll:
            patterns.append(AvoidPattern(
                pattern=f"Don't implement {problem} manually",
                reason=f"Use {solution} instead",
                source="RESEARCH.md"
            ))
        
        # Pitfalls
        for pitfall in self.pitfalls:
            patterns.append(AvoidPattern(
                pattern=pitfall.name,
                reason=pitfall.how_to_avoid,
                source="RESEARCH.md"
            ))
        
        return patterns


class ResearchCache:
    """Cache for research findings by goal hash."""
    
    def __init__(self, project_path: str):
        self.cache_file = Path(project_path) / ".eri-rpg" / "research_cache.json"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self):
        if self.cache_file.exists():
            try:
                self._cache = json.loads(self.cache_file.read_text())
            except (json.JSONDecodeError, IOError):
                self._cache = {}
    
    def _save(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self._cache, indent=2))
    
    @staticmethod
    def _hash_goal(goal: str) -> str:
        return hashlib.md5(goal.lower().strip().encode()).hexdigest()[:12]
    
    def get(self, goal: str) -> Optional[ResearchFindings]:
        """Get cached findings for a goal."""
        key = self._hash_goal(goal)
        if key in self._cache:
            try:
                return ResearchFindings.from_dict(self._cache[key]["findings"])
            except (KeyError, TypeError):
                return None
        return None
    
    def set(self, goal: str, findings: ResearchFindings):
        """Cache findings for a goal."""
        key = self._hash_goal(goal)
        self._cache[key] = {
            "goal": goal,
            "findings": findings.to_dict(),
            "cached_at": datetime.utcnow().isoformat(),
        }
        self._save()
    
    def clear(self, goal: Optional[str] = None):
        """Clear cache for specific goal or all."""
        if goal:
            key = self._hash_goal(goal)
            self._cache.pop(key, None)
        else:
            self._cache = {}
        self._save()


class ResearchPhase:
    """Orchestrates research for a goal."""
    
    def __init__(self, project_path: str, goal: str, level: int):
        self.project_path = Path(project_path)
        self.goal = goal
        self.level = level
        self.cache = ResearchCache(project_path)
    
    def execute(self) -> Optional[ResearchFindings]:
        """
        Execute research phase.
        
        Returns None if level is 0 (skip).
        Returns cached findings if available.
        Otherwise, returns a template for CC to fill.
        """
        if self.level == 0:
            return None
        
        # Check cache
        cached = self.cache.get(self.goal)
        if cached:
            return cached
        
        # Return template - CC will fill this via tools
        return ResearchFindings(
            goal=self.goal,
            discovery_level=self.level,
            summary="[TO BE FILLED BY RESEARCH]",
            confidence="LOW",
        )
    
    def save_findings(self, findings: ResearchFindings, phase_id: Optional[str] = None):
        """Save findings to cache and optionally to phase directory."""
        self.cache.set(self.goal, findings)
        
        if phase_id:
            phase_dir = self.project_path / ".eri-rpg" / "phases" / phase_id
            phase_dir.mkdir(parents=True, exist_ok=True)
            
            # Save markdown
            (phase_dir / "RESEARCH.md").write_text(findings.to_markdown())
            
            # Save JSON
            (phase_dir / "research.json").write_text(
                json.dumps(findings.to_dict(), indent=2)
            )
