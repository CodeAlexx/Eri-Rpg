# EriRPG Requirements

Refined requirements based on research findings.

## Core Problem Statement

Claude Code (with or without GSD) fails at cross-project feature transplant because:

1. **Web search instead of local code** — User says "use onetrainer's flux loader" and Claude searches web for blog posts instead of reading `/home/alex/OneTrainer/modules/modelLoader/flux/`

2. **No project registry** — No way to say "onetrainer lives at /path/to/onetrainer, read THAT"

3. **No dependency graph** — Doesn't know that changing `zimage.py` affects `flux2_klein.py`

4. **Context rot** — Writing file 10, forgot interfaces from file 1

5. **Unwired outputs** — Generated code is 60% right, imports wrong, glue code missing

## Solution: EriRPG

A lean CLI tool (~1500 lines Python) that:
- Registers external projects with paths
- Indexes codebases to build dependency graphs
- Finds capabilities in code via local search
- Extracts features as self-contained units
- Plans transplants between projects
- Generates minimal context for Claude Code

**Key insight:** This tool has NO LLM. It's pure Python. Claude Code is the LLM.

## Use Cases

### UC-1: Register External Projects
```bash
eri-rpg add onetrainer /home/alex/OneTrainer/modules --lang python
eri-rpg add eritrainer /home/alex/OneTrainer/eritrainer --lang python
eri-rpg list
# Output:
# onetrainer: /home/alex/OneTrainer/modules (Python, indexed)
# eritrainer: /home/alex/OneTrainer/eritrainer (Python, indexed)
```

### UC-2: Index a Project
```bash
eri-rpg index onetrainer
# Output:
# Indexing onetrainer...
# Found 200+ Python files
# Extracted 500+ interfaces
# Built dependency graph (1200 edges)
# Saved to /home/alex/OneTrainer/modules/.eri-rpg/graph.json
```

### UC-3: Find a Capability
```bash
eri-rpg find onetrainer "24GB Klein training without quantization"
# Output:
# Matching modules:
# 1. modules/model/FluxModel.py (0.85) - "Flux model with memory optimization"
# 2. modules/util/offload/ModelOffloader.py (0.72) - "Layer offloading for large models"
# 3. modules/module/quantized/ (0.65) - "Quantization utilities"
```

### UC-4: Extract a Feature
```bash
eri-rpg extract onetrainer "24GB Klein training" -o klein_memory.json
# Output:
# Extracting feature...
# Primary: modules/model/FluxModel.py
# Dependencies:
#   - modules/util/offload/ModelOffloader.py
#   - modules/module/EMAModule.py
# Interfaces: FluxModel, ModelOffloader, EMAModule
# Total: 3 files, 1200 lines
# Saved to klein_memory.json
```

### UC-5: Plan a Transplant
```bash
eri-rpg plan klein_memory.json eritrainer
# Output:
# Transplant plan:
#
# Mappings:
#   FluxModel (onetrainer) → Flux1Model (eritrainer) - ADAPT
#   ModelOffloader (onetrainer) → NEW: utils/offload.py - CREATE
#   EMAModule (onetrainer) → SKIP (already exists)
#
# Wiring:
#   - eritrainer/models/flux1.py: add offload import
#   - eritrainer/training/base.py: add offloader initialization
#
# Saved to klein_memory.plan.json
```

### UC-6: Generate Context for Claude Code
```bash
eri-rpg context klein_memory.json eritrainer
# Output:
# Generated context file: .eri-rpg/context/klein_memory.md (4.2K tokens)
#
# Contents:
# - Source code from onetrainer (relevant files)
# - Target interfaces from eritrainer (signatures only)
# - Transplant plan with mappings and wiring
# - NOT the entire target codebase
```

### UC-7: Check Impact
```bash
eri-rpg impact eritrainer models/zimage.py
# Output:
# Impact analysis for eritrainer/models/zimage.py:
#
# Direct dependents:
#   - eritrainer/training/flux2/base.py (imports ZImageModel)
#   - eritrainer/api/routes/training.py (uses zimage)
#
# Transitive dependents:
#   - eritrainer/api/app.py
#   - 3 test files
#
# Risk: MEDIUM (4 files affected)
```

## Token Budgets

| Operation | Max Tokens | Notes |
|-----------|------------|-------|
| Full graph structure | 2-5K | All modules, summaries, deps |
| Single module context | 1-3K | One module + interfaces |
| Feature extraction | 3-8K | Source code + mappings |
| Full codebase dump | NEVER | This is what we're avoiding |

## Data Structures

### Registry (`~/.eri-rpg/registry.json`)
```json
{
  "projects": {
    "onetrainer": {
      "path": "/home/alex/OneTrainer/modules",
      "lang": "python",
      "indexed_at": "2026-01-25T10:30:00Z",
      "graph": "/home/alex/OneTrainer/modules/.eri-rpg/graph.json"
    }
  }
}
```

### Graph (`.eri-rpg/graph.json` per project)
```json
{
  "project": "onetrainer",
  "version": "1.0.0",
  "indexed_at": "2026-01-25T10:30:00Z",
  "modules": {
    "model/FluxModel": {
      "path": "model/FluxModel.py",
      "lang": "python",
      "lines": 423,
      "deps": ["torch", "diffusers", "util/offload"],
      "interfaces": [
        {"name": "FluxModel", "type": "class", "methods": ["forward", "load"]},
        {"name": "create_flux_model", "type": "function", "sig": "def create_flux_model(config) -> FluxModel"}
      ],
      "summary": "Flux model wrapper with memory optimization"
    }
  },
  "edges": [
    {"from": "trainer/GenericTrainer", "to": "model/FluxModel", "type": "imports"}
  ]
}
```

### Feature (extracted unit)
```json
{
  "name": "24gb_klein_training",
  "source": "onetrainer",
  "extracted_at": "2026-01-25T...",
  "components": [
    {"module": "model/FluxModel", "files": ["model/FluxModel.py"], "lines": 423}
  ],
  "requires": [
    {"interface": "Tensor", "from": "torch"}
  ],
  "provides": [
    {"interface": "FluxModel", "type": "class"}
  ],
  "code": {
    "model/FluxModel.py": "... actual code ..."
  }
}
```

## CLI Commands

### Setup
```bash
eri-rpg add <name> <path> [--lang python|rust|ts]
eri-rpg remove <name>
eri-rpg list
eri-rpg index <name>
```

### Exploration
```bash
eri-rpg show <name>                    # Project structure from graph
eri-rpg find <project> "<capability>"  # Find modules
eri-rpg impact <project> <module>      # Impact analysis
```

### Transplant
```bash
eri-rpg extract <project> "<capability>" -o <output.json>
eri-rpg plan <feature.json> <target_project>
eri-rpg context <feature.json> <target_project>
```

### Orchestration
```bash
eri-rpg do "<task>"     # Smart mode - figures out steps
eri-rpg status          # Where am I? What's next?
eri-rpg validate        # Check Claude's work
eri-rpg diagnose        # What went wrong?
```

## Technical Constraints

1. **No LLM calls** — Pure Python utility
2. **Minimal deps** — stdlib + tree-sitter (for non-Python)
3. **~1500 lines** — Lean and focused
4. **Fast indexing** — Seconds, not minutes
5. **Local only** — Never search web

## Self-Improvement Requirement

v1 must be able to:
- Register itself as a project
- Index its own code
- Extract its own modules
- Generate context for improving itself

**Test:** After v1 built, use v1 to build v1.1

## Success Criteria

1. **Token efficient** — Context <5K tokens, not 50K
2. **Local only** — Never searches web for local code
3. **Accurate extraction** — Features include all necessary code
4. **Correct wiring** — Transplant plan identifies all integration points
5. **Self-improving** — Can index and improve itself
6. **Fast** — Index a project in seconds
7. **Simple** — ~1500 lines, no complexity
8. **Guides you** — Tells you when to /clear, validates results
