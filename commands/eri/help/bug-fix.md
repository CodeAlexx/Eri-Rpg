# Workflow: Fixing a Bug

## Quick Bug Fix (Single File)

```bash
# 1. Start quick fix
/eri:quick myproject src/buggy-file.py "fix null pointer bug"

# 2. Make the fix

# 3. Complete (auto-commits)
eri-rpg quick-done myproject
```

## Bug Fix with Investigation

```bash
# 1. Check impact of the file
/eri:impact myproject src/buggy-file.py

# 2. Learn the module first
/eri:learn myproject src/buggy-file.py

# 3. Start quick fix
/eri:quick myproject src/buggy-file.py "fix the bug"

# 4. Fix it

# 5. Complete
eri-rpg quick-done myproject

# 6. Capture what you learned
/eri:pattern myproject "Always null-check before accessing .user" --gotcha
```

## Multi-File Bug Fix

```bash
# 1. Start full execution
/eri:execute "fix authentication bypass bug"

# 2. EriRPG will:
#    - Create a run
#    - Track all files touched
#    - Run verification
#    - Auto-learn changes

# 3. Log what caused the bug
/eri:decide myproject "Bug root cause" "Missing validation" "Add input validation to all endpoints"
```

## Post-Fix Best Practices

1. **Capture the gotcha**
   ```bash
   /eri:pattern myproject "Always validate X before Y" --gotcha
   ```

2. **Log the decision**
   ```bash
   /eri:decide myproject "Bug fix approach" "Added validation layer" "Prevents similar bugs"
   ```

3. **Verify the fix**
   ```bash
   /eri:verify myproject
   ```
