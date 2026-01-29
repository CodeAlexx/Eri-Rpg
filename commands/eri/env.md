---
description: "Show project environment (test, lint, build commands)"
user_invocable: true
---

<env-command>

# /eri:env - Project Environment

Show the configured environment for the current or specified project.

## Usage

```
/eri:env [project]
```

## What to Do

1. Run the CLI command:
   ```bash
   python3 -m erirpg.cli env <project> --show
   ```

2. Display the results showing:
   - Runner (uv, pip, cargo, npm, etc.)
   - Test command
   - Lint command
   - Build command
   - Python path
   - Environment variables

## Example Output

```
Environment for myproject:
Runner: uv

Commands:
  test: uv run pytest
  lint: uv run ruff check
  format: uv run ruff format

Paths:
  python: .venv/bin/python
  venv: .venv
  test_dir: tests
```

## Setting Environment

If not configured, suggest auto-detection:
```bash
python3 -m erirpg.cli env <project> --detect
```

Or manual setup:
```bash
python3 -m erirpg.cli env <project> --set test "uv run pytest"
python3 -m erirpg.cli env <project> --set lint "uv run ruff check"
```

</env-command>
