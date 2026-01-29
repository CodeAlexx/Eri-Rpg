---
name: eri:test
description: Run project tests
argument-hint: "<project> [test-pattern]"
---

# /eri:test - Run Tests

Quick way to run tests for a project.

## Usage
```bash
# Run all tests
eri-rpg verify run <project>

# Or use the verification system
eri-rpg verify run <project>
```

## Direct Test Commands
For quick test runs, you can also use bash directly:

```bash
# Python
cd <project-path> && pytest -v

# With pattern
cd <project-path> && pytest -v -k "test_auth"

# Node
cd <project-path> && npm test

# Rust
cd <project-path> && cargo test
```

## With EriRPG Verification
```bash
# Configure custom test command
eri-rpg verify config <project>

# Run configured tests
eri-rpg verify run <project>

# Check what failed
eri-rpg gaps <project>
```

## Tier
Verification requires: **full**
Direct bash testing: **any tier**
