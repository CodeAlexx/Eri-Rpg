# RPG Paper Analysis

Analysis of [Repository Planning Graph](https://arxiv.org/abs/2509.16198) concepts for EriRPG design.

## Disclaimer

The paper is recent (2509.16198 suggests late 2025) and no code is available. This analysis is based on the abstract and general repository-level code generation concepts.

## Graph Structure

### Nodes

From the paper abstract, RPG encodes:

| Node Type | What It Represents | Example |
|-----------|-------------------|---------|
| Module | Logical grouping of related code | `memory/`, `training/` |
| File | Single source file | `gradient_checkpoint.py` |
| Function | Callable unit | `checkpoint_forward()` |
| Class | Type definition | `GradientCheckpointer` |
| Interface | Public contract | Method signatures, exports |

### Edges

| Edge Type | Meaning | Example |
|-----------|---------|---------|
| contains | Hierarchy | `module → file`, `file → class` |
| imports | Dependency | `trainer.py → gradient_checkpoint.py` |
| calls | Runtime | `train_step() → checkpoint_forward()` |
| inherits | OOP | `FluxTrainer extends BaseTrainer` |
| data_flow | Value passing | `config → trainer → checkpoint` |

### Example Graph

```
onetrainer/ (module)
├── memory/ (module)
│   └── gradient_checkpoint.py (file)
│       ├── GradientCheckpointer (class)
│       │   ├── __init__ (function)
│       │   └── forward (function)
│       └── checkpoint_forward (function)
│
└── training/ (module)
    └── trainer.py (file)
        └── Trainer (class)
            └── train_step (function)
                └── [calls] → checkpoint_forward
```

## Key Operations

### 1. Topological Sort (Generation Order)

When generating code, order matters. Can't use `GradientCheckpointer` before it exists.

```
Dependencies:
  trainer.py → gradient_checkpoint.py
  gradient_checkpoint.py → torch

Generation order (topological):
  1. torch (external, assumed)
  2. gradient_checkpoint.py
  3. trainer.py
```

**For EriRPG:** When extracting a feature, include dependencies in correct order. When transplanting, generate in dependency order.

### 2. Impact Zone Analysis

"If I change X, what breaks?"

```
Impact analysis for gradient_checkpoint.py:

Direct dependents:
  - trainer.py (imports GradientCheckpointer)
  - klein_model.py (imports checkpoint_forward)

Transitive dependents:
  - training_loop.py (uses Trainer)
  - main.py (uses training_loop)

Risk assessment:
  - 2 direct impacts
  - 4 total impacts
  - High centrality - changes ripple widely
```

**For EriRPG:** `eri-rpg impact zimage_pipeline` shows what modules depend on it, helping users understand change risk.

### 3. Interface Contracts

What does a module promise?

```yaml
module: memory/gradient_checkpoint
provides:
  - class GradientCheckpointer
    - __init__(self, model, checkpoint_layers)
    - forward(self, *args) -> Tensor
  - function checkpoint_forward(fn, *args) -> Any
requires:
  - torch.Tensor
  - torch.nn.Module
```

**For EriRPG:** Track interfaces for compatibility checking during transplant.

### 4. Dependency Tracking

Two types:

**Static (import-time):**
```python
from memory.gradient_checkpoint import GradientCheckpointer
# trainer.py statically depends on gradient_checkpoint.py
```

**Dynamic (runtime):**
```python
def get_checkpointer(config):
    if config.use_gradient_checkpointing:
        return GradientCheckpointer(model)
    return None
# Conditional dependency - harder to track statically
```

**For EriRPG:** Focus on static dependencies (AST analysis). Note that dynamic dependencies exist but are harder to capture.

## Useful for EriRPG

### Adopt Directly

1. **Dependency Graph**
   - Modules as nodes
   - Imports as edges
   - Build via AST parsing

2. **Impact Analysis**
   - BFS/DFS from changed module
   - Show all affected modules
   - Assess change risk

3. **Generation Order**
   - Topological sort for correct sequencing
   - Dependencies first, dependents later

4. **Interface Extraction**
   - Classes, functions, exports
   - Signatures for compatibility checking

### Adapt for Our Use Case

1. **Not Full Code Generation**
   - Paper generates entire repositories
   - We transplant features between existing repos
   - Focus on extraction + integration, not generation

2. **Not LLM-Driven Planning**
   - Paper uses LLM for planning phases
   - We use deterministic graph operations
   - LLM (Claude Code) only for final implementation

3. **Cross-Project Graphs**
   - Paper works within single repo
   - We need cross-project capability matching
   - Graph spans multiple registered projects

## Data Structure Design

Based on RPG concepts:

```json
{
  "project": "onetrainer",
  "modules": {
    "memory/gradient_checkpoint": {
      "path": "memory/gradient_checkpoint.py",
      "type": "module",
      "interfaces": [
        {
          "name": "GradientCheckpointer",
          "type": "class",
          "methods": ["__init__", "forward"]
        },
        {
          "name": "checkpoint_forward",
          "type": "function",
          "signature": "def checkpoint_forward(fn, *args)"
        }
      ],
      "deps": ["torch"],
      "summary": "Gradient checkpointing for memory optimization"
    }
  },
  "edges": [
    {
      "from": "training/trainer",
      "to": "memory/gradient_checkpoint",
      "type": "imports",
      "specifics": ["GradientCheckpointer", "checkpoint_forward"]
    }
  ]
}
```

## Key Takeaway

RPG provides the theoretical foundation:
- **Graph structure** for representing codebases
- **Topological sort** for generation order
- **Impact analysis** for change understanding
- **Interface contracts** for compatibility

EriRPG applies these concepts to cross-project feature transplant, not full repository generation.
