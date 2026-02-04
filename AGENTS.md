# Repository Guidelines

## Project Structure & Module Organization
- `erirpg/` is the main Python package.
  - `cli.py` is the entrypoint; `cli_commands/` wires user-facing CLI commands.
  - `commands/` and `skills/` hold slash-command behavior implementations.
  - `agent/` plus `agents/*.md` define runtime agent logic and versioned agent specs.
  - `ui/` contains the FastAPI server, templates, and static assets.
- `tests/` contains the pytest suite.
- `docs/` stores architecture notes, command references, and user guides.
- `commands/eri/` contains packaged command docs; `specs/` contains design/research specs.

## Build, Test, and Development Commands
- `pip install -e .` installs the project in editable mode.
- `pip install -e ".[dev,ui]"` adds lint/test tools and UI dependencies.
- `eri-rpg --help` (or `python -m erirpg.cli --help`) checks CLI wiring locally.
- `python -m pytest tests/ -v` runs the full test suite.
- `python -m pytest tests/test_runner.py -v` runs a focused test file.
- `ruff check .` runs linting (including import ordering rules).

## Coding Style & Naming Conventions
- Target Python 3.10+, use 4-space indentation, and keep line length near 100 (see `pyproject.toml`).
- Follow Ruff lint groups enabled here: `E`, `F`, `I`, `W`.
- Use `snake_case` for modules/functions, `PascalCase` for classes, and `UPPER_CASE` for constants.
- Keep CLI orchestration in `erirpg/cli_commands/`; move reusable logic into core modules.
- Add short docstrings/comments only when behavior is not obvious from code.

## Testing Guidelines
- Use `pytest`; name files `test_<feature>.py` and keep them under `tests/`.
- Add regression tests with bug fixes (expected behavior + edge/failure path).
- For CLI/parser changes, include targeted tests and relevant integration coverage.
- Run `python -m pytest tests/ -v` before opening a pull request.

## Commit & Pull Request Guidelines
- Follow Conventional Commit patterns used in history: `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `chore: ...`.
- Keep commits small and imperative (example: `fix(workflow): require runtime verification`).
- PRs should include: problem statement, key changes, test commands/results, and linked issue(s).
- For UI updates in `erirpg/ui/`, attach screenshots or a short recording.

## Security & Configuration Tips
- Never commit private/local artifacts: `CLAUDE.md`, `.planning/`, `.eri-rpg/`, `.claude/`, `.env`, or key/cert files.
- Avoid absolute local paths in docs; prefer repo-relative paths or placeholders like `/path/to/project`.
- Run `git status` before push to confirm only intended files are staged.
