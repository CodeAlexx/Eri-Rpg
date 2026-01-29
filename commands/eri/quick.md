---
name: eri:quick
description: Start a quick fix on a single file (snapshots for safety)
argument-hint: "<project> <file> <description>"
---

<action>
Run this command to start a quick fix:

```bash
python3 -m erirpg.cli quick $ARGUMENTS
```

This snapshots the file for safety. After making edits, complete with:
```bash
python3 -m erirpg.cli quick-done <project>
```

Or cancel and restore original:
```bash
python3 -m erirpg.cli quick-cancel <project>
```
</action>
