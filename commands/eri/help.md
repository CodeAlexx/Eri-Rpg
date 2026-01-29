---
name: eri:help
description: Get help on any EriRPG topic
argument-hint: "<topic>"
---

# /eri:help - EriRPG Help System

Get guidance on any EriRPG topic.

## Topic: $ARGUMENTS

<instructions>
Based on the topic requested, provide helpful guidance:

1. **If topic is empty or "topics"** - Show available help topics
2. **If topic matches a command** - Explain the command with examples
3. **If topic is a concept** - Explain the concept and how to use it
4. **If topic is a workflow** - Walk through the steps
5. **If topic is a problem** - Troubleshoot and suggest solutions

## Available Help Topics

### Commands (type `/eri:help <command>`)
- `quick` - Quick fix mode for single files
- `execute` - Full agent runs with verification
- `discuss` - Goal clarification discussions
- `learn` / `recall` - Knowledge management
- `decide` / `defer` - Decision tracking
- `spec` / `plan` - Formal specifications
- `verify` / `test` - Verification and testing
- `roadmap` - Long-term planning
- `impact` - Impact analysis before changes
- `cleanup` / `reset` - State management

### Concepts (type `/eri:help <concept>`)
- `tiers` - Lite vs Standard vs Full
- `modes` - Bootstrap vs Maintain
- `decisions` - Decision tracking workflow
- `enforcement` - How hooks protect your code
- `learning` - Knowledge capture and recall
- `verification` - Test verification system
- `waves` - Parallel execution (coming soon)

### Workflows (type `/eri:help <workflow>`)
- `getting-started` - First time setup
- `new-feature` - Implementing a feature
- `bug-fix` - Fixing a bug safely
- `refactor` - Safe refactoring
- `new-project` - Starting fresh
- `resume` - Resuming interrupted work

### Troubleshooting (type `/eri:help <problem>`)
- `blocked` - "I'm blocked by EriRPG"
- `stale` - "Stale runs/state"
- `hooks` - "Hooks not working"
- `tier-error` - "Command requires higher tier"

</instructions>

<action>
Read the user's topic and provide appropriate help:

**For commands:** Read the command file from ~/.claude/commands/eri/{topic}.md and summarize with examples.

**For concepts:** Explain from the POWER_USER_GUIDE.md or config.py.

**For workflows:** Walk through step-by-step.

**For troubleshooting:** Diagnose and provide solutions.

If the topic is unclear, ask a clarifying question or suggest related topics.
</action>

## Quick Reference

```
/eri:help                    # Show all topics
/eri:help quick              # Help with quick fix
/eri:help getting-started    # First time setup
/eri:help blocked            # Troubleshoot blocking
/eri:help tiers              # Explain tier system
```
