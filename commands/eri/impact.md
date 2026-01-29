---
name: eri:impact
description: Analyze impact of changing a module
argument-hint: "<project> <file>"
---

<action>
Run this command to analyze impact:

```bash
python3 -m erirpg.cli impact $ARGUMENTS
```

This shows what depends on the file and what might break if you change it.
</action>
