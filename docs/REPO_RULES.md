# Repository Rules

What can and cannot be committed to this repository.

## NEVER Commit

| File/Pattern | Reason |
|--------------|--------|
| `CLAUDE.md` | Private project instructions - stays local only |
| `.env` | Secrets, API keys |
| `*.key`, `*.pem` | Credentials |
| `credentials.json` | Auth tokens |
| `.eri-rpg/session.json` | Session state |
| `EXECUTION_STATE.json` | Runtime state |

## Always Gitignore

```
CLAUDE.md
.env
*.key
*.pem
credentials.json
.eri-rpg/
.planning/quick/*/SUMMARY.md
```

## Safe to Commit

| Path | Contents |
|------|----------|
| `erirpg/` | Source code |
| `erirpg/agents/*.md` | Agent specs (version control copies) |
| `docs/` | Documentation |
| `tests/` | Test files |
| `.planning/phases*/` | Phase planning files |
| `EMPOWERMENT.md` | Public principles |

## Why CLAUDE.md is Private

- Contains project-specific instructions for AI assistants
- May include workflow patterns, shortcuts, workarounds
- Different per machine/user
- Not useful to other users of the repo
- Could expose internal processes

## Before Every Push

Check: `git status` - verify no private files staged.
