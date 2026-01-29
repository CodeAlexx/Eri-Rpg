"""
New Mode - Create new project from scratch.

Usage:
    eri-rpg new "video editor with timeline and effects"

Flow:
    1. Ask - questions until it understands what you want
    2. Spec - generate PROJECT.md + STRUCTURE.md
    3. Structure - generate project skeleton
    4. Plan - break into buildable chunks
    5. Context - generate context for first chunk
    6. Guide - tell user what to do next
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from erirpg.registry import Registry
from erirpg.state import State


@dataclass
class ProjectSpec:
    """Specification for a new project."""
    name: str
    description: str
    language: str = "python"
    framework: Optional[str] = None

    # Core features
    core_features: List[str] = field(default_factory=list)

    # Constraints
    constraints: List[str] = field(default_factory=list)

    # Structure
    directories: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)

    # Chunks (buildable pieces)
    chunks: List[Dict] = field(default_factory=list)


@dataclass
class Question:
    """A question to ask the user."""
    id: str
    question: str
    why: str  # Why we're asking
    options: Optional[List[str]] = None  # If multiple choice
    default: Optional[str] = None
    required: bool = True


# Question flow for new projects
QUESTIONS = [
    Question(
        id="name",
        question="What should we call this project?",
        why="Need a name for the directory and references",
        default=None,
        required=True,
    ),
    Question(
        id="core_feature",
        question="What's the ONE core feature? (be specific)",
        why="Starting with one thing keeps scope manageable",
        required=True,
    ),
    Question(
        id="language",
        question="What language?",
        why="Determines project structure and tooling",
        options=["python", "rust", "c", "mojo"],  # Must match indexer support
        default="python",
        required=True,
    ),
    Question(
        id="framework",
        question="Any framework? (or 'none')",
        why="Frameworks dictate structure",
        default="none",
        required=False,
    ),
    Question(
        id="constraints",
        question="Any constraints? (e.g., 'must work offline', 'no external deps')",
        why="Constraints guide architecture decisions",
        default="none",
        required=False,
    ),
]


def slugify(name: str) -> str:
    """Convert name to valid directory name."""
    return name.lower().replace(" ", "_").replace("-", "_")


def generate_project_spec(answers: Dict[str, str], description: str) -> ProjectSpec:
    """Generate project specification from answers."""
    name = slugify(answers.get("name", "project"))

    # Parse constraints
    constraints_raw = answers.get("constraints", "none")
    constraints = []
    if constraints_raw and constraints_raw.lower() != "none":
        constraints = [c.strip() for c in constraints_raw.split(",")]

    # Determine structure based on language/framework
    language = answers.get("language", "python")
    framework = answers.get("framework", "none")
    if framework.lower() == "none":
        framework = None

    directories, key_files = get_structure_for(language, framework)

    # Create chunks from core feature
    core_feature = answers.get("core_feature", "main functionality")
    chunks = create_chunks(core_feature, language, framework)

    return ProjectSpec(
        name=name,
        description=description,
        language=language,
        framework=framework,
        core_features=[core_feature],
        constraints=constraints,
        directories=directories,
        key_files=key_files,
        chunks=chunks,
    )


def get_structure_for(language: str, framework: Optional[str]) -> tuple:
    """Get directory structure and key files for language/framework."""

    if language == "python":
        if framework == "fastapi":
            return (
                ["app", "app/api", "app/models", "app/core", "tests"],
                ["app/__init__.py", "app/main.py", "app/api/__init__.py",
                 "app/models/__init__.py", "app/core/__init__.py", "app/core/config.py",
                 "tests/__init__.py", "requirements.txt", "README.md"],
            )
        elif framework == "flask":
            return (
                ["app", "app/routes", "app/models", "tests"],
                ["app/__init__.py", "app/routes/__init__.py", "app/models/__init__.py",
                 "tests/__init__.py", "requirements.txt", "README.md"],
            )
        else:
            # Plain Python
            return (
                ["src", "tests"],
                ["src/__init__.py", "src/main.py", "tests/__init__.py",
                 "requirements.txt", "README.md"],
            )

    elif language == "rust":
        return (
            ["src"],
            ["src/main.rs", "src/lib.rs", "Cargo.toml", "README.md"],
        )

    elif language == "c":
        return (
            ["src", "include", "tests"],
            ["src/main.c", "include/main.h", "Makefile", "README.md"],
        )

    # Default
    return (["src"], ["src/main.py", "README.md"])


def create_chunks(core_feature: str, language: str, framework: Optional[str]) -> List[Dict]:
    """Break core feature into buildable chunks."""

    # Generic chunking - could be smarter
    chunks = [
        {
            "id": "001",
            "name": "Project Setup",
            "description": f"Initialize {language} project structure and dependencies",
            "creates": ["config", "dependencies", "base structure"],
            "depends_on": [],
        },
        {
            "id": "002",
            "name": "Core Data Structures",
            "description": f"Define data models for: {core_feature}",
            "creates": ["models", "types", "interfaces"],
            "depends_on": ["001"],
        },
        {
            "id": "003",
            "name": "Core Logic",
            "description": f"Implement main logic for: {core_feature}",
            "creates": ["business logic", "algorithms"],
            "depends_on": ["002"],
        },
        {
            "id": "004",
            "name": "Integration",
            "description": "Wire components together and create entry point",
            "creates": ["main entry", "CLI or API"],
            "depends_on": ["003"],
        },
    ]

    return chunks


def generate_project_md(spec: ProjectSpec, output_dir: str) -> str:
    """Generate PROJECT.md specification."""
    lines = [
        f"# {spec.name}",
        "",
        f"**Description:** {spec.description}",
        f"**Language:** {spec.language}",
    ]

    if spec.framework:
        lines.append(f"**Framework:** {spec.framework}")

    lines.extend([
        "",
        "## Core Features",
        "",
    ])

    for feature in spec.core_features:
        lines.append(f"- {feature}")

    if spec.constraints:
        lines.extend([
            "",
            "## Constraints",
            "",
        ])
        for constraint in spec.constraints:
            lines.append(f"- {constraint}")

    lines.extend([
        "",
        "## Build Order",
        "",
    ])

    for chunk in spec.chunks:
        lines.append(f"### Chunk {chunk['id']}: {chunk['name']}")
        lines.append(f"{chunk['description']}")
        lines.append(f"- Creates: {', '.join(chunk['creates'])}")
        if chunk['depends_on']:
            lines.append(f"- Depends on: {', '.join(chunk['depends_on'])}")
        lines.append("")

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = os.path.join(output_dir, "PROJECT.md")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


def generate_structure_md(spec: ProjectSpec, output_dir: str) -> str:
    """Generate STRUCTURE.md with directory layout."""
    lines = [
        f"# Structure: {spec.name}",
        "",
        "## Directories",
        "",
        "```",
        f"{spec.name}/",
    ]

    for d in spec.directories:
        lines.append(f"├── {d}/")

    lines.extend([
        "└── .eri-rpg/",
        "```",
        "",
        "## Key Files",
        "",
    ])

    for f in spec.key_files:
        lines.append(f"- `{f}`")

    # Write file
    path = os.path.join(output_dir, "STRUCTURE.md")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


def generate_chunk_context(spec: ProjectSpec, chunk_id: str, output_dir: str) -> tuple:
    """Generate context file for a specific chunk.

    Returns: (context_path, token_estimate)
    """
    chunk = None
    for c in spec.chunks:
        if c["id"] == chunk_id:
            chunk = c
            break

    if not chunk:
        raise ValueError(f"Chunk {chunk_id} not found")

    lines = [
        f"# Build: {spec.name}",
        f"## Chunk {chunk['id']}: {chunk['name']}",
        "",
        f"**Project:** {spec.name}",
        f"**Language:** {spec.language}",
    ]

    if spec.framework:
        lines.append(f"**Framework:** {spec.framework}")

    lines.extend([
        "",
        "---",
        "",
        "## What to Build",
        "",
        chunk['description'],
        "",
        "**Creates:**",
    ])

    for item in chunk['creates']:
        lines.append(f"- {item}")

    if chunk['depends_on']:
        lines.extend([
            "",
            "**Depends on chunks:**",
        ])
        for dep in chunk['depends_on']:
            lines.append(f"- Chunk {dep}")

    lines.extend([
        "",
        "---",
        "",
        "## Project Context",
        "",
        f"**Description:** {spec.description}",
        "",
        "**Core features:**",
    ])

    for feature in spec.core_features:
        lines.append(f"- {feature}")

    if spec.constraints:
        lines.extend([
            "",
            "**Constraints:**",
        ])
        for constraint in spec.constraints:
            lines.append(f"- {constraint}")

    lines.extend([
        "",
        "---",
        "",
        "## Structure",
        "",
        "Create these directories:",
        "",
    ])

    for d in spec.directories:
        lines.append(f"- `{d}/`")

    lines.extend([
        "",
        "Key files for this chunk:",
        "",
    ])

    # Filter key files relevant to this chunk
    for f in spec.key_files:
        lines.append(f"- `{f}`")

    lines.extend([
        "",
        "---",
        "",
        "## Instructions",
        "",
        f"1. Create the directory structure for `{spec.name}/`",
        f"2. Implement: {chunk['name']}",
        "3. Follow project constraints",
        "4. Keep it minimal - only what this chunk needs",
        "",
        f"When done: `eri-rpg next`",
        "",
    ])

    # Write file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"chunk_{chunk_id}_{chunk['name'].lower().replace(' ', '_')}.md"
    path = os.path.join(output_dir, filename)

    with open(path, "w") as f:
        f.write("\n".join(lines))

    tokens = len("\n".join(lines)) // 4  # Rough estimate

    return path, tokens


def create_project_skeleton(spec: ProjectSpec, base_path: str) -> str:
    """Create the actual project directory structure.

    Returns: path to project root
    """
    project_path = os.path.join(base_path, spec.name)

    # Create directories
    for d in spec.directories:
        Path(os.path.join(project_path, d)).mkdir(parents=True, exist_ok=True)

    # Create .eri-rpg directories
    Path(os.path.join(project_path, ".eri-rpg", "specs")).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(project_path, ".eri-rpg", "context")).mkdir(parents=True, exist_ok=True)

    # Create empty key files (stubs)
    for f in spec.key_files:
        file_path = os.path.join(project_path, f)
        Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)

        if not os.path.exists(file_path):
            # Create with minimal content
            if f.endswith(".py"):
                content = f'"""{os.path.basename(f)} - TODO: implement"""\n'
            elif f.endswith(".ts") or f.endswith(".tsx"):
                content = f"// {os.path.basename(f)} - TODO: implement\n"
            elif f.endswith(".rs"):
                content = f"// {os.path.basename(f)} - TODO: implement\n"
            elif f.endswith(".go"):
                content = f"// {os.path.basename(f)} - TODO: implement\npackage main\n"
            elif f.endswith(".md"):
                content = f"# {os.path.basename(f).replace('.md', '')}\n\nTODO\n"
            elif f.endswith(".json"):
                content = "{}\n"
            elif f.endswith(".toml"):
                content = "# TODO\n"
            else:
                content = ""

            with open(file_path, "w") as fp:
                fp.write(content)

    return project_path


def format_guide(
    spec: ProjectSpec,
    project_path: str,
    context_path: str,
    tokens: int,
    current_chunk: Dict,
) -> str:
    """Format the guide output for the user."""
    border = "═" * 56

    lines = [
        "",
        border,
        f"PROJECT: {spec.name}",
        "",
        f"Created: {project_path}",
        "",
        f"CHUNK {current_chunk['id']}: {current_chunk['name']}",
        f"Context file: {context_path}",
        f"Tokens: ~{tokens:,}",
        "",
        "NEXT STEPS:",
        "  1. /clear",
        f"  2. Read the context: cat {context_path}",
        "  3. Tell CC: \"Build this\"",
        "",
        "When done: eri-rpg next",
        border,
        "",
    ]

    return "\n".join(lines)


def save_new_state(spec: ProjectSpec, project_path: str, current_chunk: str):
    """Save state for resuming."""
    state_data = {
        "mode": "new",
        "project_name": spec.name,
        "project_path": project_path,
        "current_chunk": current_chunk,
        "total_chunks": len(spec.chunks),
        "spec": {
            "name": spec.name,
            "description": spec.description,
            "language": spec.language,
            "framework": spec.framework,
            "core_features": spec.core_features,
            "constraints": spec.constraints,
            "directories": spec.directories,
            "key_files": spec.key_files,
            "chunks": spec.chunks,
        }
    }

    # Save to .eri-rpg in project
    state_path = os.path.join(project_path, ".eri-rpg", "new_state.json")
    import json
    with open(state_path, "w") as f:
        json.dump(state_data, f, indent=2)


def load_new_state(project_path: str) -> Optional[dict]:
    """Load saved new project state."""
    state_path = os.path.join(project_path, ".eri-rpg", "new_state.json")
    if os.path.exists(state_path):
        import json
        with open(state_path) as f:
            return json.load(f)
    return None


def run_new(
    description: str,
    output_dir: Optional[str] = None,
    answers: Optional[Dict[str, str]] = None,
    verbose: bool = False,
) -> dict:
    """Run the new mode.

    Args:
        description: What to build
        output_dir: Where to create project (default: current directory)
        answers: Pre-provided answers (for non-interactive use)
        verbose: Show detailed progress

    Returns:
        dict with results including 'questions' if more input needed
    """
    registry = Registry.get_instance()
    state = State.load()

    if output_dir is None:
        output_dir = os.getcwd()

    # If no answers provided, return questions
    if answers is None:
        return {
            'success': False,
            'need_input': True,
            'questions': QUESTIONS,
            'description': description,
        }

    # Generate spec from answers
    if verbose:
        print("Generating project specification...")

    spec = generate_project_spec(answers, description)

    if verbose:
        print(f"  Name: {spec.name}")
        print(f"  Language: {spec.language}")
        print(f"  Framework: {spec.framework or 'none'}")
        print(f"  Chunks: {len(spec.chunks)}")

    # Create project skeleton
    if verbose:
        print("Creating project structure...")

    project_path = create_project_skeleton(spec, output_dir)

    if verbose:
        print(f"  Created: {project_path}")

    # Generate specs
    if verbose:
        print("Generating specifications...")

    specs_dir = os.path.join(project_path, ".eri-rpg", "specs")
    project_md = generate_project_md(spec, specs_dir)
    structure_md = generate_structure_md(spec, specs_dir)

    if verbose:
        print(f"  PROJECT.md: {project_md}")
        print(f"  STRUCTURE.md: {structure_md}")

    # Generate context for first chunk
    if verbose:
        print("Generating context for Chunk 001...")

    context_dir = os.path.join(project_path, ".eri-rpg", "context")
    context_path, tokens = generate_chunk_context(spec, "001", context_dir)

    if verbose:
        print(f"  Context: {context_path}")
        print(f"  Tokens: ~{tokens:,}")

    # Save state for resuming
    save_new_state(spec, project_path, "001")

    # Register project
    try:
        registry.add(spec.name, project_path, spec.language)
        if verbose:
            print(f"  Registered project: {spec.name}")
    except ValueError:
        # Already registered, update path
        pass

    # Update global state
    state.update(
        current_task=f"New project: {spec.name}",
        phase="building",
        context_file=context_path,
        waiting_on="claude",
    )
    state.log("new", f"Created new project: {spec.name}")

    # Generate guide
    guide = format_guide(spec, project_path, context_path, tokens, spec.chunks[0])

    return {
        'success': True,
        'project_name': spec.name,
        'project_path': project_path,
        'spec': spec,
        'project_md': project_md,
        'structure_md': structure_md,
        'context_path': context_path,
        'tokens': tokens,
        'current_chunk': "001",
        'total_chunks': len(spec.chunks),
        'guide': guide,
    }


def run_next(project_path: Optional[str] = None, verbose: bool = False) -> dict:
    """Advance to next chunk in new project.

    Args:
        project_path: Path to project (default: current directory)
        verbose: Show detailed progress

    Returns:
        dict with results
    """
    if project_path is None:
        project_path = os.getcwd()

    # Load state
    state_data = load_new_state(project_path)

    if not state_data:
        return {
            'success': False,
            'error': "No new project state found. Are you in a project created with 'eri-rpg new'?"
        }

    current_chunk = state_data['current_chunk']
    chunks = state_data['spec']['chunks']

    # Find current chunk index
    current_idx = None
    for i, c in enumerate(chunks):
        if c['id'] == current_chunk:
            current_idx = i
            break

    if current_idx is None:
        return {'success': False, 'error': f"Chunk {current_chunk} not found"}

    # Check if done
    if current_idx >= len(chunks) - 1:
        return {
            'success': True,
            'done': True,
            'message': f"Project {state_data['project_name']} complete! All {len(chunks)} chunks built.",
        }

    # Advance to next chunk
    next_chunk = chunks[current_idx + 1]

    if verbose:
        print(f"Advancing to Chunk {next_chunk['id']}: {next_chunk['name']}")

    # Reconstruct spec
    spec = ProjectSpec(**state_data['spec'])

    # Generate context for next chunk
    context_dir = os.path.join(project_path, ".eri-rpg", "context")
    context_path, tokens = generate_chunk_context(spec, next_chunk['id'], context_dir)

    # Update saved state
    state_data['current_chunk'] = next_chunk['id']
    import json
    state_path = os.path.join(project_path, ".eri-rpg", "new_state.json")
    with open(state_path, "w") as f:
        json.dump(state_data, f, indent=2)

    # Update global state
    state = State.load()
    state.update(
        context_file=context_path,
        waiting_on="claude",
    )
    state.log("next", f"Advanced to chunk {next_chunk['id']}")

    # Generate guide
    guide = format_guide(spec, project_path, context_path, tokens, next_chunk)

    return {
        'success': True,
        'done': False,
        'project_name': spec.name,
        'context_path': context_path,
        'tokens': tokens,
        'current_chunk': next_chunk['id'],
        'chunk_name': next_chunk['name'],
        'remaining': len(chunks) - current_idx - 1,
        'guide': guide,
    }
