---
name: eri:mode
description: Show or change project mode and tier
argument-hint: "<project> [--bootstrap|--maintain] [--lite|--standard|--full]"
---

<action>
Run this command to show or change mode/tier:

```bash
python3 -m erirpg.cli mode $ARGUMENTS
```

Examples:
- Show current: `python3 -m erirpg.cli mode myapp`
- Upgrade tier: `python3 -m erirpg.cli mode myapp --full`
- Disable enforcement: `python3 -m erirpg.cli mode myapp --bootstrap`
</action>
