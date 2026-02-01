#!/usr/bin/env python3
"""
/coder:verify-behavior - Run behavior diff after implementation.

Usage:
    python -m erirpg.commands.verify_behavior <program>/<feature> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from erirpg.coder import ensure_planning_dir


def load_behavior_spec(program: str, section: str, project_path: Optional[Path] = None) -> Optional[dict]:
    """Load a behavior spec from blueprints."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    program_dir = blueprints_dir / program

    # Handle nested sections
    if "/" in section:
        parts = section.split("/")
        behavior_file = program_dir
        for part in parts[:-1]:
            behavior_file = behavior_file / part
        behavior_file = behavior_file / f"{parts[-1]}-BEHAVIOR.md"
    else:
        behavior_file = program_dir / f"{section}-BEHAVIOR.md"

    if not behavior_file.exists():
        return None

    return {
        "program": program,
        "section": section,
        "file": str(behavior_file),
        "content": behavior_file.read_text()
    }


def load_feature_spec(program: str, feature: str, project_path: Optional[Path] = None) -> Optional[dict]:
    """Load a feature spec from features directory."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    features_dir = planning_dir / "features"

    # Try different file patterns
    patterns = [
        f"{program}-{feature}.md",
        f"feature-{feature}.md",
        f"{feature}.md"
    ]

    for pattern in patterns:
        feature_file = features_dir / pattern
        if feature_file.exists():
            return {
                "program": program,
                "feature": feature,
                "file": str(feature_file),
                "content": feature_file.read_text()
            }

    return None


def extract_spec_items(behavior_content: str) -> List[dict]:
    """Extract checkable items from behavior spec."""
    items = []

    lines = behavior_content.split("\n")

    # Extract inputs
    in_inputs = False
    for line in lines:
        line_lower = line.lower().strip()
        if "## inputs" in line_lower:
            in_inputs = True
        elif in_inputs and line.startswith("## "):
            in_inputs = False
        elif in_inputs and line.startswith("- **") and "**:" in line:
            name = line.split("**")[1].strip(":")
            items.append({
                "category": "input",
                "name": name,
                "spec": line,
                "check_type": "type_signature"
            })

    # Extract outputs
    in_outputs = False
    for line in lines:
        line_lower = line.lower().strip()
        if "## outputs" in line_lower:
            in_outputs = True
        elif in_outputs and line.startswith("## "):
            in_outputs = False
        elif in_outputs and line.startswith("- ") and not line.startswith("- ["):
            items.append({
                "category": "output",
                "name": line[2:50].strip(),
                "spec": line,
                "check_type": "output_check"
            })

    # Extract interface contract
    in_interface = False
    for line in lines:
        line_lower = line.lower().strip()
        if "## interface contract" in line_lower:
            in_interface = True
        elif in_interface and line.startswith("## "):
            in_interface = False
        elif in_interface and "**" in line and ":" in line:
            parts = line.split("**")
            if len(parts) >= 2:
                name = parts[1].strip(":")
                items.append({
                    "category": "interface",
                    "name": name,
                    "spec": line,
                    "check_type": "interface_check"
                })

    # Extract state machine states
    in_states = False
    for line in lines:
        line_lower = line.lower().strip()
        if "### state descriptions" in line_lower:
            in_states = True
        elif in_states and line.startswith("## "):
            in_states = False
        elif in_states and "|" in line and "---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and parts[0].lower() != "state":
                items.append({
                    "category": "state",
                    "name": parts[0],
                    "spec": line,
                    "check_type": "state_machine"
                })

    # Extract test contracts
    in_tests = False
    for line in lines:
        line_lower = line.lower().strip()
        if "## test contracts" in line_lower:
            in_tests = True
        elif in_tests and line.startswith("## "):
            in_tests = False
        elif in_tests and "|" in line and "---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3 and parts[0].lower() != "given":
                items.append({
                    "category": "test",
                    "name": f"Given {parts[0]} When {parts[1]}",
                    "spec": f"Then {parts[2]}",
                    "check_type": "test_contract"
                })

    # Extract global state impact items
    in_global = False
    for line in lines:
        line_lower = line.lower().strip()
        if "## global state impact" in line_lower:
            in_global = True
        elif in_global and line.startswith("## "):
            in_global = False
        elif in_global and "thread safety" in line_lower:
            items.append({
                "category": "side_effect",
                "name": "Thread safety",
                "spec": line,
                "check_type": "manual_verify"
            })
        elif in_global and "global mutations" in line_lower and "**" in line:
            items.append({
                "category": "side_effect",
                "name": "Global mutations",
                "spec": line,
                "check_type": "global_state_check"
            })

    # Extract ownership items
    in_ownership = False
    for line in lines:
        line_lower = line.lower().strip()
        if "## ownership model" in line_lower:
            in_ownership = True
        elif in_ownership and line.startswith("## "):
            in_ownership = False
        elif in_ownership and "|" in line and "---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and parts[0].lower() not in ["data", "lifetime"]:
                items.append({
                    "category": "ownership",
                    "name": parts[0],
                    "spec": f"Ownership: {parts[1]}",
                    "check_type": "ownership_check"
                })

    # Extract resource constraints
    in_constraints = False
    for line in lines:
        line_lower = line.lower().strip()
        if "### constraints" in line_lower:
            in_constraints = True
        elif in_constraints and line.startswith("## ") or (in_constraints and line.startswith("### ")):
            in_constraints = False
        elif in_constraints and line.startswith("- "):
            items.append({
                "category": "resource",
                "name": line[2:50].strip(),
                "spec": line,
                "check_type": "manual_verify"
            })

    return items


def generate_verification_report(
    spec_items: List[dict],
    auto_check_results: Optional[Dict[str, str]] = None
) -> dict:
    """Generate verification report with status for each item."""
    report = {
        "items": [],
        "summary": {
            "total": len(spec_items),
            "passed": 0,
            "failed": 0,
            "manual": 0,
            "pending": 0
        }
    }

    for item in spec_items:
        status = "⏳"  # pending
        code_check = ""

        # Auto-check results would come from actual code analysis
        if auto_check_results and item["name"] in auto_check_results:
            result = auto_check_results[item["name"]]
            if result == "pass":
                status = "✅"
                report["summary"]["passed"] += 1
            elif result == "fail":
                status = "❌"
                report["summary"]["failed"] += 1
            else:
                code_check = result
                status = "⚠️"
                report["summary"]["manual"] += 1
        elif item["check_type"] == "manual_verify":
            status = "⚠️ Manual"
            report["summary"]["manual"] += 1
        else:
            report["summary"]["pending"] += 1

        report["items"].append({
            "category": item["category"],
            "spec": f"{item['name']}: {item['spec'][:60]}",
            "code_check": code_check or "[Run code analysis]",
            "status": status
        })

    return report


def verify_behavior(
    program_feature: str,
    project_path: Optional[Path] = None,
    source_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Verify implementation matches behavior spec.
    
    Args:
        program_feature: Format 'program/feature' to verify
        project_path: Target project path (default: cwd)
        source_path: Source project path for automated verification
        output_json: Print result as JSON
    
    Returns:
        Verification result dict with status, scores, and details
    """
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "verify-behavior",
        "project": str(project_path),
        "target": program_feature,
    }

    try:
        if "/" not in program_feature:
            result["error"] = "Format: <program>/<feature>"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        parts = program_feature.split("/", 1)
        program = parts[0]
        feature = parts[1]

        # Load behavior spec
        behavior = load_behavior_spec(program, feature, project_path)
        if not behavior:
            # Try loading from feature file reference
            feature_spec = load_feature_spec(program, feature, project_path)
            if feature_spec:
                result["feature_file"] = feature_spec["file"]
                # Parse reference from feature file
                content = feature_spec["content"]
                if "reference_source:" in content:
                    import re
                    match = re.search(r"reference_source:\s*(\S+)", content)
                    if match:
                        ref = match.group(1)
                        ref_parts = ref.split("/", 1)
                        behavior = load_behavior_spec(ref_parts[0], ref_parts[1], project_path)

        if not behavior:
            result["error"] = f"No behavior spec found for {program_feature}"
            result["hint"] = f"Create with: /coder:blueprint add {program} {feature} --extract-behavior"
            if output_json:
                print(json.dumps(result, indent=2))
            return result

        result["behavior_file"] = behavior["file"]

        # Extract spec items from behavior file
        spec_items = extract_spec_items(behavior["content"])
        result["spec_items_count"] = len(spec_items)

        # NEW: If source_path provided, do automated code verification
        if source_path:
            try:
                from .lib.behavior_verifier import verify_module_behavior, format_verification_table
                from .lib.file_parity import compute_file_parity
                
                source_path = Path(source_path).expanduser().resolve()
                
                # Compute file parity
                parity = compute_file_parity(source_path, project_path, feature)
                result["file_parity"] = parity.to_dict()
                
                # Run automated verification
                verification_report = verify_module_behavior(
                    source_path, project_path, feature
                )
                
                result["automated_verification"] = verification_report.to_dict()
                result["verification_table"] = format_verification_table(verification_report)
                
                # Determine status from automated results
                if verification_report.total_missing > 0:
                    result["status"] = "FAILED"
                    result["message"] = f"🔴 {verification_report.total_missing} items MISSING in target"
                    result["blocking"] = True
                elif verification_report.total_failed > 0:
                    result["status"] = "FAILED"
                    result["message"] = f"❌ {verification_report.total_failed} failures found"
                    result["blocking"] = True
                elif verification_report.total_partial > 0:
                    result["status"] = "PARTIAL"
                    result["message"] = f"⚠️ {verification_report.total_partial} items need review"
                    result["blocking"] = False
                else:
                    result["status"] = "PASSED"
                    result["message"] = f"✅ All {verification_report.total_passed} checks passed"
                    result["blocking"] = False
                
                result["next_steps"] = []
                if parity.parity_score < 0.9:
                    result["next_steps"].append(
                        f"File parity is {parity.parity_score:.1%} - {len(parity.missing_in_target)} files missing"
                    )
                if verification_report.total_missing > 0:
                    result["next_steps"].append("Implement all missing classes and functions")
                if verification_report.total_failed > 0:
                    result["next_steps"].append("Fix all signature/inheritance mismatches")
                
            except ImportError:
                result["warning"] = "behavior_verifier not available, falling back to template verification"
                source_path = None  # Fall back to template
            except Exception as e:
                result["warning"] = f"Automated verification failed: {e}"
                source_path = None  # Fall back to template
        
        # Fall back to template-based verification if no source_path
        if not source_path:
            # Generate verification report (template-based)
            # Note: This is paper-only verification - use --source for automated
            report = generate_verification_report(spec_items)
            result["report"] = report
            result["verification_mode"] = "template"

            # Generate markdown table for easy viewing
            table_lines = [
                "| Behavior Spec | Code Check | Status |",
                "|---------------|------------|--------|"
            ]
            for item in report["items"]:
                table_lines.append(f"| {item['spec'][:40]} | {item['code_check'][:20]} | {item['status']} |")

            result["verification_table"] = "\n".join(table_lines)

            # Determine overall status
            if report["summary"]["failed"] > 0:
                result["status"] = "FAILED"
                result["message"] = f"❌ {report['summary']['failed']} violations found - fix before marking done"
                result["blocking"] = True
            elif report["summary"]["manual"] > 0:
                result["status"] = "NEEDS_REVIEW"
                result["message"] = f"⚠️ {report['summary']['manual']} items need manual verification"
                result["blocking"] = False
            elif report["summary"]["pending"] > 0:
                result["status"] = "PENDING"
                result["message"] = f"⏳ {report['summary']['pending']} items pending - use --source for automated verification"
                result["blocking"] = False
            else:
                result["status"] = "PASSED"
                result["message"] = "✅ All behavior spec items verified"
                result["blocking"] = False

            result["next_steps"] = []
            if report["summary"]["failed"] > 0:
                result["next_steps"].append("Fix all ❌ violations before continuing")
            if report["summary"]["manual"] > 0:
                result["next_steps"].append("Manually verify all ⚠️ items")
            if report["summary"]["pending"] > 0:
                result["next_steps"].append("Run with --source <path> for automated code analysis")

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    
    # Parse --source flag
    source_path = None
    if "--source" in sys.argv:
        idx = sys.argv.index("--source")
        if idx + 1 < len(sys.argv):
            source_path = Path(sys.argv[idx + 1])
    
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # Filter out the source path value if it was after --source
    if source_path and str(source_path) in args:
        args.remove(str(source_path))

    if not args:
        print(json.dumps({
            "error": "Target required",
            "usage": "verify_behavior <program>/<feature> [--source <source_path>] [--json]",
            "example": "verify_behavior eritrainer/sana --source ~/onetrainer",
            "options": {
                "--source <path>": "Source project for automated code verification",
                "--json": "Output as JSON"
            }
        }, indent=2))
        sys.exit(1)

    verify_behavior(args[0], source_path=source_path, output_json=output_json)


if __name__ == "__main__":
    main()
