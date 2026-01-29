"""
Plan Verifier for EriRPG.

Uses adversarial Claude-based verification to find gaps between specs and plans.
The key insight: quantifier audit catches most gaps (e.g., "all models" that only
covers image models, missing video models).

Usage:
    from erirpg.verifier import verify_plan, format_verification_result

    result = verify_plan(spec_dict, plan_dict)
    print(format_verification_result(result))
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Check for anthropic availability
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# The adversarial verification prompt
VERIFIER_PROMPT = '''You are an adversarial plan verifier. Your job is to find gaps between specs and plans, NOT to confirm they look good.

## Core Mindset
**Assume gaps exist until proven otherwise.** The plan is guilty until proven innocent.

## Your Task
Given a SPEC (what should be done) and a PLAN (how it will be done), find coverage gaps.

## SPEC:
```json
{{SPEC}}
```

## PLAN:
```json
{{PLAN}}
```

## Verification Steps

### 1. QUANTIFIER AUDIT (MANDATORY)
Find ALL universal quantifiers in the spec:
- "all", "every", "each", "any", "both", "complete", "full", "entire"

For EACH quantifier:
1. List exactly what it refers to (enumerate the items)
2. Check if plan has steps for EACH item
3. Mark covered or MISSING

### 2. EXPLICIT REQUIREMENTS
For every noun/entity in the spec, does the plan have a step?

### 3. IMPLICIT REQUIREMENTS
What does the spec assume but not state?
- Error handling
- Testing
- Edge cases

## Output Format
Return ONLY valid JSON with this structure:

{
  "verdict": "complete" | "gaps_found" | "incomplete",
  "confidence": "high" | "medium" | "low",
  "total_requirements": <number>,
  "covered_requirements": <number>,
  "quantifier_audit": [
    {
      "phrase": "all models",
      "refers_to": ["image models", "video models"],
      "covered": ["image models"],
      "missing": ["video models"]
    }
  ],
  "gaps": [
    {
      "id": "GAP-001",
      "severity": "critical" | "moderate" | "minor",
      "description": "Missing video model support",
      "spec_says": "support all models",
      "plan_has": "Only image model steps",
      "fix": "Add steps for video model support"
    }
  ],
  "recommendation": "proceed" | "revise_plan" | "clarify_spec"
}

## Anti-Patterns (DO NOT DO)
- "The plan looks comprehensive" - this is NOT verification
- Assuming coverage without enumerating each item
- Ignoring quantifiers
- Marking "covered" without specific step reference

Return ONLY the JSON, no other text.'''


@dataclass
class VerificationGap:
    """A gap found during verification."""
    id: str
    severity: str  # critical, moderate, minor
    description: str
    spec_says: str
    plan_has: str
    fix: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "description": self.description,
            "spec_says": self.spec_says,
            "plan_has": self.plan_has,
            "fix": self.fix,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationGap":
        return cls(
            id=data.get("id", "GAP-???"),
            severity=data.get("severity", "moderate"),
            description=data.get("description", "Unknown gap"),
            spec_says=data.get("spec_says", ""),
            plan_has=data.get("plan_has", ""),
            fix=data.get("fix", ""),
        )


@dataclass
class QuantifierAudit:
    """Audit of a quantifier phrase."""
    phrase: str
    refers_to: List[str]
    covered: List[str]
    missing: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phrase": self.phrase,
            "refers_to": self.refers_to,
            "covered": self.covered,
            "missing": self.missing,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuantifierAudit":
        return cls(
            phrase=data.get("phrase", ""),
            refers_to=data.get("refers_to", []),
            covered=data.get("covered", []),
            missing=data.get("missing", []),
        )


@dataclass
class VerificationResult:
    """Result of plan verification."""
    verdict: str  # complete, gaps_found, incomplete
    confidence: str  # high, medium, low
    total_requirements: int
    covered_requirements: int
    quantifier_audit: List[QuantifierAudit] = field(default_factory=list)
    gaps: List[VerificationGap] = field(default_factory=list)
    recommendation: str = "proceed"  # proceed, revise_plan, clarify_spec
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "total_requirements": self.total_requirements,
            "covered_requirements": self.covered_requirements,
            "quantifier_audit": [q.to_dict() for q in self.quantifier_audit],
            "gaps": [g.to_dict() for g in self.gaps],
            "recommendation": self.recommendation,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        return cls(
            verdict=data.get("verdict", "incomplete"),
            confidence=data.get("confidence", "low"),
            total_requirements=data.get("total_requirements", 0),
            covered_requirements=data.get("covered_requirements", 0),
            quantifier_audit=[
                QuantifierAudit.from_dict(q) for q in data.get("quantifier_audit", [])
            ],
            gaps=[VerificationGap.from_dict(g) for g in data.get("gaps", [])],
            recommendation=data.get("recommendation", "revise_plan"),
            error=data.get("error"),
        )

    @property
    def has_critical_gaps(self) -> bool:
        """Check if there are any critical gaps."""
        return any(g.severity == "critical" for g in self.gaps)

    @property
    def gap_count(self) -> int:
        """Total number of gaps."""
        return len(self.gaps)

    @property
    def critical_count(self) -> int:
        """Number of critical gaps."""
        return sum(1 for g in self.gaps if g.severity == "critical")

    @property
    def moderate_count(self) -> int:
        """Number of moderate gaps."""
        return sum(1 for g in self.gaps if g.severity == "moderate")

    @property
    def minor_count(self) -> int:
        """Number of minor gaps."""
        return sum(1 for g in self.gaps if g.severity == "minor")


def verify_plan(
    spec: Dict[str, Any],
    plan: Dict[str, Any],
    model: str = "claude-sonnet-4-20250514",
) -> VerificationResult:
    """Run adversarial verification via Claude.

    Args:
        spec: The spec dictionary (from spec.to_dict())
        plan: The plan dictionary (from plan.to_dict())
        model: The Claude model to use (default: claude-sonnet-4-20250514)

    Returns:
        VerificationResult with gaps found
    """
    if not ANTHROPIC_AVAILABLE:
        return VerificationResult(
            verdict="incomplete",
            confidence="low",
            total_requirements=0,
            covered_requirements=0,
            recommendation="revise_plan",
            error="anthropic package not installed. Run: pip install anthropic",
        )

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return VerificationResult(
            verdict="incomplete",
            confidence="low",
            total_requirements=0,
            covered_requirements=0,
            recommendation="revise_plan",
            error="ANTHROPIC_API_KEY not set",
        )

    # Build the prompt
    prompt = VERIFIER_PROMPT.replace(
        "{{SPEC}}", json.dumps(spec, indent=2)
    ).replace(
        "{{PLAN}}", json.dumps(plan, indent=2)
    )

    try:
        client = Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract response text
        response_text = response.content[0].text.strip()

        # Parse JSON from response
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (code block markers)
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        result_data = json.loads(response_text)
        return VerificationResult.from_dict(result_data)

    except json.JSONDecodeError as e:
        return VerificationResult(
            verdict="incomplete",
            confidence="low",
            total_requirements=0,
            covered_requirements=0,
            recommendation="revise_plan",
            error=f"Failed to parse verification result: {e}",
        )
    except Exception as e:
        return VerificationResult(
            verdict="incomplete",
            confidence="low",
            total_requirements=0,
            covered_requirements=0,
            recommendation="revise_plan",
            error=f"Verification failed: {e}",
        )


def format_verification_result(result: VerificationResult) -> str:
    """Format verification result for CLI display with box drawing.

    Args:
        result: The verification result to format

    Returns:
        Formatted string for terminal output
    """
    lines = []

    # Header
    lines.append("=" * 59)
    lines.append(" ERI:VERIFY RESULTS")
    lines.append("=" * 59)
    lines.append("")

    # Error handling
    if result.error:
        lines.append(f"Error: {result.error}")
        lines.append("")
        lines.append("=" * 59)
        return "\n".join(lines)

    # Summary
    verdict_icon = {
        "complete": "\u2705",  # green check
        "gaps_found": "\u26a0\ufe0f",  # warning
        "incomplete": "\u274c",  # red x
    }.get(result.verdict, "?")

    lines.append(f"Verdict: {verdict_icon} {result.verdict.upper()}")
    lines.append(f"Confidence: {result.confidence}")
    lines.append(
        f"Coverage: {result.covered_requirements} of {result.total_requirements} requirements"
        f" \u00b7 {result.gap_count} gaps found"
    )
    lines.append("")

    # Quantifier Audit
    if result.quantifier_audit:
        lines.append("-" * 59)
        lines.append("QUANTIFIER AUDIT")
        lines.append("-" * 59)
        for qa in result.quantifier_audit:
            lines.append(f'\u2022 "{qa.phrase}"')
            lines.append(f"  Refers to: {', '.join(qa.refers_to)}")
            if qa.covered:
                lines.append(f"  Covered:   {', '.join(qa.covered)} \u2713")
            if qa.missing:
                lines.append(f"  Missing:   {', '.join(qa.missing)} \u2717")
        lines.append("")

    # Gaps
    if result.gaps:
        lines.append("-" * 59)
        lines.append("GAPS")
        lines.append("-" * 59)
        lines.append("")

        # Group by severity
        critical = [g for g in result.gaps if g.severity == "critical"]
        moderate = [g for g in result.gaps if g.severity == "moderate"]
        minor = [g for g in result.gaps if g.severity == "minor"]

        if critical:
            lines.append("\U0001f534 CRITICAL (blocks completion)")
            for gap in critical:
                lines.append(f"{gap.id}: {gap.description}")
                lines.append(f'  Spec says: "{gap.spec_says}"')
                lines.append(f"  Plan has:  {gap.plan_has}")
                lines.append(f"  Fix:       {gap.fix}")
                lines.append("")

        if moderate:
            lines.append("\U0001f7e1 MODERATE (notable omission)")
            for gap in moderate:
                lines.append(f"{gap.id}: {gap.description}")
                lines.append(f'  Spec says: "{gap.spec_says}"')
                lines.append(f"  Plan has:  {gap.plan_has}")
                lines.append(f"  Fix:       {gap.fix}")
                lines.append("")

        if minor:
            lines.append("\U0001f7e2 MINOR (could be deferred)")
            for gap in minor:
                lines.append(f"{gap.id}: {gap.description}")
                lines.append(f'  Spec says: "{gap.spec_says}"')
                lines.append(f"  Plan has:  {gap.plan_has}")
                lines.append(f"  Fix:       {gap.fix}")
                lines.append("")

    # Recommendation
    lines.append("-" * 59)
    rec_icon = {
        "proceed": "\u2705",
        "revise_plan": "\u270f\ufe0f",
        "clarify_spec": "\u2753",
    }.get(result.recommendation, "")
    lines.append(f"RECOMMENDATION: {rec_icon} {result.recommendation}")
    lines.append("=" * 59)

    return "\n".join(lines)


def format_verification_json(result: VerificationResult) -> str:
    """Format verification result as JSON.

    Args:
        result: The verification result to format

    Returns:
        JSON string
    """
    return json.dumps(result.to_dict(), indent=2)


def format_status_line(persona: str, model: str, task: str) -> str:
    """Format a status line showing current persona, model, and task.

    Args:
        persona: Current persona (e.g., "Verifier")
        model: Current model (e.g., "sonnet", "opus")
        task: Current task (e.g., "eri:verify")

    Returns:
        Formatted status line
    """
    lines = []
    lines.append("-" * 59)
    lines.append(f" PERSONA: {persona} \u2502 MODEL: {model} \u2502 TASK: {task}")
    lines.append("-" * 59)
    return "\n".join(lines)


def format_model_comparison(
    sonnet_result: VerificationResult,
    opus_result: VerificationResult,
) -> str:
    """Format comparison between Sonnet and Opus verification results.

    Args:
        sonnet_result: Result from Sonnet verification
        opus_result: Result from Opus verification

    Returns:
        Formatted comparison box
    """
    lines = []

    # Box top
    lines.append("\u250c" + "\u2500" * 57 + "\u2510")
    lines.append("\u2502 MODEL COMPARISON" + " " * 40 + "\u2502")
    lines.append("\u251c" + "\u2500" * 57 + "\u2524")

    # Sonnet summary
    sonnet_gaps = f"{sonnet_result.gap_count} gaps"
    if sonnet_result.gap_count > 0:
        parts = []
        if sonnet_result.critical_count > 0:
            parts.append(f"{sonnet_result.critical_count} critical")
        if sonnet_result.moderate_count > 0:
            parts.append(f"{sonnet_result.moderate_count} moderate")
        if sonnet_result.minor_count > 0:
            parts.append(f"{sonnet_result.minor_count} minor")
        sonnet_gaps += f" ({', '.join(parts)})"

    sonnet_line = f"\u2502 Sonnet found: {sonnet_gaps}"
    sonnet_line += " " * (58 - len(sonnet_line)) + "\u2502"
    lines.append(sonnet_line)

    # Opus summary
    opus_gaps = f"{opus_result.gap_count} gaps"
    if opus_result.gap_count > 0:
        parts = []
        if opus_result.critical_count > 0:
            parts.append(f"{opus_result.critical_count} critical")
        if opus_result.moderate_count > 0:
            parts.append(f"{opus_result.moderate_count} moderate")
        if opus_result.minor_count > 0:
            parts.append(f"{opus_result.minor_count} minor")
        opus_gaps += f" ({', '.join(parts)})"

    opus_line = f"\u2502 Opus found:   {opus_gaps}"
    opus_line += " " * (58 - len(opus_line)) + "\u2502"
    lines.append(opus_line)

    # Find additional findings from Opus
    sonnet_gap_ids = {g.description for g in sonnet_result.gaps}
    opus_additional = [g for g in opus_result.gaps if g.description not in sonnet_gap_ids]

    if opus_additional:
        lines.append("\u2502" + " " * 57 + "\u2502")
        header = "\u2502 Opus additional findings:"
        header += " " * (58 - len(header)) + "\u2502"
        lines.append(header)

        for gap in opus_additional:
            icon = {
                "critical": "\U0001f534",  # red circle
                "moderate": "\U0001f7e1",  # yellow circle
                "minor": "\U0001f7e2",     # green circle
            }.get(gap.severity, "\u26aa")

            gap_line = f"\u2502  {icon} {gap.id}: {gap.description[:40]}"
            if len(gap.description) > 40:
                gap_line += "..."
            gap_line += " " * (58 - len(gap_line)) + "\u2502"
            lines.append(gap_line)

    # Box bottom
    lines.append("\u2514" + "\u2500" * 57 + "\u2518")

    return "\n".join(lines)


def should_escalate(result: VerificationResult) -> tuple[bool, str]:
    """Determine if verification should escalate to Opus.

    Args:
        result: The Sonnet verification result

    Returns:
        Tuple of (should_escalate, reason)
    """
    # PASS verdict is suspicious - gaps likely missed
    if result.verdict == "complete" and result.gap_count == 0:
        return True, "PASS verdict with 0 gaps is suspicious"

    # Low or medium confidence
    if result.confidence in ("low", "medium"):
        return True, f"confidence is {result.confidence}"

    # Any ambiguity gaps
    for gap in result.gaps:
        if "ambig" in gap.description.lower() or "unclear" in gap.description.lower():
            return True, "found ambiguity-related gaps"

    return False, ""
