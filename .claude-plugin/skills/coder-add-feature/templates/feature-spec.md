# Feature Spec Template

```markdown
# Feature: {feature-name}

## Problem Statement
{what problem this solves}

## User Stories
- As a {user}, I want to {action} so that {benefit}

## Acceptance Criteria
- [ ] {criterion 1}
- [ ] {criterion 2}
- [ ] {criterion 3}

## Technical Approach
Based on codebase analysis:
- **Integration Point:** `{path}` - {how to integrate}
- **Pattern to Follow:** {pattern from CONVENTIONS.md}
- **Files to Create/Modify:**
  - `{path}` - {what}
  - `{path}` - {what}

## Out of Scope
- {excluded functionality}

## Dependencies
- Requires: {existing modules}
- Blocked by: {none or blockers}

## Notes
{any additional context}
```

## Reference Mode Additions

When porting a feature with `--reference`, add these sections:

```markdown
## Source Reference
- Source: {source_path}/{section}
- Behavior spec: {source}-BEHAVIOR.md

## Target Must Adapt To
- **Base traits:** {traits}
- **Input wrapper:** {type}
- **Output wrapper:** {type}
- **Decorators:** {decorators}

## Compatibility Check
| Aspect | Source | Target | Status |
|--------|--------|--------|--------|
| Ownership | {model} | {model} | {✅/❌/⚠️} |
| Threading | {model} | {model} | {✅/❌/⚠️} |
| Side effects | {list} | {allowed} | {✅/❌/⚠️} |

## Verification Checklist
- [ ] Interface contract matches
- [ ] State machine preserved
- [ ] Test contracts pass
- [ ] Resource budget met
- [ ] Ownership model compatible
```
