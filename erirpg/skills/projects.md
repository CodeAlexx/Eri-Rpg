---
name: coder:projects
description: List all registered projects with status
---

<action>
List all projects:

```bash
python3 -m erirpg.cli list
```

Show active project:

```bash
python3 -m erirpg.cli status 2>&1 | head -5
```

Output shows:
- Project name, tier, mode
- Path and language
- Index status
- Which project is currently active
</action>
