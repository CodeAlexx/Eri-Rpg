#!/usr/bin/env python3
"""
EriRPG Feature Implementation Planning

Uses project patterns to plan implementation of new features.
Generates specs with file plans, registrations, and hooks.

Usage:
    eri-rpg implement <project> "<feature description>"
    eri-rpg transplant --from source:path --to target
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from erirpg.analyze import load_patterns, ProjectPatterns
from erirpg.memory import KnowledgeStore, load_knowledge
from erirpg.graph import load_graph


@dataclass
class FeatureComponent:
    """A component of a feature to implement."""
    name: str                    # "RankScheduler"
    type: str                    # "scheduler" | "module" | "config" | "hook" | "test"
    purpose: str                 # "Adjusts ranks during training"
    keywords: List[str] = field(default_factory=list)  # Keywords that identified this


@dataclass
class FilePlan:
    """Plan for a single file."""
    component: str               # "RankScheduler"
    action: str                  # "create" | "modify"
    path: str                    # "training/scheduler/rank_scheduler.py"
    extends: Optional[str] = None  # "BaseScheduler"
    reason: str = ""             # "Schedulers live in training/scheduler/, inherit BaseScheduler"


@dataclass
class Phase:
    """A phase of implementation."""
    name: str
    description: str
    files: List[str]
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ImplementationPlan:
    """Complete plan for implementing a feature."""
    feature: str
    components: List[FeatureComponent]
    file_plan: List[FilePlan]
    registrations: List[str]     # ["SchedulerFactory.register('rank', RankScheduler)"]
    hooks: List[str]             # ["trainer.on_step_end"]
    phases: List[Phase]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "feature": self.feature,
            "components": [
                {"name": c.name, "type": c.type, "purpose": c.purpose}
                for c in self.components
            ],
            "file_plan": [
                {"component": f.component, "action": f.action, "path": f.path,
                 "extends": f.extends, "reason": f.reason}
                for f in self.file_plan
            ],
            "registrations": self.registrations,
            "hooks": self.hooks,
            "phases": [
                {"name": p.name, "description": p.description, "files": p.files,
                 "depends_on": p.depends_on}
                for p in self.phases
            ],
        }


# Component type keywords for detection
COMPONENT_KEYWORDS = {
    "scheduler": ["scheduler", "schedule", "lr", "learning rate", "warmup", "decay"],
    "optimizer": ["optimizer", "optim", "sgd", "adam", "adamw"],
    "module": ["module", "layer", "lora", "adapter", "embedding", "attention"],
    "model": ["model", "network", "backbone", "encoder", "decoder"],
    "config": ["config", "configuration", "settings", "params", "parameters"],
    "hook": ["hook", "callback", "event", "listener", "handler"],
    "loader": ["loader", "dataset", "dataloader", "sampler", "batch"],
    "loss": ["loss", "criterion", "objective"],
    "metric": ["metric", "accuracy", "precision", "recall", "score"],
    "util": ["util", "helper", "utils", "tools"],
    "test": ["test", "testing", "unittest", "pytest"],
}


def extract_components(feature: str) -> List[FeatureComponent]:
    """Parse feature description into components."""
    components = []
    feature_lower = feature.lower()

    # Look for explicit component mentions
    # Pattern: "needs X, Y, and Z" or "requires X, Y"
    needs_match = re.search(r'(?:needs|requires|includes?|with)\s+([^.]+)', feature_lower)
    if needs_match:
        parts = re.split(r',\s*(?:and\s+)?|\s+and\s+', needs_match.group(1))
        for part in parts:
            part = part.strip()
            if part:
                comp_type = detect_component_type(part)
                comp_name = generate_component_name(part, comp_type)
                components.append(FeatureComponent(
                    name=comp_name,
                    type=comp_type,
                    purpose=part,
                    keywords=[w for w in part.split() if len(w) > 3],
                ))

    # Also detect from main description
    for comp_type, keywords in COMPONENT_KEYWORDS.items():
        for kw in keywords:
            if kw in feature_lower and not any(c.type == comp_type for c in components):
                # Extract context around keyword
                match = re.search(rf'(\w+\s+)?{kw}(\s+\w+)?', feature_lower)
                if match:
                    context = match.group(0).strip()
                    comp_name = generate_component_name(context, comp_type)
                    if not any(c.name == comp_name for c in components):
                        components.append(FeatureComponent(
                            name=comp_name,
                            type=comp_type,
                            purpose=f"Handle {context}",
                            keywords=[kw],
                        ))

    # If no components detected, create a generic one
    if not components:
        # Try to extract a name from the feature
        name_match = re.search(r'(?:add|create|implement|build)\s+(?:a\s+)?(\w+)', feature_lower)
        if name_match:
            name = to_pascal_case(name_match.group(1))
            components.append(FeatureComponent(
                name=name,
                type="module",
                purpose=feature,
            ))
        else:
            components.append(FeatureComponent(
                name="Feature",
                type="module",
                purpose=feature,
            ))

    return components


def detect_component_type(text: str) -> str:
    """Detect component type from text."""
    text_lower = text.lower()
    for comp_type, keywords in COMPONENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return comp_type
    return "module"  # Default


def generate_component_name(text: str, comp_type: str) -> str:
    """Generate a component name from description."""
    # Remove common words
    stop_words = {'a', 'an', 'the', 'with', 'for', 'to', 'and', 'or', 'that', 'this'}
    words = [w for w in text.split() if w.lower() not in stop_words and len(w) > 2]

    # Remove the type keyword itself
    type_keywords = COMPONENT_KEYWORDS.get(comp_type, [])
    words = [w for w in words if w.lower() not in type_keywords]

    if not words:
        return to_pascal_case(comp_type)

    # Combine remaining words
    name = ''.join(to_pascal_case(w) for w in words[:3])

    # Add type suffix if not already there
    type_suffix = comp_type.capitalize()
    if not name.endswith(type_suffix) and comp_type not in ['module', 'util']:
        name += type_suffix

    return name


def to_pascal_case(text: str) -> str:
    """Convert text to PascalCase."""
    words = re.split(r'[_\s-]+', text)
    return ''.join(w.capitalize() for w in words if w)


def to_snake_case(text: str) -> str:
    """Convert text to snake_case."""
    # Insert underscore before uppercase letters
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def map_component_to_target(comp: FeatureComponent, patterns: ProjectPatterns) -> FilePlan:
    """Map component to target location using patterns."""

    # Default paths by type
    default_paths = {
        "scheduler": "schedulers/{name}.py",
        "optimizer": "optimizers/{name}.py",
        "module": "modules/{Name}.py",
        "model": "models/{name}.py",
        "config": "config/{name}_config.py",
        "hook": "hooks/{name}.py",
        "loader": "loaders/{name}.py",
        "loss": "losses/{name}.py",
        "metric": "metrics/{name}.py",
        "util": "utils/{name}.py",
        "test": "tests/test_{name}.py",
    }

    # Get path template from patterns or default
    path_template = patterns.structure.get(
        comp.type + "s",  # Try plural first (schedulers)
        patterns.structure.get(
            comp.type,  # Then singular
            default_paths.get(comp.type, "src/{name}.py")
        )
    )

    # Fill in template
    snake_name = to_snake_case(comp.name)
    path = path_template.format(
        name=snake_name,
        Name=comp.name,
        category="model",  # Default category
    )

    # Find base class to extend
    extends = None
    convention = patterns.conventions.get(f"new_{comp.type}")

    if comp.type in ["scheduler", "optimizer", "module", "model", "loader"]:
        # Look for matching base class
        base_name = f"Base{comp.type.capitalize()}"
        for name in patterns.base_classes:
            if comp.type.lower() in name.lower():
                extends = name
                break
        if not extends and base_name in patterns.base_classes:
            extends = base_name

    return FilePlan(
        component=comp.name,
        action="create",
        path=path,
        extends=extends,
        reason=convention or f"{comp.type}s follow project patterns",
    )


def find_needed_registrations(file_plan: List[FilePlan], patterns: ProjectPatterns) -> List[str]:
    """Identify registrations needed for new components."""
    registrations = []

    for fp in file_plan:
        # Skip tests and configs
        if "test" in fp.path or "config" in fp.path:
            continue

        # Find matching registry
        for reg in patterns.registries:
            # Match by path similarity or type
            if (fp.extends and fp.extends.lower() in reg.name.lower()) or \
               (fp.component.lower().replace('scheduler', '') in reg.name.lower()):
                reg_name = to_snake_case(fp.component.replace('Scheduler', '').replace('Module', ''))
                registrations.append(f"{reg.name}.register('{reg_name}', {fp.component})")
                break

    return registrations


def find_relevant_hooks(components: List[FeatureComponent], patterns: ProjectPatterns) -> List[str]:
    """Find hooks that the feature should use."""
    hooks = []

    # Keywords that suggest hook usage
    hook_triggers = {
        "step": ["on_step_start", "on_step_end"],
        "epoch": ["on_epoch_start", "on_epoch_end"],
        "train": ["on_train_start", "on_train_end"],
        "batch": ["on_batch_start", "on_batch_end"],
        "forward": ["on_forward", "forward_hook"],
        "backward": ["on_backward", "backward_hook"],
    }

    for comp in components:
        desc = (comp.purpose + " " + comp.name).lower()
        for trigger, hook_names in hook_triggers.items():
            if trigger in desc:
                # Find matching extension point
                for ep in patterns.extension_points:
                    for method in ep.methods:
                        if any(h in method for h in hook_names):
                            hooks.append(f"{ep.location.replace('.py', '')}.{method}")
                            break

    return list(set(hooks))


def create_phases(
    file_plan: List[FilePlan],
    registrations: List[str],
    hooks: List[str]
) -> List[Phase]:
    """Order implementation into phases."""
    phases = []

    # Phase 1: Create base components (modules, models)
    base_files = [fp.path for fp in file_plan if fp.action == "create"
                  and "test" not in fp.path and "config" not in fp.path]
    if base_files:
        phases.append(Phase(
            name="Create Components",
            description="Create new source files",
            files=base_files,
        ))

    # Phase 2: Create configs
    config_files = [fp.path for fp in file_plan if "config" in fp.path]
    if config_files:
        phases.append(Phase(
            name="Create Configs",
            description="Create configuration files",
            files=config_files,
            depends_on=["Create Components"] if base_files else [],
        ))

    # Phase 3: Register components
    if registrations:
        phases.append(Phase(
            name="Register Components",
            description="Add to factories/registries",
            files=[],  # Modifications to existing files
            depends_on=["Create Components"],
        ))

    # Phase 4: Wire hooks
    if hooks:
        phases.append(Phase(
            name="Wire Hooks",
            description="Connect to extension points",
            files=[],
            depends_on=["Create Components"],
        ))

    # Phase 5: Tests
    test_files = [fp.path for fp in file_plan if "test" in fp.path]
    if test_files:
        phases.append(Phase(
            name="Add Tests",
            description="Create test files",
            files=test_files,
            depends_on=["Create Components"],
        ))
    else:
        # Add a phase to remind about tests
        phases.append(Phase(
            name="Add Tests",
            description="Create tests for new components",
            files=[],
            depends_on=["Create Components"],
        ))

    return phases


def plan_implementation(project_path: str, feature: str) -> ImplementationPlan:
    """Generate implementation plan for a feature."""
    patterns = load_patterns(project_path)
    if not patterns:
        # Create minimal patterns
        patterns = ProjectPatterns()

    # 1. Parse feature into components
    components = extract_components(feature)

    # 2. Map each component to target using patterns
    file_plan = []
    for comp in components:
        plan = map_component_to_target(comp, patterns)
        file_plan.append(plan)

    # 3. Add test files for each component
    for comp in components:
        if comp.type != "test":
            test_path = patterns.test_patterns.get("location", "tests")
            test_naming = patterns.test_patterns.get("naming", "test_{name}.py")
            test_file = f"{test_path}/{test_naming.format(name=to_snake_case(comp.name), module=to_snake_case(comp.name))}"
            file_plan.append(FilePlan(
                component=f"Test{comp.name}",
                action="create",
                path=test_file,
                reason="Tests for new component",
            ))

    # 4. Identify registrations needed
    registrations = find_needed_registrations(file_plan, patterns)

    # 5. Identify hooks to use
    hooks = find_relevant_hooks(components, patterns)

    # 6. Order into phases
    phases = create_phases(file_plan, registrations, hooks)

    return ImplementationPlan(
        feature=feature,
        components=components,
        file_plan=file_plan,
        registrations=registrations,
        hooks=hooks,
        phases=phases,
    )


def describe_feature(project_path: str, file_path: str) -> str:
    """Extract feature description from a source file."""
    full_path = Path(project_path) / file_path
    if not full_path.exists():
        return f"# Feature from {file_path}\n\nFile not found."

    try:
        content = full_path.read_text()
    except Exception as e:
        return f"# Feature from {file_path}\n\nError reading: {e}"

    lines = []
    lines.append(f"# Feature from {file_path}")
    lines.append("")

    # Extract module docstring
    docstring_match = re.search(r'^"""([\s\S]*?)"""', content)
    if docstring_match:
        lines.append("## Description")
        lines.append(docstring_match.group(1).strip())
        lines.append("")

    # Extract classes
    classes = re.findall(r'class\s+(\w+)\s*(?:\([^)]*\))?:', content)
    if classes:
        lines.append("## Components")
        for cls in classes:
            # Try to get class docstring
            cls_doc_match = re.search(rf'class\s+{cls}[^:]*:\s*"""([^"]+)"""', content)
            if cls_doc_match:
                lines.append(f"- {cls}: {cls_doc_match.group(1).strip()}")
            else:
                lines.append(f"- {cls}")
        lines.append("")

    # Extract key methods
    methods = re.findall(r'def\s+(\w+)\s*\(self', content)
    public_methods = [m for m in methods if not m.startswith('_')]
    if public_methods:
        lines.append("## Key Methods")
        for method in public_methods[:10]:
            lines.append(f"- {method}()")
        lines.append("")

    return "\n".join(lines)


def format_implementation_plan(plan: ImplementationPlan) -> str:
    """Format implementation plan for display."""
    lines = []
    lines.append(f"Implementation Plan: {plan.feature}")
    lines.append("=" * 60)
    lines.append("")

    # Components
    lines.append("Components detected:")
    for comp in plan.components:
        lines.append(f"  - {comp.name} ({comp.type}) - {comp.purpose}")
    lines.append("")

    # File Plan
    lines.append("File Plan:")
    lines.append("-" * 60)
    header = f"{'Component':<20} {'Action':<8} {'Path':<30} {'Extends':<15}"
    lines.append(header)
    lines.append("-" * 60)
    for fp in plan.file_plan:
        ext = fp.extends or "-"
        lines.append(f"{fp.component:<20} {fp.action:<8} {fp.path:<30} {ext:<15}")
    lines.append("")

    # Registrations
    if plan.registrations:
        lines.append("Registrations needed:")
        for reg in plan.registrations:
            lines.append(f"  - {reg}")
        lines.append("")

    # Hooks
    if plan.hooks:
        lines.append("Hooks to use:")
        for hook in plan.hooks:
            lines.append(f"  - {hook}")
        lines.append("")

    # Phases
    lines.append("Phases:")
    for i, phase in enumerate(plan.phases, 1):
        deps = f" (after: {', '.join(phase.depends_on)})" if phase.depends_on else ""
        lines.append(f"  {i}. {phase.name}{deps}")
        lines.append(f"     {phase.description}")
        if phase.files:
            for f in phase.files[:3]:
                lines.append(f"       - {f}")
            if len(phase.files) > 3:
                lines.append(f"       ... and {len(phase.files) - 3} more")
    lines.append("")

    return "\n".join(lines)


def plan_to_spec(plan: ImplementationPlan, project_path: str) -> Dict[str, Any]:
    """Convert implementation plan to EriRPG spec."""
    import uuid

    steps = []
    step_id = 0

    # Learn phase - learn about base classes and registries
    learn_targets = []
    patterns = load_patterns(project_path)
    if patterns:
        # Add base classes to learn
        for fp in plan.file_plan:
            if fp.extends and fp.extends in patterns.base_classes:
                learn_targets.append(patterns.base_classes[fp.extends])
        # Add registry files to learn
        for reg in plan.registrations:
            reg_name = reg.split('.')[0]
            for r in patterns.registries:
                if r.name == reg_name:
                    learn_targets.append(r.path)

    if learn_targets:
        step_id += 1
        steps.append({
            "id": f"learn_{step_id}",
            "action": "learn",
            "targets": list(set(learn_targets)),
        })

    # Create phases
    for phase in plan.phases:
        if phase.files:
            step_id += 1
            action = "create" if "Create" in phase.name else "modify"
            steps.append({
                "id": f"{action}_{step_id}",
                "action": action,
                "targets": phase.files,
                "depends_on": [f"learn_1"] if steps and step_id > 1 else [],
            })

    # Registration phase
    if plan.registrations:
        step_id += 1
        steps.append({
            "id": f"register_{step_id}",
            "action": "modify",
            "targets": [],  # Will be filled during execution
            "notes": "Register components: " + ", ".join(plan.registrations),
        })

    # Verify phase
    step_id += 1
    steps.append({
        "id": f"verify_{step_id}",
        "action": "verify",
    })

    spec = {
        "id": str(uuid.uuid4())[:8],
        "goal": plan.feature,
        "generated_from": "implement",
        "steps": steps,
        "must_haves": {
            "artifacts": [
                {"path": fp.path}
                for fp in plan.file_plan
                if fp.action == "create" and "test" not in fp.path
            ],
        },
    }

    return spec
