---
name: eri:spec
description: Manage feature specifications
argument-hint: "<project> [new|list|show] [name]"
---

<action>
For listing specs:
```bash
python3 -m erirpg.cli spec list $ARGUMENTS
```

For creating new spec:
```bash
python3 -m erirpg.cli spec new <project> "<name>"
```

For showing a spec:
```bash
python3 -m erirpg.cli spec show <project> <spec-id>
```
</action>
