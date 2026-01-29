# Workflow: Implementing a New Feature

## Quick Path (Lite Tier)

```bash
# 1. Start quick fix if single file
/eri:quick myproject src/feature.py "add new feature"

# 2. Make your changes

# 3. Complete
/eri:done myproject
```

## Standard Path (With Planning)

```bash
# 1. Discuss the feature first
/eri:discuss myproject "add user notifications"

# 2. Answer clarifying questions
eri-rpg discuss-answer myproject 1 "email and in-app"
eri-rpg discuss-answer myproject 2 "users can disable"

# 3. Log key decisions
/eri:decide myproject "Notification channel" "Both email and in-app" "Users want choice"

# 4. Defer v2 ideas
/eri:defer myproject "Add SMS notifications" --tags v2

# 5. Resolve and generate spec
eri-rpg discuss-resolve myproject
```

## Full Path (With Verification)

```bash
# 1. Discuss (as above)
/eri:discuss myproject "add user notifications"

# 2. Research if needed
/eri:research myproject "notification systems"

# 3. Generate spec
eri-rpg spec new myproject "notifications" --from-discussion

# 4. Execute with verification
/eri:execute "implement notification system per spec"

# 5. Verify passes
/eri:verify myproject

# 6. Check gaps
/eri:gaps myproject
```

## Best Practices

1. **Learn affected modules first**
   ```bash
   /eri:impact myproject src/users.py
   /eri:learn myproject src/users.py
   ```

2. **Log decisions as you make them**
   ```bash
   /eri:decide myproject "context" "choice" "rationale"
   ```

3. **Defer scope creep**
   ```bash
   /eri:defer myproject "nice-to-have idea" --tags later
   ```

4. **Verify before committing**
   ```bash
   /eri:verify myproject
   /eri:gaps myproject
   ```
