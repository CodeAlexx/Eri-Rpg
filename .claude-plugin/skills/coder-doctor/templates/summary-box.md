# Diagnosis Summary Box

Use this format for diagnosis output:

```
╔════════════════════════════════════════════════════════════════╗
║  DIAGNOSIS COMPLETE                                             ║
╠════════════════════════════════════════════════════════════════╣
║  Contract Lint:    {PASS|FAIL}                                  ║
║  Global State:     {OK|WARN|ERROR}                              ║
║  Project State:    {OK|WARN|ERROR}                              ║
║  Execution State:  {ACTIVE|IDLE}                                ║
║  Phase Health:     {N}/{M} phases healthy                       ║
║  Research Gaps:    {N} phases missing research                  ║
║  Verification:     {N} phases need attention                    ║
║  Hooks:            {OK|WARN|ERROR}                              ║
║  Skills:           {OK|WARN|ERROR}                              ║
╚════════════════════════════════════════════════════════════════╝
```

## Issue Severity Levels

List issues by severity:

1. **CRITICAL** - Workflow cannot proceed
2. **HIGH** - Execution gaps found
3. **MEDIUM** - Missing optional components
4. **WARN** - Configuration issues

## Example Output

```
ISSUES FOUND:
  - CRITICAL: ROADMAP.md missing
  - HIGH: Phase 2 has verification gaps
  - MEDIUM: Phase 3 missing RESEARCH.md
  - WARN: Hook sessionstart.py missing
```
