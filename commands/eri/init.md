---
name: eri:init
description: Initialize a new EriRPG project
argument-hint: "<name> [--path <dir>] [--tier lite|standard|full]"
---

<action>
Run this command to initialize the project:

```bash
python3 -m erirpg.cli init $ARGUMENTS
```

If no arguments provided, ask the user for:
1. Project name
2. Path (default: current directory)
3. Tier (default: lite)

After initialization, offer to:
- Index the project: `python3 -m erirpg.cli index <name>`
- Install hooks: `python3 -m erirpg.cli install`
</action>
