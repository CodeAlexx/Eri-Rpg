#!/usr/bin/env python3
"""
/coder:meta-edit - Safe self-modification of ANY coder/erirpg files.

Scope:
- ~/.claude/commands/coder/*.md (coder commands)
- erirpg/*.py (the system itself)
- Any file affecting coder/erirpg behavior

No more breaking files with ad hoc edits. This follows EMPOWERMENT.md:
- Challenge before implementing
- Require intent
- Flag what could break

Usage:
    # For coder commands (shorthand)
    python -m erirpg.commands.meta_edit analyze init [--json]

    # For any file (full path)
    python -m erirpg.commands.meta_edit analyze /path/to/file.py [--json]

    python -m erirpg.commands.meta_edit plan <target> --intent "<what to change>" [--json]
    python -m erirpg.commands.meta_edit execute <target> [--json]
    python -m erirpg.commands.meta_edit verify <target> [--json]
    python -m erirpg.commands.meta_edit rollback <target> [--json]
    python -m erirpg.commands.meta_edit status <target> [--json]
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple


# Where coder commands live
COMMANDS_DIR = Path.home() / ".claude" / "commands" / "coder"
# Where erirpg code lives
ERIRPG_DIR = Path(__file__).parent.parent  # erirpg/
# Where meta-edit stores its work
META_EDIT_DIR = Path.home() / ".claude" / ".coder" / "meta-edit"


def resolve_target(target: str) -> Tuple[Path, str, str]:
    """
    Resolve target to (file_path, display_name, file_type).

    Accepts:
    - "init" -> ~/.claude/commands/coder/init.md (coder command)
    - "coder:init" -> ~/.claude/commands/coder/init.md
    - "/path/to/file.py" -> that file (python)
    - "erirpg/statusline.py" -> erirpg/statusline.py (python)
    - "statusline" -> erirpg/statusline.py (erirpg shorthand)
    """
    # Full path
    if target.startswith("/") or target.startswith("~"):
        path = Path(target).expanduser()
        name = path.name
        file_type = "python" if path.suffix == ".py" else "markdown" if path.suffix == ".md" else "unknown"
        return path, name, file_type

    # Relative path with extension
    if "/" in target and ("." in target.split("/")[-1]):
        path = Path(target)
        if not path.is_absolute():
            # Check if it's relative to erirpg
            if target.startswith("erirpg/"):
                path = ERIRPG_DIR.parent / target
            else:
                path = Path.cwd() / target
        name = path.name
        file_type = "python" if path.suffix == ".py" else "markdown" if path.suffix == ".md" else "unknown"
        return path, name, file_type

    # Coder command shorthand (e.g., "init" or "coder:init")
    if ":" in target:
        cmd_name = target.split(":")[-1]
    else:
        cmd_name = target

    # Check if it's a coder command
    coder_path = COMMANDS_DIR / f"{cmd_name}.md"
    if coder_path.exists():
        return coder_path, f"coder:{cmd_name}", "markdown"

    # Check if it's an erirpg module (shorthand)
    erirpg_path = ERIRPG_DIR / f"{cmd_name}.py"
    if erirpg_path.exists():
        return erirpg_path, f"erirpg/{cmd_name}.py", "python"

    # Check erirpg subdirectories
    for subdir in ["commands", "hooks", "coder", "cli_commands"]:
        sub_path = ERIRPG_DIR / subdir / f"{cmd_name}.py"
        if sub_path.exists():
            return sub_path, f"erirpg/{subdir}/{cmd_name}.py", "python"

    # Default: assume it's a coder command that doesn't exist yet
    return coder_path, f"coder:{cmd_name}", "markdown"


def get_meta_dir(target: str) -> Path:
    """Get meta-edit directory for a target."""
    _, display_name, _ = resolve_target(target)
    # Sanitize for directory name
    safe_name = display_name.replace("/", "_").replace(":", "_").replace(".", "_")
    return META_EDIT_DIR / safe_name


def find_python_dependencies(path: Path, content: str) -> dict:
    """Find dependencies for a Python file."""
    deps = {
        "imports": [],
        "imported_by": [],
        "calls_cli": [],
    }

    # Find imports
    import_patterns = [
        r'^import\s+([\w.]+)',
        r'^from\s+([\w.]+)\s+import',
    ]
    for pattern in import_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        deps["imports"].extend(matches)

    # Find erirpg-specific imports
    deps["erirpg_imports"] = [i for i in deps["imports"] if "erirpg" in i]

    # Find what imports this module
    module_name = path.stem
    parent_dir = path.parent.name

    # Search erirpg for imports of this module
    for py_file in ERIRPG_DIR.rglob("*.py"):
        if py_file == path:
            continue
        try:
            other_content = py_file.read_text()
            if f"from erirpg.{parent_dir}.{module_name}" in other_content or \
               f"from erirpg.{module_name}" in other_content or \
               f"import {module_name}" in other_content:
                rel_path = py_file.relative_to(ERIRPG_DIR.parent)
                deps["imported_by"].append(str(rel_path))
        except Exception:
            pass

    return deps


def find_markdown_dependencies(content: str, cmd_name: str) -> dict:
    """Find dependencies for a markdown command file."""
    deps = {
        "calls": [],
        "called_by": [],
        "cli_commands": [],
    }

    # Find /coder: references
    coder_refs = re.findall(r'/coder:([a-z-]+)', content)
    deps["calls"] = list(set(coder_refs) - {cmd_name})

    # Find CLI commands
    cli_refs = re.findall(r'(?:erirpg|python[3]? -m erirpg(?:\.[a-z_]+)?)\s+([a-z_-]+)', content)
    deps["cli_commands"] = list(set(cli_refs))

    # Find eri: references
    eri_refs = re.findall(r'/eri:([a-z-]+)', content)
    if eri_refs:
        deps["eri_commands"] = list(set(eri_refs))

    # Check other commands for references
    for cmd_file in COMMANDS_DIR.glob("*.md"):
        if cmd_file.stem == cmd_name:
            continue
        try:
            other_content = cmd_file.read_text()
            if f"/coder:{cmd_name}" in other_content:
                deps["called_by"].append(cmd_file.stem)
        except Exception:
            pass

    return deps


def verify_python(path: Path, content: str) -> list:
    """Verify a Python file."""
    checks = []
    all_passed = True

    # Check 1: File exists
    check1 = {"name": "file_exists", "passed": path.exists()}
    if not check1["passed"]:
        check1["error"] = f"File not found: {path}"
        all_passed = False
    checks.append(check1)

    if not path.exists():
        return checks

    # Check 2: Not empty
    check2 = {"name": "not_empty", "passed": len(content.strip()) > 0}
    if not check2["passed"]:
        check2["error"] = "File is empty"
        all_passed = False
    checks.append(check2)

    # Check 3: Python syntax valid
    try:
        compile(content, str(path), 'exec')
        check3 = {"name": "python_syntax", "passed": True}
    except SyntaxError as e:
        check3 = {"name": "python_syntax", "passed": False, "error": f"Syntax error: {e}"}
        all_passed = False
    checks.append(check3)

    # Check 4: Can import (more thorough check)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        check4 = {"name": "py_compile", "passed": result.returncode == 0}
        if not check4["passed"]:
            check4["error"] = result.stderr.strip() or "py_compile failed"
            all_passed = False
    except Exception as e:
        check4 = {"name": "py_compile", "passed": False, "error": str(e)}
        all_passed = False
    checks.append(check4)

    # Check 5: Reasonable size
    check5 = {"name": "reasonable_size", "passed": 50 < len(content) < 500000}
    if not check5["passed"]:
        check5["error"] = f"Suspicious size: {len(content)} bytes"
        all_passed = False
    checks.append(check5)

    return checks


def verify_markdown(path: Path, content: str) -> list:
    """Verify a markdown file."""
    checks = []

    # Check 1: File exists
    check1 = {"name": "file_exists", "passed": path.exists()}
    if not check1["passed"]:
        check1["error"] = f"File not found: {path}"
    checks.append(check1)

    if not path.exists():
        return checks

    # Check 2: Not empty
    check2 = {"name": "not_empty", "passed": len(content.strip()) > 0}
    if not check2["passed"]:
        check2["error"] = "File is empty"
    checks.append(check2)

    # Check 3: Valid frontmatter (if present)
    if content.startswith("---"):
        parts = content.split("---", 2)
        check3 = {"name": "valid_frontmatter", "passed": len(parts) >= 3}
        if not check3["passed"]:
            check3["error"] = "Frontmatter not properly closed"
        checks.append(check3)

    # Check 4: Balanced code blocks
    code_blocks = content.count("```")
    check4 = {"name": "balanced_code_blocks", "passed": code_blocks % 2 == 0}
    if not check4["passed"]:
        check4["error"] = f"Unbalanced code blocks: {code_blocks} backtick sequences"
    checks.append(check4)

    # Check 5: Reasonable size
    check5 = {"name": "reasonable_size", "passed": 100 < len(content) < 100000}
    if not check5["passed"]:
        check5["error"] = f"Suspicious size: {len(content)} bytes"
    checks.append(check5)

    # Check 6: Has structure
    has_structure = any([
        "<process>" in content,
        "## Process" in content,
        "## Execution" in content,
        "## Usage" in content,
        "## Steps" in content,
        "def " in content,  # For mixed files
    ])
    check6 = {"name": "has_structure", "passed": has_structure}
    if not check6["passed"]:
        check6["warning"] = "No standard structure found"
    checks.append(check6)

    return checks


def analyze(target: str, output_json: bool = False) -> dict:
    """Phase 1: ANALYZE - Before any changes."""
    file_path, display_name, file_type = resolve_target(target)
    meta_dir = get_meta_dir(target)

    result = {
        "command": "meta-edit",
        "phase": "analyze",
        "target": target,
        "file_path": str(file_path),
        "display_name": display_name,
        "file_type": file_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not file_path.exists():
        result["error"] = f"File not found: {file_path}"
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    content = file_path.read_text()
    result["line_count"] = len(content.splitlines())
    result["size_bytes"] = len(content.encode())

    # Find dependencies based on file type
    if file_type == "python":
        result["dependencies"] = find_python_dependencies(file_path, content)
    else:
        cmd_name = display_name.split(":")[-1] if ":" in display_name else file_path.stem
        result["dependencies"] = find_markdown_dependencies(content, cmd_name)

    # Create meta-edit directory and snapshot
    meta_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot_name = f"{file_path.name}.snapshot.{timestamp}"
    snapshot_path = meta_dir / snapshot_name
    shutil.copy2(file_path, snapshot_path)
    result["snapshot"] = str(snapshot_path)

    # Write ANALYSIS.md
    deps = result["dependencies"]
    if file_type == "python":
        deps_text = f"""### Imports
{chr(10).join(f"- {i}" for i in deps.get('erirpg_imports', [])) or "- None (erirpg-specific)"}

### Imported By
{chr(10).join(f"- {i}" for i in deps.get('imported_by', [])) or "- None detected"}"""
    else:
        deps_text = f"""### Commands This Calls
{chr(10).join(f"- /coder:{c}" for c in deps.get('calls', [])) or "- None"}

### CLI Commands Used
{chr(10).join(f"- `erirpg {c}`" for c in deps.get('cli_commands', [])) or "- None"}

### Called By
{chr(10).join(f"- /coder:{c}" for c in deps.get('called_by', [])) or "- None detected"}"""

    analysis_content = f"""# Analysis: {display_name}

Generated: {result['timestamp']}
Source: {file_path}
Type: {file_type}
Snapshot: {snapshot_path}

## Current State

- **Lines**: {result['line_count']}
- **Size**: {result['size_bytes']} bytes
- **Type**: {file_type}

## Dependencies

{deps_text}

## Snapshot Created

```
{snapshot_path}
```

To restore: `cp "{snapshot_path}" "{file_path}"`

## Next Step

Run: `python3 -m erirpg.commands.meta_edit plan "{target}" --intent "<what you want to change>"`
"""

    (meta_dir / "ANALYSIS.md").write_text(analysis_content)
    result["analysis_file"] = str(meta_dir / "ANALYSIS.md")
    result["message"] = f"Analysis complete. Snapshot: {snapshot_path}"

    if output_json:
        print(json.dumps(result, indent=2))
    return result


def plan(target: str, intent: str, output_json: bool = False) -> dict:
    """Phase 2: PLAN - Requires user approval."""
    file_path, display_name, file_type = resolve_target(target)
    meta_dir = get_meta_dir(target)

    result = {
        "command": "meta-edit",
        "phase": "plan",
        "target": target,
        "intent": intent,
        "file_path": str(file_path),
        "file_type": file_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not (meta_dir / "ANALYSIS.md").exists():
        result["error"] = "No analysis found. Run analyze phase first."
        result["fix"] = f'python3 -m erirpg.commands.meta_edit analyze "{target}"'
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    snapshots = sorted(meta_dir.glob(f"{file_path.name}.snapshot.*"))
    if not snapshots:
        result["error"] = "No snapshot found."
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    latest_snapshot = snapshots[-1]
    result["snapshot"] = str(latest_snapshot)

    content = file_path.read_text()

    # Build risks based on file type
    risks = []
    if file_type == "python":
        deps = find_python_dependencies(file_path, content)
        if deps.get("imported_by"):
            risks.append(f"Files that import this: {', '.join(deps['imported_by'][:5])}")
        if "def " in content and ("class " in intent.lower() or "function" in intent.lower()):
            risks.append("Changing function signatures may break callers")
        risks.append("Python changes require syntax verification")
    else:
        cmd_name = display_name.split(":")[-1] if ":" in display_name else file_path.stem
        deps = find_markdown_dependencies(content, cmd_name)
        if deps.get("called_by"):
            risks.append(f"Commands that depend on this: {', '.join(deps['called_by'])}")
        if deps.get("cli_commands"):
            risks.append(f"CLI integration: {', '.join(deps['cli_commands'])}")

    # Verification steps
    if file_type == "python":
        verifications = [
            "1. Python syntax is valid (compile check)",
            "2. py_compile passes",
            "3. File is not empty",
            "4. Reasonable file size",
            f"5. Rollback: cp \"{latest_snapshot}\" \"{file_path}\""
        ]
    else:
        verifications = [
            "1. Markdown is valid",
            "2. Code blocks are balanced",
            "3. File is not empty",
            f"4. Rollback: cp \"{latest_snapshot}\" \"{file_path}\""
        ]

    plan_content = f"""# Plan: Modify {display_name}

Generated: {result['timestamp']}
Type: {file_type}

## Intent

{intent}

## Current File

- **Path**: {file_path}
- **Snapshot**: {latest_snapshot}

## Risk Assessment

{chr(10).join(f"- ⚠️ {r}" for r in risks) or "- No significant risks detected"}

## Verification Steps

{chr(10).join(verifications)}

## Instructions for Claude

**DO NOT EDIT THE FILE YET.**

1. Read the current file: `{file_path}`
2. Show EXACTLY what you plan to change
3. Wait for explicit approval
4. Then run: `python3 -m erirpg.commands.meta_edit execute "{target}"`

## Approval Required

User must approve before execution.
"""

    (meta_dir / "PLAN.md").write_text(plan_content)
    result["plan_file"] = str(meta_dir / "PLAN.md")
    result["risks"] = risks
    result["requires_approval"] = True
    result["current_file"] = str(file_path)
    result["message"] = "Plan created. Show changes and wait for approval."

    if output_json:
        print(json.dumps(result, indent=2))
    return result


def execute(target: str, output_json: bool = False) -> dict:
    """Phase 3: EXECUTE - Only after approval."""
    file_path, display_name, file_type = resolve_target(target)
    meta_dir = get_meta_dir(target)

    result = {
        "command": "meta-edit",
        "phase": "execute",
        "target": target,
        "file_path": str(file_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not (meta_dir / "PLAN.md").exists():
        result["error"] = "No plan found. Run plan phase first."
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    snapshots = sorted(meta_dir.glob(f"{file_path.name}.snapshot.*"))
    if snapshots:
        result["snapshot"] = str(snapshots[-1])
        result["rollback_command"] = f'cp "{snapshots[-1]}" "{file_path}"'

    result["file_to_edit"] = str(file_path)
    result["execution_approved"] = True
    result["instructions"] = [
        f"1. Edit {file_path}",
        "2. Run verify phase after editing",
        f'3. Verify: python3 -m erirpg.commands.meta_edit verify "{target}"'
    ]
    result["message"] = f"Execution approved. Edit {file_path} then verify."

    if output_json:
        print(json.dumps(result, indent=2))
    return result


def verify(target: str, output_json: bool = False) -> dict:
    """Phase 4: VERIFY - Required, auto-rollback on failure."""
    file_path, display_name, file_type = resolve_target(target)
    meta_dir = get_meta_dir(target)

    result = {
        "command": "meta-edit",
        "phase": "verify",
        "target": target,
        "file_path": str(file_path),
        "file_type": file_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    snapshots = sorted(meta_dir.glob(f"{file_path.name}.snapshot.*"))
    snapshot = snapshots[-1] if snapshots else None

    content = file_path.read_text() if file_path.exists() else ""

    # Run appropriate verification
    if file_type == "python":
        checks = verify_python(file_path, content)
    else:
        checks = verify_markdown(file_path, content)

    all_passed = all(c.get("passed", False) for c in checks if "error" in c or c.get("passed") is not None)
    # More precise: fail if any check has passed=False and has an error
    all_passed = not any(c.get("passed") == False and "error" in c for c in checks)

    result["checks"] = checks
    result["all_passed"] = all_passed

    if not all_passed and snapshot:
        shutil.copy2(snapshot, file_path)
        result["rolled_back"] = True
        result["message"] = f"VERIFICATION FAILED. Rolled back from {snapshot}"
    elif not all_passed:
        result["rolled_back"] = False
        result["message"] = "VERIFICATION FAILED. No snapshot for rollback!"
    else:
        result["message"] = "All checks passed. Changes verified."
        result["snapshot_kept"] = str(snapshot) if snapshot else None

    # Write VERIFY.md
    verify_content = f"""# Verification: {display_name}

Generated: {result['timestamp']}
Type: {file_type}
Status: {"✅ PASSED" if all_passed else "❌ FAILED"}

## Checks

| Check | Status | Details |
|-------|--------|---------|
{chr(10).join(f"| {c['name']} | {'✅' if c.get('passed') else '❌'} | {c.get('error', c.get('warning', 'OK'))} |" for c in checks)}

## Result

{"All checks passed." if all_passed else "FAILED: " + ("Rolled back." if result.get('rolled_back') else "Manual fix needed.")}
"""

    (meta_dir / "VERIFY.md").write_text(verify_content)
    result["verify_file"] = str(meta_dir / "VERIFY.md")

    if output_json:
        print(json.dumps(result, indent=2))
    return result


def rollback(target: str, output_json: bool = False) -> dict:
    """Manual rollback to snapshot."""
    file_path, display_name, _ = resolve_target(target)
    meta_dir = get_meta_dir(target)

    result = {
        "command": "meta-edit",
        "phase": "rollback",
        "target": target,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    snapshots = sorted(meta_dir.glob(f"{file_path.name}.snapshot.*"))
    if not snapshots:
        result["error"] = "No snapshot found"
        if output_json:
            print(json.dumps(result, indent=2))
        return result

    latest = snapshots[-1]
    shutil.copy2(latest, file_path)
    result["rolled_back_from"] = str(latest)
    result["rolled_back_to"] = str(file_path)
    result["message"] = f"Rolled back from {latest.name}"

    if output_json:
        print(json.dumps(result, indent=2))
    return result


def status(target: str, output_json: bool = False) -> dict:
    """Show current meta-edit status."""
    file_path, display_name, file_type = resolve_target(target)
    meta_dir = get_meta_dir(target)

    result = {
        "command": "meta-edit",
        "phase": "status",
        "target": target,
        "file_path": str(file_path),
        "display_name": display_name,
        "file_type": file_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result["file_exists"] = file_path.exists()
    result["meta_dir_exists"] = meta_dir.exists()

    if meta_dir.exists():
        result["has_analysis"] = (meta_dir / "ANALYSIS.md").exists()
        result["has_plan"] = (meta_dir / "PLAN.md").exists()
        result["has_verify"] = (meta_dir / "VERIFY.md").exists()
        result["snapshots"] = [s.name for s in sorted(meta_dir.glob("*.snapshot.*"))]

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
        result["next_step"] = f'python3 -m erirpg.commands.meta_edit analyze "{target}"'

    if output_json:
        print(json.dumps(result, indent=2))
    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if len(args) < 1:
        result = {
            "error": "Usage: meta_edit <phase> <target> [options]",
            "phases": ["analyze", "plan", "execute", "verify", "rollback", "status"],
            "targets": [
                "init (coder command shorthand)",
                "erirpg/statusline.py (erirpg code)",
                "/full/path/to/file.py (any file)",
                "statusline (erirpg module shorthand)",
            ],
            "examples": [
                "python3 -m erirpg.commands.meta_edit analyze init",
                "python3 -m erirpg.commands.meta_edit analyze erirpg/statusline.py",
                'python3 -m erirpg.commands.meta_edit plan statusline --intent "Add active project display"',
            ]
        }
        print(json.dumps(result, indent=2))
        return

    phase = args[0]

    if phase == "analyze":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit analyze <target>"}, indent=2))
            return
        analyze(args[1], output_json=output_json)

    elif phase == "plan":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit plan <target> --intent '<changes>'"}, indent=2))
            return
        intent = None
        for i, arg in enumerate(sys.argv):
            if arg == "--intent" and i + 1 < len(sys.argv):
                intent = sys.argv[i + 1]
                break
        if not intent:
            print(json.dumps({"error": "--intent required"}, indent=2))
            return
        plan(args[1], intent, output_json=output_json)

    elif phase == "execute":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit execute <target>"}, indent=2))
            return
        execute(args[1], output_json=output_json)

    elif phase == "verify":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit verify <target>"}, indent=2))
            return
        verify(args[1], output_json=output_json)

    elif phase == "rollback":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit rollback <target>"}, indent=2))
            return
        rollback(args[1], output_json=output_json)

    elif phase == "status":
        if len(args) < 2:
            print(json.dumps({"error": "Usage: meta_edit status <target>"}, indent=2))
            return
        status(args[1], output_json=output_json)

    else:
        print(json.dumps({"error": f"Unknown phase: {phase}"}, indent=2))


if __name__ == "__main__":
    main()
