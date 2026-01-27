# Installation

## Prerequisites

- Python 3.10 or higher
- pip
- git (optional, for rollback features)

## Install from Source

```bash
# Clone the repository
git clone https://github.com/CodeAlexx/Eri-Rpg.git
cd Eri-Rpg

# Install in development mode
pip install -e .

# Or with system packages override (if needed)
pip install -e . --break-system-packages

# Verify installation
eri-rpg --version
eri-rpg --help
```

## Environment Setup

Set the `ERIRPG_ROOT` environment variable for hooks:

```bash
export ERIRPG_ROOT=/path/to/Eri-Rpg
```

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) for persistence.

## Claude Code Integration

To use EriRPG with Claude Code, install the hooks:

1. **Copy hook configuration:**
   ```bash
   # View the hook config
   cat $ERIRPG_ROOT/erirpg/hooks/hooks.json
   ```

2. **Add to Claude Code settings** (`~/.claude/settings.json`):
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Edit|Write|MultiEdit",
           "hooks": [
             {
               "type": "command",
               "command": "python3 ${ERIRPG_ROOT}/erirpg/hooks/pretooluse.py",
               "timeout": 5
             }
           ]
         }
       ],
       "PreCompact": [
         {
           "matcher": ".*",
           "hooks": [
             {
               "type": "command",
               "command": "python3 ${ERIRPG_ROOT}/erirpg/hooks/precompact.py",
               "timeout": 10
             }
           ]
         }
       ],
       "SessionStart": [
         {
           "matcher": ".*",
           "hooks": [
             {
               "type": "command",
               "command": "python3 ${ERIRPG_ROOT}/erirpg/hooks/sessionstart.py",
               "timeout": 5
             }
           ]
         }
       ]
     }
   }
   ```

3. **Optional: Install plugin commands:**
   ```bash
   ln -sf ~/eri-rpg-plugin/commands ~/.claude/commands/eri
   ```

## Verify Installation

```bash
# Check CLI works
eri-rpg list

# Should show empty list or registered projects
# No errors = success

# Test hook (should output JSON)
echo '{"tool_name":"Read","tool_input":{},"cwd":"/tmp"}' | \
  python3 $ERIRPG_ROOT/erirpg/hooks/pretooluse.py
```

## Troubleshooting

### "command not found: eri-rpg"

The package wasn't installed correctly. Try:
```bash
pip install -e /path/to/Eri-Rpg --break-system-packages
```

Or use the module directly:
```bash
python3 -m erirpg.cli --help
```

### Hook errors

If hooks fail, check:
1. `ERIRPG_ROOT` is set correctly
2. Python can import erirpg: `python3 -c "import erirpg"`
3. Hook script is executable and valid

### Module import errors

The `hooks.py` file shadows the `hooks/` directory. This is a known issue.
Hooks must be called as scripts, not imported as modules.

```bash
# This works:
python3 /path/to/erirpg/hooks/pretooluse.py

# This does NOT work:
python3 -m erirpg.hooks.pretooluse
```
