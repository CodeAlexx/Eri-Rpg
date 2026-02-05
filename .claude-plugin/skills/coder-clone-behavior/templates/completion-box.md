# Clone Completion Box

Use this format when clone is complete:

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ CLONE COMPLETE: {source_name} → {target_name}               ║
╠════════════════════════════════════════════════════════════════╣
║  Source: {source_path} ({source_language})                     ║
║  Target: {target_name} ({target_language})                     ║
║  Modules: {count} cloned, {count} verified                     ║
║  Result: Different code, same functionality                    ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Validate the clone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Run tests: {test_command}
2. Run app: {run_command}
3. Compare outputs with source (manual)
4. Type:  /clear
5. Then:  /coder:init
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## STATE.md Update

```markdown
## Last Action
Completed clone-behavior: {source_name} → {target_name}
- Modules cloned: {count}
- Behaviors verified: {count}/{count}

## Next Step
Run application and compare with source
```

## Global State Update

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```
