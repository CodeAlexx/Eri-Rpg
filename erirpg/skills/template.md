# /coder:template - Save as Reusable Template

Save project structure, patterns, and configuration as a reusable template.

## CLI Integration

**First, call the CLI to list or query templates:**
```bash
# List available templates
erirpg coder-template --list

# Get specific template info
erirpg coder-template web-app
```

This returns JSON with:
- For list: `templates` array with name, path, description, category
- For specific: `template` object with full details

The CLI provides template metadata. Use the workflow below for save/use operations.

---

## Usage

```
/coder:template save "web-app"         # Save current as template
/coder:template list                   # List available templates
/coder:template use "web-app"          # Apply template to new project
/coder:template export "web-app"       # Export to shareable format
/coder:template import template.zip    # Import shared template
```

## Template Contents

A template captures:

```
~/.eri-rpg/templates/{name}/
├── template.yaml         # Template metadata
├── scaffold/             # File structure to copy
│   ├── src/
│   ├── tests/
│   ├── config/
│   └── docs/
├── patterns/             # Extracted patterns
│   ├── auth.yaml
│   └── api.yaml
├── planning/             # Planning templates
│   ├── PROJECT.template.md
│   ├── ROADMAP.template.md
│   └── phase-templates/
├── decisions/            # Documented decisions
│   └── decisions.md
└── config/               # Config templates
    ├── config.json
    └── .env.example
```

## Execution Steps

### Step 1: Analyze Current Project

```python
def analyze_for_template(project):
    return {
        "stack": detect_stack(project),
        "structure": map_directory_structure(project),
        "patterns": extract_reusable_patterns(project),
        "decisions": extract_key_decisions(project),
        "config": extract_config_templates(project),
        "planning": extract_planning_templates(project)
    }
```

### Step 2: Present Template Preview

```markdown
## Template Preview: web-app

**Source project:** my-app
**Type:** Full-stack web application

### Stack
- Frontend: Next.js 14, TypeScript, Tailwind
- Backend: API routes, Prisma
- Auth: JWT, httpOnly cookies
- Testing: Vitest, Playwright

### Structure to Include
```
scaffold/
├── src/
│   ├── app/           # Next.js app router
│   ├── components/    # React components
│   ├── lib/           # Utilities
│   ├── api/           # API layer
│   └── types/         # TypeScript types
├── prisma/
│   └── schema.prisma  # DB schema template
├── tests/
│   ├── unit/
│   └── e2e/
└── config/
    ├── next.config.js
    └── tailwind.config.js
```

### Patterns Included
| Pattern | Description |
|---------|-------------|
| api-layer | Structured API with services |
| jwt-auth | JWT authentication flow |
| error-handling | Consistent error responses |
| testing | Vitest + Playwright setup |

### Planning Templates
- PROJECT.md template with sections
- ROADMAP.md with common phases
- 5 phase templates for web apps

### Decisions Captured
| Decision | Choice | Applies To |
|----------|--------|------------|
| ORM | Prisma | Any SQL project |
| Validation | Zod | TypeScript projects |
| State | Zustand | React projects |

Create template? (yes/no/customize)
```

### Step 3: Customize Template

```markdown
## Customize Template

### Include/Exclude
- [x] src/ structure
- [x] tests/ setup
- [x] config files
- [ ] .planning/ (use fresh planning)
- [ ] node_modules (never)
- [ ] .env (secrets)

### Parameterize
| Placeholder | Description | Default |
|-------------|-------------|---------|
| {{PROJECT_NAME}} | Project name | my-app |
| {{DATABASE_URL}} | DB connection | - |
| {{JWT_SECRET}} | Auth secret | - |

### Phase Templates
- [x] Foundation phase
- [x] Auth phase (if auth needed)
- [x] Core features phase
- [ ] Social features (optional)
- [x] Polish phase

Save with these settings? (yes/no)
```

### Step 4: Create Template

```python
def create_template(name, project, config):
    template_dir = f"~/.eri-rpg/templates/{name}"

    # Create template.yaml
    write_yaml(f"{template_dir}/template.yaml", {
        "name": name,
        "version": "1.0.0",
        "created": timestamp(),
        "source_project": project.name,
        "stack": config.stack,
        "parameters": config.parameters,
        "phases": config.phase_templates
    })

    # Copy scaffold
    for path in config.include_paths:
        copy_with_parameterization(
            source=f"{project.path}/{path}",
            dest=f"{template_dir}/scaffold/{path}",
            params=config.parameters
        )

    # Extract patterns
    for pattern in config.patterns:
        save_pattern(f"{template_dir}/patterns/{pattern.name}.yaml", pattern)

    # Create planning templates
    for phase in config.phase_templates:
        create_phase_template(f"{template_dir}/planning/phases/{phase}")

    return template_dir
```

### Step 5: Report

```markdown
## Template Created

**Name:** web-app
**Location:** ~/.eri-rpg/templates/web-app/
**Size:** 45 files, 2.3 MB

### Contents
| Category | Count |
|----------|-------|
| Scaffold files | 32 |
| Patterns | 4 |
| Planning templates | 6 |
| Config templates | 3 |

### Usage
```
/coder:new-project my-new-app --template web-app
```

### Parameters
When using, you'll be asked:
- PROJECT_NAME: Your project name
- DATABASE_URL: Your database connection
- JWT_SECRET: Will be auto-generated

### Share
Export: `/coder:template export web-app`
Creates: `web-app-template.zip`
```

## Use Template

```
/coder:template use "web-app"
```

Or during new project:
```
/coder:new-project my-app --template web-app
```

### Template Application

```python
def apply_template(template_name, project_path, params):
    template = load_template(template_name)

    # Copy scaffold with parameter substitution
    for file in template.scaffold:
        content = read(file)
        for param, value in params.items():
            content = content.replace(f"{{{{{param}}}}}", value)
        write(f"{project_path}/{file.relative}", content)

    # Apply patterns to context
    for pattern in template.patterns:
        project.patterns.append(pattern)

    # Set up planning templates
    for phase in template.phases:
        copy_phase_template(phase, project_path)

    # Apply decisions
    for decision in template.decisions:
        add_decision_to_project(decision, project_path)
```

## List Templates

```
/coder:template list
```

```markdown
## Available Templates

### Built-in
| Name | Description | Stack |
|------|-------------|-------|
| web-app | Full-stack Next.js | Next, Prisma, JWT |
| api-only | REST API backend | Express, Prisma |
| cli-tool | CLI application | Node, Commander |

### User-Created
| Name | Created | Source |
|------|---------|--------|
| my-saas | 2026-01-28 | saas-project |
| mobile-api | 2026-01-20 | mobile-backend |

### Community
Install with: `/coder:template import <url>`
```

## Export/Import

### Export
```
/coder:template export web-app
```
Creates `web-app-template.zip` for sharing.

### Import
```
/coder:template import web-app-template.zip
/coder:template import https://example.com/template.zip
```

## Template Parameters

### Defining Parameters
```yaml
# template.yaml
parameters:
  - name: PROJECT_NAME
    description: Your project name
    type: string
    required: true

  - name: DATABASE_URL
    description: PostgreSQL connection string
    type: string
    required: true
    pattern: "postgres://.*"

  - name: JWT_SECRET
    description: JWT signing secret
    type: string
    required: true
    auto_generate: true  # Will generate if not provided
```

### Parameter Substitution
In template files:
```typescript
// {{PROJECT_NAME}}/src/config.ts
export const config = {
  appName: "{{PROJECT_NAME}}",
  database: "{{DATABASE_URL}}",
  jwtSecret: "{{JWT_SECRET}}"
};
```

## Integration Points

- Creates: ~/.eri-rpg/templates/{name}/
- Reads: Current project structure, patterns, decisions
- Exports: Shareable ZIP files
- Imports: Community templates
- Uses: During /coder:new-project with --template
