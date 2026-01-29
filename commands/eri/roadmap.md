---
name: eri:roadmap
description: View and manage project roadmap
argument-hint: "<project> [phase-name] [--must-haves features]"
---

<action>
If just project name provided, show roadmap:
```bash
python3 -m erirpg.cli roadmap $ARGUMENTS
```

If adding a phase (has phase name):
```bash
python3 -m erirpg.cli roadmap-add $ARGUMENTS
```

To advance to next phase:
```bash
python3 -m erirpg.cli roadmap-next <project>
```
</action>
