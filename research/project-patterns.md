# Project Patterns Analysis

Analysis of user's project codebases for EriRPG design.

## Projects Analyzed

| Project | Path | Language | Lines | Files |
|---------|------|----------|-------|-------|
| EriTrainer | `/home/alex/OneTrainer/eritrainer/` | Python | ~43K | ~80 |
| OneTrainer | `/home/alex/OneTrainer/modules/` | Python | ~58K | ~200+ |

## EriTrainer Structure

```
eritrainer/
├── core/              # Core abstractions
│   ├── interfaces.py  # BaseModel, ModelType, etc.
│   └── config.py      # Configuration classes
├── models/            # Model wrappers (one per architecture)
│   ├── flux1.py
│   ├── flux2.py
│   ├── flux2_klein.py
│   ├── zimage.py
│   ├── sdxl.py
│   ├── sd15.py
│   └── ltx2.py
├── adapters/          # LoRA/LyCORIS adapters
│   ├── base.py
│   ├── lora.py
│   ├── lycoris/
│   └── manager.py
├── training/          # Training logic
│   └── flux2/
│       └── base.py
├── utils/             # Utilities
│   ├── factory.py
│   └── quantization.py
├── api/               # Web API
│   ├── app.py
│   └── routes/
└── tests/             # Test files
```

### Patterns

**Module Organization:**
- One file per model architecture (`zimage.py`, `flux1.py`)
- Clear separation: core → models → training → api
- Factory pattern for model creation

**Import Style:**
```python
# Relative imports within package
from eritrainer.core.interfaces import BaseModel, ModelType
from eritrainer.utils import factory

# External dependencies
from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler
from transformers import Qwen2Tokenizer, Qwen3ForCausalLM
```

**Interface Pattern:**
```python
class BaseModel(ABC):
    """Abstract base for all model wrappers."""

    @abstractmethod
    def forward(self, batch: Dict[str, Any]) -> torch.Tensor:
        """Forward pass - returns loss."""
        pass

    @abstractmethod
    def get_trainable_params(self) -> Iterator[Parameter]:
        """Return parameters to optimize."""
        pass
```

**Dependencies:**
- torch, diffusers, transformers, accelerate, safetensors
- No MGDS (unlike OneTrainer)
- Clean dependency graph

## OneTrainer Structure

```
modules/
├── cloud/            # Remote training
│   ├── BaseCloud.py
│   └── RunpodCloud.py
├── module/           # Utility modules
│   ├── LoRAModule.py
│   ├── EMAModule.py
│   ├── quantized/
│   └── BaseImageCaptionModel.py
├── modelSampler/     # Inference samplers
│   ├── BaseModelSampler.py
│   ├── FluxSampler.py
│   └── ZImageSampler.py
├── modelLoader/      # Model loading (complex!)
│   ├── flux/
│   │   ├── FluxModelLoader.py
│   │   ├── FluxLoRALoader.py
│   │   └── FluxEmbeddingLoader.py
│   └── mixin/
│       └── HFModelLoaderMixin.py
├── model/            # Model classes
│   ├── FluxModel.py
│   ├── ZImageModel.py
│   └── BaseModel.py
├── dataLoader/       # Data loading (MGDS-based)
│   ├── MgdsFluxDataLoader.py
│   └── MgdsZImageDataLoader.py
├── trainer/          # Training logic
│   ├── GenericTrainer.py
│   └── BaseTrainer.py
└── util/             # Configuration, enums
    ├── config/
    │   └── TrainConfig.py
    └── enum/
        └── ModelType.py
```

### Patterns

**Module Organization:**
- Role-based directories: modelLoader, modelSampler, dataLoader
- Multiple classes per concern (FluxModelLoader, FluxLoRALoader, FluxEmbeddingLoader)
- Heavy use of mixins

**Import Style:**
```python
# Internal imports - relative path from modules
from modules.model.FluxModel import FluxModel
from modules.modelLoader.mixin.HFModelLoaderMixin import HFModelLoaderMixin
from modules.util.config.TrainConfig import QuantizationConfig
```

**Class Pattern:**
```python
class FluxModelLoader(HFModelLoaderMixin):
    """Loads Flux models with multiple formats and quantization."""

    def __load_diffusers(self, model, ...):
        # Private method for diffusers format

    def __load_ckpt(self, model, ...):
        # Private method for checkpoint format
```

**Complexity:**
- Many interdependent modules
- Mixin inheritance chains
- MGDS data system adds abstraction

## Key Differences

| Aspect | EriTrainer | OneTrainer |
|--------|-----------|------------|
| Size | ~43K lines | ~58K lines |
| Architecture | Clean, flat | Deep, complex |
| Model files | One per arch | Multiple per arch |
| Loading | Simple factory | Loader + mixin chains |
| Data | Native PyTorch | MGDS abstraction |
| Inheritance | ABC interfaces | Mixin chains |

## Parsing Requirements

### Python Parser Must Extract

1. **Module name** — from file path
   - `eritrainer/models/zimage.py` → `eritrainer.models.zimage`

2. **Imports** — dependencies
   ```python
   from eritrainer.core.interfaces import BaseModel
   from diffusers import AutoencoderKL
   import torch
   ```

3. **Classes** — public interfaces
   ```python
   class ZImageModel(BaseModel):
       def forward(...) -> torch.Tensor
       def get_trainable_params(...) -> Iterator[Parameter]
   ```

4. **Functions** — module-level exports
   ```python
   def _load_sharded_safetensors(path: str, subfolder: str) -> dict
   ```

5. **Docstrings** — for summaries
   ```python
   """
   Z-Image model wrapper for EriTrainer.
   Uses Qwen3 text encoder, flow-matching training.
   """
   ```

### Dependency Types

1. **Internal** — within same project
   ```python
   from eritrainer.core.interfaces import BaseModel
   ```

2. **External** — third-party packages
   ```python
   from diffusers import AutoencoderKL
   from torch import nn
   ```

3. **Relative** — sibling modules
   ```python
   from .base import BaseAdapter
   ```

## Feature Transplant Examples

### Example 1: Z-Image Training from OneTrainer to EriTrainer

**Source (OneTrainer):**
- `modules/model/ZImageModel.py` — model wrapper
- `modules/modelLoader/zimage/ZImageModelLoader.py` — loading
- `modules/dataLoader/MgdsZImageDataLoader.py` — data
- `modules/modelSampler/ZImageSampler.py` — inference

**Target (EriTrainer):**
- `eritrainer/models/zimage.py` — model wrapper
- No separate loader (factory pattern)
- No MGDS (native PyTorch)
- `eritrainer/sampling/zimage.py` — inference

**Transplant Mapping:**
- ZImageModel.py → zimage.py (adapt to BaseModel interface)
- Skip loader (use factory)
- Skip MGDS (use native pipeline)
- ZImageSampler → zimage.py sampling methods

### Example 2: 24GB Klein Training

**Capability:** Train Klein 9B at 24GB VRAM without quantization

**Source files to identify:**
- Memory optimization code
- Gradient checkpointing setup
- Model offloading patterns
- Optimizer configuration

**Graph query:**
- Find modules tagged "memory", "gradient_checkpoint", "offload"
- Trace dependencies
- Extract as feature

## Indexing Strategy

For these codebases, the indexer should:

1. **Parse with Python ast module** — stdlib, no deps
2. **Extract interfaces** — class/function signatures
3. **Build dependency graph** — import statements
4. **Generate summaries** — from docstrings
5. **Store in JSON** — lightweight, readable

**Token budget per module:**
- Summary: 50-100 tokens
- Interfaces: 100-200 tokens
- Full graph: 2-5K tokens for entire project
