# EriRPG

**Cross-project feature transplant tool for Claude Code.**

EriRPG helps you transplant features between codebases by:
- Registering external projects with paths (no web search!)
- Indexing codebases to build dependency graphs
- Finding capabilities in code via local search
- Extracting features as self-contained units
- Planning transplants with mappings and wiring
- Generating minimal context for Claude Code

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Register your projects
eri-rpg add onetrainer /path/to/onetrainer --lang python
eri-rpg add eritrainer /path/to/eritrainer --lang python

# Index them
eri-rpg index onetrainer
eri-rpg index eritrainer

# Find a capability
eri-rpg find onetrainer "24GB Klein training"

# Extract it
eri-rpg extract onetrainer "24GB Klein training" -o klein_memory.json

# Plan the transplant
eri-rpg plan klein_memory.json eritrainer

# Generate context for Claude Code
eri-rpg context klein_memory.json eritrainer

# Give the context file to Claude Code...

# Validate
eri-rpg validate
```

## Commands

### Setup

| Command | Description |
|---------|-------------|
| `eri-rpg add <name> <path>` | Register a project |
| `eri-rpg remove <name>` | Remove a project |
| `eri-rpg list` | List registered projects |
| `eri-rpg index <name>` | Index a project |

### Exploration

| Command | Description |
|---------|-------------|
| `eri-rpg show <project>` | Show project structure |
| `eri-rpg find <project> "<query>"` | Find modules matching query |
| `eri-rpg impact <project> <module>` | Analyze change impact |

### Transplant

| Command | Description |
|---------|-------------|
| `eri-rpg extract <project> "<query>" -o <file>` | Extract a feature |
| `eri-rpg plan <feature.json> <target>` | Plan transplant |
| `eri-rpg context <feature.json> <target>` | Generate context |

### Orchestration

| Command | Description |
|---------|-------------|
| `eri-rpg do "<task>"` | Smart mode - figure out steps |
| `eri-rpg status` | Show current status |
| `eri-rpg validate` | Check implementation |
| `eri-rpg diagnose` | Analyze what went wrong |
| `eri-rpg reset` | Reset state to idle |

## Smart Mode

The `do` command understands natural language tasks:

```bash
# Transplant a feature
eri-rpg do "transplant 24GB Klein training from onetrainer to eritrainer"

# Find something
eri-rpg do "find gradient checkpointing in onetrainer"

# Impact analysis
eri-rpg do "what uses zimage.py in eritrainer"
```

## How It Works

1. **Index** parses your codebase with Python's `ast` module
2. **Find** uses token-based similarity matching (no LLM needed)
3. **Extract** includes transitive dependencies automatically
4. **Plan** maps source interfaces to target, identifies wiring
5. **Context** generates a focused markdown file (<5K tokens)

The context file is what you give to Claude Code - it has:
- Source code from the feature
- Target interfaces (signatures only, not full code)
- Transplant plan with mappings and wiring tasks

## Token Efficiency

| What | Tokens |
|------|--------|
| Full project dump | 50-100K (BAD) |
| EriRPG context | 3-8K (GOOD) |

## Philosophy

- **No LLM calls** - Pure Python utility
- **Read local code** - Never web search for local projects
- **Minimal deps** - Just `click` for CLI
- **Token efficient** - Context <5K tokens
- **Self-improving** - Can index and improve itself

## License

MIT
