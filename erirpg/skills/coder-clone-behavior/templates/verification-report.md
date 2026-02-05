# Clone Verification Report Template

```markdown
# Clone Verification Report

## Source
- Project: {source_name}
- Language: {source_language}
- Framework: {source_framework}
- Modules: {module_count}

## Target
- Project: {target_name}
- Language: {target_language}
- Framework: {target_framework}

## Verification Results

| Module | Interface | State | Tests | Global | Ownership | Resources |
|--------|-----------|-------|-------|--------|-----------|-----------|
| {mod1} | {status}  | {status} | {status} | {status} | {status} | {status} |

## Status Legend
- ✅ Passed
- ❌ Failed (must fix)
- ⚠️ Manual check required

## Summary
- Total modules: {N}
- Fully verified: {N}
- Manual checks: {N}
- Failed: {N}

## Manual Verification Evidence
{For each ⚠️, document what was verified and how}

## Deviations
{Any intentional differences from source behavior, with rationale}

## Conclusion
{✅ Clone complete with behavior parity | ❌ Issues remain}
```
