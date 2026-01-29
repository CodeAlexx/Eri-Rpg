---
name: eri:discuss
description: Start or continue a goal clarification discussion
argument-hint: "<project> <goal>"
---

<action>
Run this command to start/continue a discussion:

```bash
python3 -m erirpg.cli discuss $ARGUMENTS
```

IMPORTANT: One question at a time workflow:
1. Show the user ONLY the first unanswered question
2. Wait for their answer
3. Record it with: `python3 -m erirpg.cli discuss-answer <project> "<goal>" "<question>" "<answer>"`
4. Show the NEXT unanswered question
5. Repeat until all questions answered

DO NOT dump all questions at once. Ask one, wait, record, ask next.

When all questions answered, resolve with:
```bash
python3 -m erirpg.cli discuss-resolve <project>
```
</action>
