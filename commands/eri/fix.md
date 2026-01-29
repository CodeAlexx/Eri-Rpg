# /eri:fix - Bug Report During Workflow

Report a bug or issue encountered during EriRPG workflow execution.

## Arguments
- `$ARGUMENTS` - Description of the bug/issue (required)

## Execution

1. **Read current context**:
   - Find active project from recent STATE.md files in working directories
   - Read STATE.md for current phase/position
   - Read TASKS.md for active tasks

2. **Log the bug**:
   Add to TASKS.md under "## Bugs/Issues" section:
   ```markdown
   - [ ] **BUG: [summary]** - $ARGUMENTS
     - Reported: [timestamp]
     - Phase: [current phase from STATE.md]
     - Status: Investigating
   ```

3. **Investigate**:
   - Search for related code/files based on bug description
   - Check recent changes (git log -5)
   - Identify root cause

4. **Fix**:
   - Apply minimal fix
   - Verify fix works
   - Update TASKS.md with resolution

5. **Resume workflow**:
   Output: "Bug fixed. Resume with: `/eri:execute [project]`"

## Quick Mode

If bug is simple (typo, missing import, obvious error):
- Fix immediately
- Log in TASKS.md as completed
- Don't interrupt workflow

## Output Format

```
## Bug Report

**Issue**: $ARGUMENTS
**Phase**: [phase] - [name]
**Status**: [Investigating|Fixed|Deferred]

### Investigation
[findings]

### Resolution
[what was fixed or deferred reason]

Resume: `/eri:execute [project]`
```
