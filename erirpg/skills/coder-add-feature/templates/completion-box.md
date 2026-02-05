# Feature Completion Box

Use this format when feature is complete:

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ FEATURE COMPLETE: {feature-name}                            ║
╠════════════════════════════════════════════════════════════════╣
║  Files created/modified: {count}                               ║
║  Tests added: {count}                                          ║
║  Location: .planning/features/{feature-name}/                  ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Verify and continue

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Run tests: {test_command}
2. Type:  /clear
3. Then:  /coder:init
4. Then:  /coder:add-feature <next-feature>  (if more features)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Commit Message

```bash
git add .planning/features/ src/
git commit -m "feat: add {feature-name}

- Feature spec and plans in .planning/features/{feature-name}/
- Implementation complete with tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## STATE.md Update

```markdown
## Last Action
Completed add-feature: {feature-name}
- Files created: {count}
- Tests added: {count}

## Next Step
Run tests or add another feature
```

## Global State Update

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```
