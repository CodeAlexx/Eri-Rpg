# Typical Feature Workflow

```
User: "Add user authentication to my app"

1. START SESSION
   /eri:start myproject
   → Sets active project, loads context

2. DISCUSS (clarify requirements)
   /eri:discuss "add user authentication"
   → EriRPG asks: JWT or sessions? OAuth? Password rules?
   → Captures decisions, constraints

3. SPEC (lock down what we're building)
   /eri:spec create auth-feature
   → Generates formal spec from discussion
   → Lists endpoints, data models, behaviors

4. RESEARCH (understand existing code)
   /eri:research auth
   → Finds related modules, patterns
   → I learn what exists before touching anything

5. PLAN (sequence the work)
   /eri:plan
   → Creates step-by-step implementation plan
   → Each step has: files, changes, verification

6. EXECUTE (do the work)
   /eri:execute
   → For each step:
      - Preflight: "I will modify user.py, add auth.py"
      - Learn: Read and index modules first
      - Edit: Make changes (hooks verify preflight)
      - Verify: Run tests, lint
      - Commit: Auto-commit if passing

7. DONE
   /eri:done
   → Marks complete, updates roadmap
```

## What Happens Behind the Scenes

```
Me: /eri:recall user
CLI: Returns structured knowledge about user.py
     - purpose, key functions, dependencies, gotchas

Me: Edit user.py (without preflight)
Hook: BLOCKED - "Run preflight first"

Me: agent.preflight(["user.py"], "modify")
Hook: Allowed - file is in preflight targets

Me: Edit user.py
Hook: ALLOWED
```

## Quick Fix (Single File, No Ceremony)

```
/eri:quick myproject src/utils.py "fix off-by-one error"
→ Snapshots file, allows edits, done when you say done
```
