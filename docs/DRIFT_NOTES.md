# Drift Integration Notes

## Decision: CLI Bridge, Not Port

**Date:** 2025-01-27
**Status:** Active - CLI Bridge implemented

## Do We Need to Port Drift?

**Short answer: No, not yet. Maybe never.**

## Reasons NOT to Port

| Factor | Assessment |
|--------|------------|
| **Drift works now** | CLI bridge gets 90% of value with 10% effort |
| **Maintenance burden** | Porting = owning Tree-sitter parsers for 8 languages |
| **Drift is actively developed** | You'd fork and immediately diverge |
| **Your stack is Rust/Python** | Drift is TypeScript - different ecosystem |
| **Call graph is complex** | Cross-file resolution, framework detection, ORM patterns |

## Reasons You MIGHT Port (Later)

| Factor | When It Matters |
|--------|-----------------|
| **Performance** | If CLI latency (100-500ms) blocks real-time use |
| **Offline/embedded** | If you need it in EriGui without Node.js |
| **Deep customization** | If you need Dart/Mojo/CUDA-specific analysis Drift won't add |
| **Single binary** | If distribution matters (Rust binary vs Node dependency) |

## Middle Ground - What We Actually Did

1. **Use CLI bridge now** (Phase 1-4 of integration plan)
2. Identify which specific features you use most after 2-3 months
3. Port only those if performance matters

## If We Do Port Later

If after 2-3 months you find you only use:
- `callgraph impact`
- `check --json` (outliers)
- Pattern confidence lookup

...then port just those 3 things to Rust using tree-sitter bindings. That's maybe 500-1000 lines vs porting the whole 15K+ LOC project.

## The Call Graph Core (Reasonable to Port)

```rust
// Core data structures
struct CallGraph {
    nodes: HashMap<FunctionId, FunctionNode>,
    edges: Vec<CallEdge>,
    data_access: Vec<DataAccess>,
}

// Per-language extractors via tree-sitter
trait LanguageExtractor {
    fn extract_functions(&self, tree: &Tree) -> Vec<FunctionNode>;
    fn extract_calls(&self, tree: &Tree) -> Vec<CallEdge>;
}
```

## What NOT to Port

The 150+ pattern detectors, ORM detection for Prisma/TypeORM/SQLAlchemy, framework-specific route extraction - that's where the bulk of Drift's value is. Porting that is a multi-month project.

## Implementation Details

### What We Built

1. **`erirpg/drift_bridge.py`** - CLI wrapper with:
   - LRU caching for repeated queries
   - Async variants for GUI/watch mode
   - Graceful degradation when Drift unavailable
   - All 50+ Drift tools accessible

2. **StoredLearning Enhancement** - Added fields:
   - `drift_pattern_id` - Pattern this learning matches
   - `drift_confidence` - Confidence score (0.0-1.0)
   - `is_outlier` - Whether code deviates from patterns
   - `validated_by_drift` - Whether enrichment was done

3. **`erirpg/implement.py` Enhancement**:
   - Impact analysis before changes
   - Risk assessment per file
   - Affected files tracking
   - Pre-implementation checks

4. **`erirpg/pattern_sync.py`** - Bidirectional sync:
   - Import Drift patterns into EriRPG
   - Export EriRPG patterns to Drift
   - Combined confidence scoring

### CLI Commands Added

```bash
eri-rpg drift-status [project]      # Check Drift availability
eri-rpg enrich-learnings [project]  # Batch enrich with Drift
eri-rpg sync-patterns [project]     # Bidirectional pattern sync
eri-rpg drift-patterns [project]    # List all patterns
eri-rpg drift-impact [project] file # Show impact analysis
```

## 90-Day Evaluation Criteria

After 90 days of use, evaluate:

1. **Which features are used most?**
   - Track CLI calls in logs
   - Identify hot paths

2. **Is latency a problem?**
   - If <500ms per call, CLI is fine
   - If real-time feedback needed, consider porting

3. **Are there missing languages?**
   - If Dart/Mojo/CUDA needed, either:
     a. Contribute to Drift
     b. Port with custom extractors

4. **Is Node.js dependency acceptable?**
   - For CLI: Yes
   - For EriGui embedded: Maybe not

## Recommendation

**Ship the bridge. Evaluate in 90 days.**

The CLI bridge gives us:
- Pattern detection (15 categories)
- Call graph analysis
- Impact analysis
- Outlier detection
- Confidence scoring

...with minimal maintenance burden and no fork divergence risk.
