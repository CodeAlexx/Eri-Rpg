#!/usr/bin/env python3
"""
/coder:meta-edit - Safe self-modification of coder commands.

No more breaking files with ad hoc edits. This follows EMPOWERMENT.md:
- Challenge before implementing
- Require intent
- Flag what could break

Usage:
    python -m erirpg.commands.meta_edit analyze <command> [--json]
    python -m erirpg.commands.meta_edit plan <command> --intent "<what to change>" [--json]
    python -m erirpg.commands.meta_edit execute <command> [--json]
    python -m erirpg.commands.meta_edit verify <command> [--json]
    python -m erirpg.commands.meta_edit rollback <command> [--json]
    python -m erirpg.commands.meta_edit status <command> [--json]
"""

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Where coder commands live
COMMANDS_DIR = Path.home() / ".claude" / "commands" / "coder"
# Where meta-edit stores its work
META_EDIT_DIR = Path.home() / ".claude" / ".coder" / "meta-edit"


def get_command_path(command: str) -> Path:
    """Get path to a coder command file."""
    # Handle both "init" and "coder:init" formats
    if ":" in command:
        command = command.split(":")[-1]
    return COMMANDS_DIR / f"{command}.md"


def get_meta_dir(command: str) -> Path:
    """Get meta-edit directory for a command."""
    if ":" in command:
        command = command.split(":")[-1]
    return META_EDIT_DIR / command


def find_dependencies(content: str, command_name: str) -> dict:
    """Find what this command calls and what might call it."""
    dependencies = {
        "calls": [],  # Commands this file references
        "called_by": [],  # Commands that might call this
        "cli_commands": [],  # CLI commands used
    }

    # Find /coder: references
    coder_refs = re.findall(r'/coder:([a-z-]+)', content)
    dependencies["calls"] = list(set(coder_refs) - {command_name})

    # Find CLI commands (erirpg or python -m erirpg)
    cli_refs = re.findall(r'(?:erirpg|python[3]? -m erirpg(?:\.cli)?)\s+([a-z-]+)', content)
    dependencies["cli_commands"] = list(set(cli_refs))

    # Find eri: references
    eri_refs = re.findall(r'/eri:([a-z-]+)', content)
    if eri_refs:
        dependencies["eri_commands"] = list(set(eri_refs))

    # Check other commands for references to this one
    for cmd_file in COMMANDS_DIR.glob("*.md"):
        if cmd_file.stem == command_name:
            continue
        try:
            other_content = cmd_file.read_text()
            if f"/coder:{command_name}" in other_content:
                dependencies["called_by"].append(cmd_file.stem)
        except Exception:
            pass

    return dependencies


def analyze(command: str, output_json: bool = False) -> dict:
    """
    Phase 1: ANALYZE - Before any changes.

    - Read the target command file completely
    - Document what it does NOW
    - List all dependencies
    - Create snapshot
    """
    result = {
        "command": "meta-edit",
        "phase": "analyze",
        "target": command,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    cmd_path = get_command_path(command)
    meta_dir = get_meta_dir(command)

    # Check command exists
    if not cmd_path.exists():
        result["error"] = f"Command not found: {cmd_path}"
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    # Read current content
    content = cmd_path.read_text()
    result["file_path"] = str(cmd_path)
    result["line_count"] = len(content.splitlines())
    result["size_bytes"] = len(content.encode())

    # Extract key sections
    sections = {
        "has_frontmatter": content.startswith("---"),
        "has_cli_integration": "```bash" in content and ("erirpg" in content or "python" in content),
        "has_process": "<process>" in content or "## Process" in content or "## Execution" in content,
        "has_objective": "<objective>" in content or "## Objective" in content,
    }
    result["structure"] = sections

    # Find dependencies
    cmd_name = command.split(":")[-1] if ":" in command else command
    dependencies = find_dependencies(content, cmd_name)
    result["dependencies"] = dependencies

    # Create meta-edit directory
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Create snapshot
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    snapshot_name = f"{cmd_path.name}.snapshot.{timestamp}"
    snapshot_path = meta_dir / snapshot_name
    shutil.copy2(cmd_path, snapshot_path)
    result["snapshot"] = str(snapshot_path)

    # Write ANALYSIS.md
    analysis_content = f"""# Analysis: /coder:{cmd_name}

Generated: {result['timestamp']}
Source: {cmd_path}
Snapshot: {snapshot_path}

## Current State

- **Lines**: {result['line_count']}
- **Size**: {result['size_bytes']} bytes
- **Has CLI Integration**: {sections['has_cli_integration']}
- **Has Process Section**: {sections['has_process']}

## Dependencies

### Commands This Calls
{chr(10).join(f"- /coder:{c}" for c in dependencies['calls']) or "- None"}

### CLI Commands Used
{chr(10).join(f"- `erirpg {c}`" for c in dependencies['cli_commands']) or "- None"}

### Commands That Call This
{chr(10).join(f"- /coder:{c}" for c in dependencies['called_by']) or "- None (or not detected)"}

## Snapshot Created

```
{snapshot_path}
```

To restore: `cp "{snapshot_path}" "{cmd_path}"`

## Next Step

Run: `python3 -m erirpg.commands.meta_edit plan {cmd_name} --intent "<what you want to change>"`
"""

    analysis_path = meta_dir / "ANALYSIS.md"
    analysis_path.write_text(analysis_content)
    result["analysis_file"] = str(analysis_path)

    result["next_step"] = {
        "phase": "plan",
        "command": f'python3 -m erirpg.commands.meta_edit plan {cmd_name} --intent "<describe changes>"'
    }

    result["message"] = f"Analysis complete. Snapshot created at {snapshot_path}"

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def plan(command: str, intent: str, output_json: bool = False) -> dict:
    """
    Phase 2: PLAN - Requires user approval.

    - State the change intent
    - List what could break
    - Define verification steps
    - STOP and wait for approval
    """
    result = {
        "command": "meta-edit",
        "phase": "plan",
        "target": command,
        "intent": intent,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    cmd_path = get_command_path(command)
    meta_dir = get_meta_dir(command)

    # Check analysis was done
    analysis_path = meta_dir / "ANALYSIS.md"
    if not analysis_path.exists():
        result["error"] = "No analysis found. Run analyze phase first."
        result["fix"] = f"python3 -m erirpg.commands.meta_edit analyze {command}"
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    # Find latest snapshot
    snapshots = sorted(meta_dir.glob(f"{cmd_path.name}.snapshot.*"))
    if not snapshots:
        result["error"] = "No snapshot found. Run analyze phase first."
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    latest_snapshot = snapshots[-1]
    result["snapshot"] = str(latest_snapshot)

    # Read current content
    content = cmd_path.read_text()
    cmd_name = command.split(":")[-1] if ":" in command else command

    # Find dependencies for risk assessment
    dependencies = find_dependencies(content, cmd_name)

    # Build risk assessment
    risks = []
    if dependencies["called_by"]:
        risks.append(f"Commands that depend on this: {', '.join(dependencies['called_by'])}")
    if dependencies["cli_commands"]:
        risks.append(f"CLI integration may need updates if changing: {', '.join(dependencies['cli_commands'])}")
    if "frontmatter" in intent.lower() or "---" in intent:
        risks.append("Frontmatter changes may affect command registration")
    if "cli" in intent.lower() or "bash" in intent.lower():
        risks.append("CLI integration changes require testing the actual CLI command")

    # Build verification steps
    verifications = [
        f"1. Command file is valid markdown",
        f"2. No syntax errors in code blocks",
    ]
    if dependencies["cli_commands"]:
        verifications.append(f"3. CLI command still works: `erirpg {dependencies['cli_commands'][0]} --help`")
    if dependencies["called_by"]:
        verifications.append(f"4. Dependent commands still reference correctly: {', '.join(dependencies['called_by'])}")
    verifications.append(f"5. Rollback available: `cp \"{latest_snapshot}\" \"{cmd_path}\"`")

    # Write PLAN.md
    plan_content = f"""# Plan: Modify /coder:{cmd_name}

Generated: {result['timestamp']}

## Intent

{intent}

## Current File

- **Path**: {cmd_path}
- **Snapshot**: {latest_snapshot}

## Risk Assessment

{chr(10).join(f"- ⚠️ {r}" for r in risks) or "- No significant risks detected"}

## Verification Steps

{chr(10).join(verifications)}

## Instructions for Claude

**DO NOT EDIT THE FILE YET.**

1. Read the current file completely: `{cmd_path}`
2. Read the snapshot to understand original state: `{latest_snapshot}`
3. Show the user EXACTLY what you plan to change (diff format preferred)
4. Wait for explicit approval
5. Only then run: `python3 -m erirpg.commands.meta_edit execute {cmd_name}`

## Approval Required

User must approve changes before execution.

To proceed after approval:
```bash
python3 -m erirpg.commands.meta_edit execute {cmd_name}
```

To abort:
```bash
rm -rf "{meta_dir}"
```
"""

    plan_path = meta_dir / "PLAN.md"
    plan_path.write_text(plan_content)
    result["plan_file"] = str(plan_path)

    result["risks"] = risks
    result["verifications"] = verifications
    result["requires_approval"] = True
    result["current_file"] = str(cmd_path)

    result["next_step"] = {
        "action": "WAIT FOR USER APPROVAL",
        "show_diff": True,
        "then_run": f"python3 -m erirpg.commands.meta_edit execute {cmd_name}"
    }

    result["message"] = "Plan created. Show proposed changes to user and wait for approval before executing."

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def execute(command: str, output_json: bool = False) -> dict:
    """
    Phase 3: EXECUTE - Only after approval.

    This phase just marks that execution is approved.
    The actual file edit is done by Claude after this returns.
    """
    result = {
        "command": "meta-edit",
        "phase": "execute",
        "target": command,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    cmd_path = get_command_path(command)
    meta_dir = get_meta_dir(command)
    cmd_name = command.split(":")[-1] if ":" in command else command

    # Check plan exists
    plan_path = meta_dir / "PLAN.md"
    if not plan_path.exists():
        result["error"] = "No plan found. Run plan phase first."
        result["fix"] = f'python3 -m erirpg.commands.meta_edit plan {cmd_name} --intent "<changes>"'
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    # Find snapshot for safety
    snapshots = sorted(meta_dir.glob(f"{cmd_path.name}.snapshot.*"))
    if snapshots:
        result["snapshot"] = str(snapshots[-1])
        result["rollback_command"] = f'cp "{snapshots[-1]}" "{cmd_path}"'

    result["file_to_edit"] = str(cmd_path)
    result["execution_approved"] = True

    result["instructions"] = [
        f"1. Edit {cmd_path} with the approved changes",
        "2. After editing, run verify phase",
        f"3. Verify: python3 -m erirpg.commands.meta_edit verify {cmd_name}"
    ]

    result["next_step"] = {
        "action": "EDIT THE FILE NOW",
        "file": str(cmd_path),
        "then_run": f"python3 -m erirpg.commands.meta_edit verify {cmd_name}"
    }

    result["message"] = f"Execution approved. Edit {cmd_path} then run verify."

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def verify(command: str, output_json: bool = False) -> dict:
    """
    Phase 4: VERIFY - Required, not optional.

    - Check file is valid
    - Test basic functionality
    - Auto-rollback if verification fails
    """
    result = {
        "command": "meta-edit",
        "phase": "verify",
        "target": command,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": [],
    }

    cmd_path = get_command_path(command)
    meta_dir = get_meta_dir(command)
    cmd_name = command.split(":")[-1] if ":" in command else command

    # Find snapshot
    snapshots = sorted(meta_dir.glob(f"{cmd_path.name}.snapshot.*"))
    snapshot = snapshots[-1] if snapshots else None

    all_passed = True
    checks = []

    # Check 1: File exists
    check1 = {"name": "file_exists", "passed": cmd_path.exists()}
    if not check1["passed"]:
        check1["error"] = f"File not found: {cmd_path}"
        all_passed = False
    checks.append(check1)

    if cmd_path.exists():
        content = cmd_path.read_text()

        # Check 2: File is not empty
        check2 = {"name": "not_empty", "passed": len(content.strip()) > 0}
        if not check2["passed"]:
            check2["error"] = "File is empty"
            all_passed = False
        checks.append(check2)

        # Check 3: Valid frontmatter (if present)
        if content.startswith("---"):
            parts = content.split("---", 2)
            check3 = {"name": "valid_frontmatter", "passed": len(parts) >= 3}
            if not check3["passed"]:
                check3["error"] = "Frontmatter not properly closed"
                all_passed = False
            checks.append(check3)

        # Check 4: No broken code blocks
        code_blocks_open = content.count("```")
        check4 = {"name": "balanced_code_blocks", "passed": code_blocks_open % 2 == 0}
        if not check4["passed"]:
            check4["error"] = f"Unbalanced code blocks: {code_blocks_open} backtick sequences"
            all_passed = False
        checks.append(check4)

        # Check 5: Reasonable size (not truncated or bloated)
        check5 = {"name": "reasonable_size", "passed": 100 < len(content) < 100000}
        if not check5["passed"]:
            check5["error"] = f"Suspicious size: {len(content)} bytes"
            all_passed = False
        checks.append(check5)

        # Check 6: Contains expected sections
        has_content = any([
            "<process>" in content,
            "## Process" in content,
            "## Execution" in content,
            "## Usage" in content,
            "## Steps" in content,
        ])
        check6 = {"name": "has_structure", "passed": has_content}
        if not check6["passed"]:
            check6["warning"] = "No standard process/execution section found"
        checks.append(check6)

    result["checks"] = checks
    result["all_passed"] = all_passed

    # Auto-rollback if failed
    if not all_passed and snapshot:
        shutil.copy2(snapshot, cmd_path)
        result["rolled_back"] = True
        result["rollback_from"] = str(snapshot)
        result["message"] = f"VERIFICATION FAILED. Auto-rolled back from {snapshot}"
    elif not all_passed:
        result["rolled_back"] = False
        result["message"] = "VERIFICATION FAILED. No snapshot available for rollback!"
    else:
        result["message"] = "All checks passed. Changes verified."
        result["snapshot_kept"] = str(snapshot) if snapshot else None
        result["cleanup_hint"] = f"To clean up after confirming: rm -rf \"{meta_dir}\""

    # Write VERIFY.md
    verify_content = f"""# Verification: /coder:{cmd_name}

Generated: {result['timestamp']}
Status: {"✅ PASSED" if all_passed else "❌ FAILED"}

## Checks

| Check | Status | Details |
|-------|--------|---------|
{chr(10).join(f"| {c['name']} | {'✅' if c.get('passed') else '❌'} | {c.get('error', c.get('warning', 'OK'))} |" for c in checks)}

## Result

{"All checks passed. Changes are safe." if all_passed else "FAILED: Auto-rollback triggered." if result.get('rolled_back') else "FAILED: Manual intervention required."}

{"## Snapshot Preserved" if snapshot else ""}
{"Keep until you confirm everything works:" if snapshot else ""}
{f"`{snapshot}`" if snapshot else ""}
"""

    verify_path = meta_dir / "VERIFY.md"
    verify_path.write_text(verify_content)
    result["verify_file"] = str(verify_path)

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def rollback(command: str, output_json: bool = False) -> dict:
    """Manual rollback to snapshot."""
    result = {
        "command": "meta-edit",
        "phase": "rollback",
        "target": command,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    cmd_path = get_command_path(command)
    meta_dir = get_meta_dir(command)

    # Find latest snapshot
    snapshots = sorted(meta_dir.glob(f"{cmd_path.name}.snapshot.*"))
    if not snapshots:
        result["error"] = "No snapshot found"
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    latest = snapshots[-1]
    shutil.copy2(latest, cmd_path)

    result["rolled_back_from"] = str(latest)
    result["rolled_back_to"] = str(cmd_path)
    result["message"] = f"Rolled back {cmd_path.name} from snapshot {latest.name}"

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def status(command: str, output_json: bool = False) -> dict:
    """Show current meta-edit status for a command."""
    result = {
        "command": "meta-edit",
        "phase": "status",
        "target": command,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    cmd_path = get_command_path(command)
    meta_dir = get_meta_dir(command)
    cmd_name = command.split(":")[-1] if ":" in command else command

    result["command_exists"] = cmd_path.exists()
    result["meta_dir_exists"] = meta_dir.exists()

    if meta_dir.exists():
        result["has_analysis"] = (meta_dir / "ANALYSIS.md").exists()
        result["has_plan"] = (meta_dir / "PLAN.md").exists()
        result["has_verify"] = (meta_dir / "VERIFY.md").exists()

        snapshots = sorted(meta_dir.glob(f"*.snapshot.*"))
        result["snapshots"] = [s.name for s in snapshots]

        # Determine current phase
        if result["has_verify"]:
            result["current_phase"] = "complete"
        elif result["has_plan"]:
            result["current_phase"] = "awaiting_execution"
        elif result["has_analysis"]:
            result["current_phase"] = "awaiting_plan"
        else:
            result["current_phase"] = "initialized"
    else:
        result["current_phase"] = "not_started"
        result["next_step"] = f"python3 -m erirpg.commands.meta_edit analyze {cmd_name}"

    if output_json:
        print(json.dumps(result, indent=2))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if len(args) < 1:
        result = {
            "error": "Usage: meta_edit <phase> <command> [options]",
            "phases": ["analyze", "plan", "execute", "verify", "rollback", "status"],
            "example": "python3 -m erirpg.commands.meta_edit analyze init"
        }
        print(json.dumps(result, indent=2))
        return

    phase = args[0]

    if phase == "analyze":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit analyze <command>"}, indent=2))
            return
        analyze(args[1], output_json=output_json)

    elif phase == "plan":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit plan <command> --intent '<changes>'"}, indent=2))
            return
        # Extract intent
        intent = None
        for i, arg in enumerate(sys.argv):
            if arg == "--intent" and i + 1 < len(sys.argv):
                intent = sys.argv[i + 1]
                break
        if not intent:
            print(json.dumps({"error": "--intent required for plan phase"}, indent=2))
            return
        plan(args[1], intent, output_json=output_json)

    elif phase == "execute":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit execute <command>"}, indent=2))
            return
        execute(args[1], output_json=output_json)

    elif phase == "verify":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit verify <command>"}, indent=2))
            return
        verify(args[1], output_json=output_json)

    elif phase == "rollback":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit rollback <command>"}, indent=2))
            return
        rollback(args[1], output_json=output_json)

    elif phase == "status":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit status <command>"}, indent=2))
            return
        status(args[1], output_json=output_json)

    else:
        print(json.dumps({
            "error": f"Unknown phase: {phase}",
            "valid_phases": ["analyze", "plan", "execute", "verify", "rollback", "status"]
        }, indent=2))


if __name__ == "__main__":
    main()
