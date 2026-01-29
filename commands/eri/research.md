---
name: eri:research
description: Run research phase before planning
argument-hint: "<project> --goal '<goal>'"
---

<action>
1. Run research command to create template:

```bash
python3 -m erirpg.cli research $ARGUMENTS
```

2. IMMEDIATELY spawn a research agent to fill it in:

Use the Task tool with these parameters:
- subagent_type: "general-purpose"
- description: "Research for EriRPG project"
- prompt: |
    You are a research agent. Your job:

    1. Read the template at: <project_path>/.eri-rpg/research/RESEARCH.md
    2. Use WebSearch to research the goal
    3. Find: best libraries, common pitfalls, architecture patterns, code examples
    4. Fill in ALL sections of RESEARCH.md using the Write tool
    5. Set Confidence to HIGH

    Goal: [insert goal from CLI output]
    Project path: [insert from CLI output]

    Do NOT ask questions. Do the research. Fill the file. Done.

Persona: --persona-analyzer
</action>
