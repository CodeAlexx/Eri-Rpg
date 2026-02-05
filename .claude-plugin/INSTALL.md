# EriRPG Plugin Installation

Install the EriRPG plugin for Claude Code.

## Prerequisites

1. **Python 3.10 or later**
2. **Claude Code CLI** installed
3. **EriRPG repository** cloned

## Installation Steps

### 1. Install Python Package

```bash
cd /path/to/eri-rpg
pip install -e .
```

This makes the `erirpg` package importable and provides the `eri-rpg` CLI.

**Verify:**
```bash
python3 -c "import erirpg; print('OK')"
eri-rpg --version
```

### 2. Validate Plugin Structure

```bash
eri-rpg plugin build --check
```

Should output: "Plugin structure valid"

### 3. Load Plugin

**Option A: Temporary (for testing)**
```bash
claude --plugin-dir /path/to/eri-rpg/.claude-plugin
```

**Option B: Permanent**

Add to `~/.claude/settings.json`:
```json
{
  "pluginDirs": [
    "/path/to/eri-rpg/.claude-plugin"
  ]
}
```

### 4. Verify Installation

In Claude Code session:
```
/coder:init
```

Should show project context recovery.

## Testing

```bash
# Check plugin info
eri-rpg plugin info

# Validate structure
eri-rpg plugin build --check

# Test in Claude Code
claude --plugin-dir /path/to/eri-rpg/.claude-plugin
```

## Troubleshooting

### "erirpg module not found"
- Ensure: `pip install -e /path/to/eri-rpg` completed
- Test: `python3 -c "import erirpg; print('OK')"`

### "Hook not executable"
- Run: `chmod +x .claude-plugin/hooks/*`

### "Version mismatch"
- Run: `eri-rpg plugin build` to see details
- plugin.json version must match pyproject.toml

### "Plugin not loading"
- Check Claude Code recognizes plugin directory
- Verify hooks have `#!/bin/bash` shebang
- Check PYTHONPATH includes erirpg package

## What Gets Loaded

| Type | Count | Examples |
|------|-------|----------|
| Skills | 6 | /coder:plan-phase, /coder:execute-phase |
| Agents | 10 | planner, executor, verifier |
| Hooks | 4 | pretooluse, sessionstart |

## Alternative: Direct Install

Instead of the plugin, you can install directly:

```bash
eri-rpg install
```

This copies skills/agents/hooks to `~/.claude/` with shorter command names.

## Uninstallation

Remove from `~/.claude/settings.json` pluginDirs array.

Or if using direct install:
```bash
eri-rpg uninstall
```
