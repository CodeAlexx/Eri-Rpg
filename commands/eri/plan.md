---
name: eri:plan
description: Manage execution plans
argument-hint: "<project> [list|show|next]"
---

<action>
For listing plans:
```bash
python3 -m erirpg.cli plan list $ARGUMENTS
```

For showing current plan:
```bash
python3 -m erirpg.cli plan show <project>
```

For advancing to next step:
```bash
python3 -m erirpg.cli plan next <project>
```
</action>
