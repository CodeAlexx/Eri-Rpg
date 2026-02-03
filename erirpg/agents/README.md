# Agent Specs Directory

This directory stores agent specifications for **version control only**.

## Architecture

| Location | Purpose | Naming |
|----------|---------|--------|
| `erirpg/agents/` | Version control storage | `eri-*.md` prefix |
| `~/.eri-rpg/agents/` | Production loading | `*.md` (no prefix) |

## How It Works

1. Agent specs are developed and committed here with `eri-` prefix
2. Install/sync copies them to `~/.eri-rpg/agents/` without prefix
3. `prompts.py` loads from `~/.eri-rpg/agents/` at runtime
4. `ERI_AGENTS_DIR` env var can override production path

## Why This Design

- **Committable**: `~/.claude/` skills can't be committed; this can
- **Separation**: Repo storage vs runtime loading are distinct
- **Override**: Users can customize without modifying repo

## Files

- `eri-*.md` - Agent specifications (planner, executor, verifier, etc.)
- `behavior-extractor.md` - Special case, no prefix
- `prompts.py` - Loads agents from production directory
- `spawn.py` - Convenience functions for spawning agents

## Adding New Agents

1. Create `eri-{name}.md` here
2. Add to `AGENT_PROMPTS` dict in `prompts.py` (without prefix)
3. Add spawn helper to `spawn.py` if needed
4. Run install to copy to `~/.eri-rpg/agents/{name}.md`
