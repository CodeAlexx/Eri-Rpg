#!/usr/bin/env python3
"""
/coder:add-feature - Add feature to existing codebase (brownfield).

Usage:
    python -m erirpg.commands.add_feature <description> [--json]
    python -m erirpg.commands.add_feature <program> <feature> "<description>" --reference <source>/<section> [--json]
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from erirpg.coder import ensure_planning_dir, load_roadmap


def load_behavior_spec(program: str, section: str, project_path: Optional[Path] = None) -> Optional[dict]:
    """Load a behavior spec from blueprints."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    program_dir = blueprints_dir / program

    # Handle nested sections
    if "/" in section:
        parts = section.split("/")
        behavior_file = program_dir
        for part in parts[:-1]:
            behavior_file = behavior_file / part
        behavior_file = behavior_file / f"{parts[-1]}-BEHAVIOR.md"
    else:
        behavior_file = program_dir / f"{section}-BEHAVIOR.md"

    if not behavior_file.exists():
        return None

    return {
        "program": program,
        "section": section,
        "file": str(behavior_file),
        "content": behavior_file.read_text()
    }


def load_target_conventions(program: str, project_path: Optional[Path] = None) -> Optional[dict]:
    """Load target program's overview/conventions from blueprints."""
    if project_path is None:
        project_path = Path.cwd()

    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    program_dir = blueprints_dir / program

    result = {
        "program": program,
        "conventions": None,
        "overview": None,
        "architecture_pattern": None
    }

    # Try to load overview
    overview_file = program_dir / "overview.md"
    if overview_file.exists():
        result["overview"] = overview_file.read_text()

    # Try to load conventions if separate
    conventions_file = program_dir / "conventions.md"
    if conventions_file.exists():
        result["conventions"] = conventions_file.read_text()

    # Try to load architecture
    arch_file = program_dir / "architecture.md"
    if arch_file.exists():
        result["architecture"] = arch_file.read_text()

    # Load index for metadata
    index_file = program_dir / "_index.json"
    if index_file.exists():
        result["index"] = json.loads(index_file.read_text())

    # Detect architecture pattern from content
    result["architecture_pattern"] = detect_architecture_pattern(result)

    return result if result["overview"] or result["conventions"] else None


def detect_architecture_pattern(target_info: dict) -> Optional[dict]:
    """Detect architecture pattern from target blueprints."""
    content = ""
    if target_info.get("overview"):
        content += target_info["overview"].lower()
    if target_info.get("architecture"):
        content += target_info["architecture"].lower()
    if target_info.get("conventions"):
        content += target_info["conventions"].lower()

    patterns = {
        "hexagonal": ["hexagonal", "ports and adapters", "port", "adapter", "domain"],
        "layered": ["layer", "service layer", "data layer", "presentation layer"],
        "mvc": ["model", "view", "controller", "mvc"],
        "clean": ["clean architecture", "use case", "entity", "interface adapter"],
        "modular": ["module", "plugin", "extension"],
        "microservices": ["microservice", "service mesh", "api gateway"],
        "event-driven": ["event", "message", "queue", "subscriber", "publisher"],
    }

    detected = None
    max_score = 0

    for pattern_name, keywords in patterns.items():
        score = sum(1 for kw in keywords if kw in content)
        if score > max_score:
            max_score = score
            detected = pattern_name

    if detected:
        layer_mapping = {
            "hexagonal": {"domain": "Core logic", "ports": "Interfaces", "adapters": "Implementations"},
            "layered": {"domain": "Business logic", "service": "Orchestration", "data": "Persistence"},
            "mvc": {"model": "Data/logic", "view": "Presentation", "controller": "Input handling"},
            "clean": {"entities": "Business objects", "use_cases": "Application logic", "adapters": "External"},
            "modular": {"core": "Shared logic", "modules": "Features", "plugins": "Extensions"},
        }
        return {
            "pattern": detected,
            "confidence": min(max_score / 3, 1.0),
            "layers": layer_mapping.get(detected, {"core": "Core", "adapters": "Adapters"})
        }

    return None


def parse_behavior_dependencies(behavior_content: str) -> dict:
    """Extract dependencies from behavior spec."""
    result = {
        "hard": [],
        "soft": [],
        "environment": []
    }

    lines = behavior_content.split("\n")
    current_section = None

    for line in lines:
        line_lower = line.lower().strip()
        if "hard dependencies" in line_lower:
            current_section = "hard"
        elif "soft dependencies" in line_lower:
            current_section = "soft"
        elif "environment" in line_lower and "##" in line:
            current_section = "environment"
        elif line.startswith("- ") and current_section:
            dep = line[2:].strip()
            if dep and not dep.startswith("["):
                result[current_section].append(dep)

    return result


def parse_resource_budget(behavior_content: str) -> dict:
    """Extract resource budget from behavior spec."""
    result = {
        "memory": {},
        "time": {},
        "constraints": []
    }

    lines = behavior_content.split("\n")
    current_section = None

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        if "## resource budget" in line_lower:
            current_section = "budget"
        elif "### memory" in line_lower:
            current_section = "memory"
        elif "### time" in line_lower:
            current_section = "time"
        elif "### constraints" in line_lower:
            current_section = "constraints"
        elif current_section == "memory" and "**" in line:
            if "vram" in line_lower:
                result["memory"]["vram"] = line.split(":")[-1].strip() if ":" in line else ""
            elif "ram" in line_lower:
                result["memory"]["ram"] = line.split(":")[-1].strip() if ":" in line else ""
        elif current_section == "time" and "**" in line:
            if "init" in line_lower:
                result["time"]["init"] = line.split(":")[-1].strip() if ":" in line else ""
            elif "per" in line_lower:
                result["time"]["per_op"] = line.split(":")[-1].strip() if ":" in line else ""
        elif current_section == "constraints" and line.startswith("- "):
            constraint = line[2:].strip()
            if constraint and not constraint.startswith("["):
                result["constraints"].append(constraint)

    return result


def parse_interface_contract(behavior_content: str) -> dict:
    """Extract interface contract from behavior spec."""
    result = {
        "input_type": None,
        "output_type": None,
        "error_handling": None,
        "decorators": []
    }

    lines = behavior_content.split("\n")
    in_interface = False

    for line in lines:
        line_lower = line.lower().strip()

        if "## interface contract" in line_lower:
            in_interface = True
        elif in_interface and line.startswith("##"):
            in_interface = False
        elif in_interface:
            if "input type" in line_lower and "**" in line:
                result["input_type"] = line.split(":")[-1].strip().strip("[]")
            elif "output type" in line_lower and "**" in line:
                result["output_type"] = line.split(":")[-1].strip().strip("[]")
            elif "error handling" in line_lower and "**" in line:
                result["error_handling"] = line.split(":")[-1].strip().strip("[]")
            elif "decorator" in line_lower and "**" in line:
                result["decorators"].append(line.split(":")[-1].strip().strip("[]"))

    return result


def parse_global_state_impact(behavior_content: str) -> dict:
    """Extract global state impact from behavior spec."""
    result = {
        "env_reads": [],
        "env_writes": [],
        "file_creates": [],
        "spawns_processes": False,
        "background_threads": False,
        "network_outbound": [],
        "global_mutations": [],
        "thread_safe": True
    }

    lines = behavior_content.split("\n")
    current_section = None

    for line in lines:
        line_lower = line.lower().strip()

        if "## global state impact" in line_lower:
            current_section = "global"
        elif current_section == "global" and line.startswith("##"):
            current_section = None
        elif current_section == "global":
            if "**reads:**" in line_lower:
                vals = line.split(":")[-1].strip().strip("[]")
                if vals.lower() != "none":
                    result["env_reads"] = [v.strip() for v in vals.split(",")]
            elif "**writes:**" in line_lower:
                vals = line.split(":")[-1].strip().strip("[]")
                if vals.lower() != "none":
                    result["env_writes"] = [v.strip() for v in vals.split(",")]
            elif "**creates:**" in line_lower:
                vals = line.split(":")[-1].strip().strip("[]")
                if vals.lower() != "none":
                    result["file_creates"] = [v.strip() for v in vals.split(",")]
            elif "**spawns:**" in line_lower:
                val = line.split(":")[-1].strip().strip("[]").lower()
                result["spawns_processes"] = val != "none"
            elif "**background threads:**" in line_lower:
                val = line.split(":")[-1].strip().strip("[]").lower()
                result["background_threads"] = val != "none" and val != "0"
            elif "**outbound:**" in line_lower:
                vals = line.split(":")[-1].strip().strip("[]")
                if vals.lower() != "none":
                    result["network_outbound"] = [v.strip() for v in vals.split(",")]
            elif "**sets:**" in line_lower:
                val = line.split(":")[-1].strip().strip("[]")
                if val.lower() != "none":
                    result["global_mutations"].append(val)
            elif "thread safety" in line_lower:
                result["thread_safe"] = "not thread-safe" not in line_lower

    return result


def parse_ownership_model(behavior_content: str) -> dict:
    """Extract ownership model from behavior spec."""
    result = {
        "inputs": [],
        "internal_state": [],
        "outputs": [],
        "rust_hints": []
    }

    lines = behavior_content.split("\n")
    current_section = None
    in_table = False

    for line in lines:
        line_lower = line.lower().strip()

        if "## ownership model" in line_lower:
            current_section = "ownership"
        elif current_section == "ownership" and line.startswith("## "):
            current_section = None
        elif current_section == "ownership":
            if "### inputs" in line_lower:
                current_section = "ownership_inputs"
                in_table = False
            elif "### internal state" in line_lower:
                current_section = "ownership_internal"
                in_table = False
            elif "### outputs" in line_lower:
                current_section = "ownership_outputs"
                in_table = False
            elif "### rust translation" in line_lower:
                current_section = "ownership_rust"
            elif current_section == "ownership_rust" and line.startswith("- "):
                result["rust_hints"].append(line[2:].strip())
            elif "|" in line and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2 and parts[0].lower() not in ["data", "lifetime"]:
                    entry = {"name": parts[0], "ownership": parts[1] if len(parts) > 1 else "",
                             "notes": parts[2] if len(parts) > 2 else ""}
                    if current_section == "ownership_inputs":
                        result["inputs"].append(entry)
                    elif current_section == "ownership_internal":
                        result["internal_state"].append(entry)
                    elif current_section == "ownership_outputs":
                        result["outputs"].append(entry)

    return result


def scan_target_interfaces(target_program: str, project_path: Optional[Path] = None) -> dict:
    """Scan target codebase for interface requirements."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "base_traits": [],
        "wrapper_types": [],
        "decorators": [],
        "naming_conventions": {},
        "error_patterns": []
    }

    planning_dir = ensure_planning_dir(project_path)
    blueprints_dir = planning_dir / "blueprints"
    program_dir = blueprints_dir / target_program

    if not program_dir.exists():
        return result

    # Scan all blueprint files for interface patterns
    for md_file in program_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        content = md_file.read_text().lower()

        # Look for trait/interface patterns
        if "trait " in content or "interface " in content or "protocol " in content:
            # Extract trait names
            import re
            traits = re.findall(r'(?:trait|interface|protocol)\s+(\w+)', content)
            result["base_traits"].extend(traits)

        # Look for wrapper type patterns
        wrapper_patterns = ["arc<", "rc<", "box<", "result<", "option<", "vec<",
                          "resourcehandle", "mutex<", "rwlock<"]
        for pattern in wrapper_patterns:
            if pattern in content:
                result["wrapper_types"].append(pattern.rstrip("<"))

        # Look for decorator/annotation patterns
        decorator_patterns = ["#[derive", "@dataclass", "@property", "#[cfg",
                             "@override", "@abstractmethod"]
        for pattern in decorator_patterns:
            if pattern in content:
                result["decorators"].append(pattern)

        # Look for error handling patterns
        error_patterns = ["result<", "anyhow::", "thiserror", "raises", "throws",
                         "-> error", "error::", "bail!"]
        for pattern in error_patterns:
            if pattern in content:
                result["error_patterns"].append(pattern)

    # Deduplicate
    result["base_traits"] = list(set(result["base_traits"]))
    result["wrapper_types"] = list(set(result["wrapper_types"]))
    result["decorators"] = list(set(result["decorators"]))
    result["error_patterns"] = list(set(result["error_patterns"]))

    return result


def check_ownership_compatibility(source_ownership: dict, target_info: dict) -> dict:
    """Check if source ownership model is compatible with target."""
    issues = []
    warnings = []

    # Check if target appears to be a memory-safe language (Rust-like)
    target_content = ""
    if target_info.get("overview"):
        target_content += target_info["overview"].lower()
    if target_info.get("conventions"):
        target_content += target_info["conventions"].lower()

    is_rust_like = any(kw in target_content for kw in
                       ["rust", "ownership", "borrow", "lifetime", "arc<", "mutex<"])

    if is_rust_like:
        # Check for problematic patterns
        for inp in source_ownership.get("inputs", []):
            ownership = inp.get("ownership", "").lower()
            if "move" in ownership and "config" not in inp.get("name", "").lower():
                warnings.append(f"Input '{inp.get('name')}' is consumed (moved) - verify caller doesn't need it after")

        for state in source_ownership.get("internal_state", []):
            lifetime = state.get("ownership", "").lower()
            if "'static" in lifetime:
                issues.append(f"Internal state '{state.get('name')}' has 'static lifetime - requires explicit cleanup")

        if not source_ownership.get("rust_hints"):
            warnings.append("No Rust translation hints provided - manual ownership analysis needed")

    return {
        "compatible": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "target_is_memory_safe": is_rust_like
    }


def check_side_effect_compatibility(source_side_effects: dict, target_info: dict) -> dict:
    """Check if source side effects are allowed in target."""
    issues = []
    warnings = []

    # Check if target appears to forbid global state
    target_content = ""
    if target_info.get("overview"):
        target_content += target_info["overview"].lower()
    if target_info.get("conventions"):
        target_content += target_info["conventions"].lower()

    forbids_global = any(kw in target_content for kw in
                         ["no global", "pure", "functional", "immutable", "no side effect"])

    if forbids_global:
        if source_side_effects.get("global_mutations"):
            issues.append(f"Source mutates global state: {source_side_effects['global_mutations']} - target forbids this")

        if source_side_effects.get("env_writes"):
            issues.append(f"Source writes env vars: {source_side_effects['env_writes']} - may be forbidden")

    if not source_side_effects.get("thread_safe"):
        warnings.append("Source is NOT thread-safe - verify target threading model")

    if source_side_effects.get("spawns_processes"):
        warnings.append("Source spawns processes - verify target allows subprocess creation")

    if source_side_effects.get("background_threads"):
        warnings.append("Source uses background threads - verify target async model")

    return {
        "compatible": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "target_forbids_global": forbids_global
    }


def add_feature(
    description: str,
    target_program: Optional[str] = None,
    feature_name: Optional[str] = None,
    reference: Optional[str] = None,
    project_path: Optional[Path] = None,
    output_json: bool = False
) -> dict:
    """Add a feature to an existing codebase."""
    if project_path is None:
        project_path = Path.cwd()

    result = {
        "command": "add-feature",
        "project": str(project_path),
        "description": description,
    }

    try:
        planning_dir = ensure_planning_dir(project_path)

        # Handle reference-based feature addition
        if reference and target_program:
            result["mode"] = "reference"
            result["target_program"] = target_program
            result["feature_name"] = feature_name or description.lower().replace(" ", "-")[:30]

            # Parse reference (source_program/section)
            if "/" not in reference:
                result["error"] = "Reference format: <source-program>/<section>"
                if output_json:
                    print(json.dumps(result, indent=2, default=str))
                return result

            ref_parts = reference.split("/", 1)
            source_program = ref_parts[0]
            source_section = ref_parts[1]
            result["reference"] = {
                "program": source_program,
                "section": source_section
            }

            # Load source behavior spec
            behavior = load_behavior_spec(source_program, source_section, project_path)
            if behavior:
                result["source_behavior"] = behavior
            else:
                result["warning"] = f"No behavior spec found for {reference}. Create with: /coder:blueprint add {source_program} {source_section} --extract-behavior"

            # Load target conventions
            target_conv = load_target_conventions(target_program, project_path)
            if target_conv:
                result["target_conventions"] = target_conv
            else:
                result["warning"] = (result.get("warning", "") +
                    f" No blueprint found for target {target_program}. Create with: /coder:blueprint add {target_program} overview").strip()

            # Parse behavior spec for all sections
            behavior_deps = None
            resource_budget = None
            interface_contract = None
            global_state = None
            ownership_model = None
            if behavior:
                behavior_deps = parse_behavior_dependencies(behavior["content"])
                resource_budget = parse_resource_budget(behavior["content"])
                interface_contract = parse_interface_contract(behavior["content"])
                global_state = parse_global_state_impact(behavior["content"])
                ownership_model = parse_ownership_model(behavior["content"])
                result["source_dependencies"] = behavior_deps
                result["source_resources"] = resource_budget
                result["source_interface"] = interface_contract
                result["source_global_state"] = global_state
                result["source_ownership"] = ownership_model

            # Scan target for interface requirements
            target_interfaces = None
            if target_conv:
                target_interfaces = scan_target_interfaces(target_program, project_path)
                result["target_interfaces"] = target_interfaces

            # Check compatibility
            ownership_compat = None
            side_effect_compat = None
            if ownership_model and target_conv:
                ownership_compat = check_ownership_compatibility(ownership_model, target_conv)
                result["ownership_compatibility"] = ownership_compat

            if global_state and target_conv:
                side_effect_compat = check_side_effect_compatibility(global_state, target_conv)
                result["side_effect_compatibility"] = side_effect_compat

            # Detect architecture pattern
            arch_pattern = None
            if target_conv:
                arch_pattern = target_conv.get("architecture_pattern")
                if arch_pattern:
                    result["target_architecture"] = arch_pattern

            # Create feature spec with reference
            feature_dir = planning_dir / "features"
            feature_dir.mkdir(exist_ok=True)

            feature_slug = result["feature_name"]
            feature_file = feature_dir / f"{target_program}-{feature_slug}.md"

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            feature_content = f"""---
feature: {description}
target_program: {target_program}
feature_name: {feature_slug}
reference_source: {reference}
created: {today}
mode: reference-port
---

# Feature: {description}

## Reference
Porting behavior from: **{reference}**

## Target Program
Implementing in: **{target_program}**

## Source Behavior
"""
            if behavior:
                feature_content += f"""
The behavior spec from {reference} defines:
- See: {behavior['file']}
- Load with: `/coder:blueprint load {reference} --behavior`

"""
            else:
                feature_content += f"""
> No behavior spec found. Extract it first:
> `/coder:blueprint add {source_program} {source_section} --extract-behavior`

"""

            feature_content += f"""
## Target Conventions
"""
            if target_conv and target_conv.get("overview"):
                feature_content += f"""
The target program {target_program} has conventions defined:
- See overview for patterns, language, frameworks

"""
            else:
                feature_content += f"""
> No blueprint found for target. Create it:
> `/coder:blueprint add {target_program} overview "<description>"`

"""

            # Add architectural gravity section
            feature_content += """
## Architectural Gravity

"""
            if arch_pattern:
                feature_content += f"""
**Detected Pattern:** {arch_pattern['pattern'].title()} (confidence: {arch_pattern['confidence']:.0%})

**Layer Mapping:**
"""
                for layer, desc in arch_pattern.get('layers', {}).items():
                    feature_content += f"- **{layer}:** {desc}\n"

                feature_content += f"""

**Implementation Strategy:**
1. Map behavior to DOMAIN layer first (pure logic, no framework deps)
2. Create ADAPTERS for framework-specific code
3. Never leak framework into domain

**Example Structure:**
```
Behavior: "{description}"
Domain:   {feature_slug.title().replace('-', '')}Trait with core methods
Adapter:  Framework{feature_slug.title().replace('-', '')} implements trait
```
"""
            else:
                feature_content += """
> Architecture pattern not detected. Analyze target blueprint.
> Default approach: Domain layer (pure logic) + Adapters (framework-specific)
"""

            # Add dependency mapping section
            feature_content += """
## Dependency Mapping

"""
            if behavior_deps:
                if behavior_deps.get("hard"):
                    feature_content += "### Hard Dependencies (must satisfy)\n"
                    for dep in behavior_deps["hard"]:
                        feature_content += f"- [ ] {dep}\n"
                    feature_content += "\n"

                if behavior_deps.get("soft"):
                    feature_content += "### Soft Dependencies (interface required)\n"
                    for dep in behavior_deps["soft"]:
                        feature_content += f"- [ ] {dep}\n"
                    feature_content += "\n"

                if behavior_deps.get("environment"):
                    feature_content += "### Environment Requirements\n"
                    for dep in behavior_deps["environment"]:
                        feature_content += f"- [ ] {dep}\n"
                    feature_content += "\n"
            else:
                feature_content += "> Dependencies not specified in behavior spec. Review source manually.\n\n"

            # Add interface contract section
            feature_content += """
## Interface Contract

"""
            if interface_contract:
                feature_content += "### Source Signatures\n"
                if interface_contract.get("input_type"):
                    feature_content += f"- **Input type:** {interface_contract['input_type']}\n"
                if interface_contract.get("output_type"):
                    feature_content += f"- **Output type:** {interface_contract['output_type']}\n"
                if interface_contract.get("error_handling"):
                    feature_content += f"- **Error handling:** {interface_contract['error_handling']}\n"
                for dec in interface_contract.get("decorators", []):
                    feature_content += f"- **Decorator:** {dec}\n"
                feature_content += "\n"

            feature_content += "### Target Must Adapt To\n"
            if target_interfaces:
                if target_interfaces.get("base_traits"):
                    feature_content += f"- **Base traits:** {', '.join(target_interfaces['base_traits'][:5])}\n"
                if target_interfaces.get("wrapper_types"):
                    feature_content += f"- **Wrapper types:** {', '.join(target_interfaces['wrapper_types'][:5])}\n"
                if target_interfaces.get("decorators"):
                    feature_content += f"- **Decorators:** {', '.join(target_interfaces['decorators'][:5])}\n"
                if target_interfaces.get("error_patterns"):
                    feature_content += f"- **Error patterns:** {', '.join(target_interfaces['error_patterns'][:3])}\n"
            else:
                feature_content += "> Scan target codebase to fill interface requirements\n"
            feature_content += "\n"

            # Add global state impact section
            feature_content += """
## Global State Impact

"""
            if global_state:
                feature_content += "### Source Side Effects\n"
                if global_state.get("env_reads"):
                    feature_content += f"- **Reads env:** {', '.join(global_state['env_reads'])}\n"
                if global_state.get("env_writes"):
                    feature_content += f"- **Writes env:** {', '.join(global_state['env_writes'])}\n"
                if global_state.get("file_creates"):
                    feature_content += f"- **Creates files:** {', '.join(global_state['file_creates'])}\n"
                if global_state.get("network_outbound"):
                    feature_content += f"- **Network outbound:** {', '.join(global_state['network_outbound'])}\n"
                if global_state.get("global_mutations"):
                    feature_content += f"- **Global mutations:** {', '.join(global_state['global_mutations'])}\n"
                feature_content += f"- **Thread safe:** {'Yes' if global_state.get('thread_safe') else 'NO'}\n"
                feature_content += f"- **Background threads:** {'Yes' if global_state.get('background_threads') else 'No'}\n"
                feature_content += "\n"

                if side_effect_compat:
                    if side_effect_compat.get("issues"):
                        feature_content += "### ❌ Compatibility Issues\n"
                        for issue in side_effect_compat["issues"]:
                            feature_content += f"- {issue}\n"
                        feature_content += "\n"
                    if side_effect_compat.get("warnings"):
                        feature_content += "### ⚠️ Warnings\n"
                        for warning in side_effect_compat["warnings"]:
                            feature_content += f"- {warning}\n"
                        feature_content += "\n"
            else:
                feature_content += "> Global state impact not specified in behavior spec.\n\n"

            # Add ownership model section
            feature_content += """
## Ownership Model

"""
            if ownership_model:
                if ownership_model.get("inputs"):
                    feature_content += "### Inputs\n"
                    feature_content += "| Data | Ownership | Notes |\n"
                    feature_content += "|------|-----------|-------|\n"
                    for inp in ownership_model["inputs"]:
                        feature_content += f"| {inp.get('name', '')} | {inp.get('ownership', '')} | {inp.get('notes', '')} |\n"
                    feature_content += "\n"

                if ownership_model.get("outputs"):
                    feature_content += "### Outputs\n"
                    feature_content += "| Data | Ownership | Notes |\n"
                    feature_content += "|------|-----------|-------|\n"
                    for out in ownership_model["outputs"]:
                        feature_content += f"| {out.get('name', '')} | {out.get('ownership', '')} | {out.get('notes', '')} |\n"
                    feature_content += "\n"

                if ownership_model.get("rust_hints"):
                    feature_content += "### Rust Translation Hints\n"
                    for hint in ownership_model["rust_hints"]:
                        feature_content += f"- {hint}\n"
                    feature_content += "\n"

                if ownership_compat:
                    if ownership_compat.get("issues"):
                        feature_content += "### ❌ Compatibility Issues\n"
                        for issue in ownership_compat["issues"]:
                            feature_content += f"- {issue}\n"
                        feature_content += "\n"
                    if ownership_compat.get("warnings"):
                        feature_content += "### ⚠️ Warnings\n"
                        for warning in ownership_compat["warnings"]:
                            feature_content += f"- {warning}\n"
                        feature_content += "\n"
            else:
                feature_content += "> Ownership model not specified in behavior spec.\n\n"

            # Add resource budget section
            feature_content += """
## Resource Budget

"""
            if resource_budget:
                if resource_budget.get("memory"):
                    feature_content += "### Memory\n"
                    for key, val in resource_budget["memory"].items():
                        if val:
                            feature_content += f"- **{key.upper()}:** {val}\n"
                    feature_content += "\n"

                if resource_budget.get("time"):
                    feature_content += "### Time\n"
                    for key, val in resource_budget["time"].items():
                        if val:
                            feature_content += f"- **{key}:** {val}\n"
                    feature_content += "\n"

                if resource_budget.get("constraints"):
                    feature_content += "### Constraints\n"
                    for constraint in resource_budget["constraints"]:
                        feature_content += f"- {constraint}\n"
                    feature_content += "\n"

                feature_content += """
**Target Compatibility:**
- [ ] Can meet memory requirements
- [ ] Can meet time requirements
- [ ] All constraints acknowledged

"""
            else:
                feature_content += "> Resource budget not specified in behavior spec.\n\n"

            feature_content += f"""
## Implementation Plan

### Before Implementation
1. **Load source behavior**: `/coder:blueprint load {reference} --behavior`
2. **Load target conventions**: `/coder:blueprint load {target_program}/overview`
3. **Verify interface requirements** - check "Target Must Adapt To" section
4. **Check ownership compatibility** - resolve any ❌ issues above
5. **Check side effect compatibility** - resolve any ❌ issues above

### Implementation
6. **Satisfy dependencies** - stub or implement each requirement
7. **Map to domain layer** - pure logic, no framework deps
8. **Create adapters** - framework-specific implementations
9. **Implement state machine** - preserve all states and transitions
10. **Add tests** - verify all test contracts from behavior spec

### After Implementation
11. **Run behavior diff**: `/coder:verify-behavior {target_program}/{feature_slug}`
12. **Resolve all ❌ violations** - fix before marking done
13. **Review all ⚠️ warnings** - manual verification required
14. **Verify resource budget** - test against constraints

## Key Decisions
- [ ] Language/framework choices aligned with target
- [ ] API design matches target conventions
- [ ] Error handling follows target patterns
- [ ] Testing approach per target norms
- [ ] State machine preserved from source
- [ ] Ownership model compatible with target
- [ ] No forbidden side effects for target

## Behavior Verification Checklist
<!-- Run /coder:verify-behavior after implementation -->

| Behavior Spec | Code Check | Status |
|---------------|------------|--------|
| Input types match | | ⏳ |
| Output types match | | ⏳ |
| State machine preserved | | ⏳ |
| No forbidden side effects | | ⏳ |
| Ownership compatible | | ⏳ |
| Test contracts have tests | | ⏳ |
| Resource budget verified | | ⏳ Manual |

## Files to Create
<!-- List files in target's structure, organized by layer -->

### Domain Layer
- `src/domain/{feature_slug}.rs` (or appropriate extension)

### Adapters
- `src/adapters/{feature_slug}_impl.rs`

### Tests
- `tests/{feature_slug}_test.rs`

## Notes
<!-- Implementation notes, gotchas from porting -->
"""
            feature_file.write_text(feature_content)
            result["feature_file"] = str(feature_file)

            result["message"] = f"Reference feature created: {target_program}/{feature_slug}"
            result["next_steps"] = [
                f"Load source behavior: /coder:blueprint load {reference} --behavior",
                f"Load target conventions: /coder:blueprint load {target_program}/overview",
                "Review dependency mapping and satisfy requirements",
                "Verify resource budget compatibility",
                "Plan implementation in target's style",
                f"Run /coder:plan-phase for the feature"
            ]

        else:
            # Standard feature addition (existing logic)
            result["mode"] = "standard"

            # Generate branch name
            slug = description.lower().replace(" ", "-")[:30]
            branch_name = f"feature/{slug}"

            result["branch"] = branch_name

            # Count existing phases and add as new phase
            roadmap = load_roadmap(project_path)
            existing = len(roadmap.get("phases", []))
            phase_number = existing + 1

            # Append to roadmap
            roadmap_path = planning_dir / "ROADMAP.md"
            new_section = f"""

## Phase {phase_number}: Feature - {description[:40]}
**Status:** pending
**Goal:** {description}

### Success Criteria
- [ ] Feature implemented
- [ ] Tests passing
"""

            if roadmap_path.exists():
                content = roadmap_path.read_text()
                roadmap_path.write_text(content + new_section)

            result["phase_number"] = phase_number

            # Create feature directory
            feature_dir = planning_dir / "features"
            feature_dir.mkdir(exist_ok=True)

            feature_file = feature_dir / f"{branch_name.replace('/', '-')}.md"
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            feature_content = f"""---
feature: {description}
branch: {branch_name}
created: {today}
phase: {phase_number}
---

# Feature: {description}

## Description
{description}

## Impact Analysis
- **Files affected**: [List files]
- **Components affected**: [List components]

## Implementation Plan
1. [Step 1]
2. [Step 2]
"""
            feature_file.write_text(feature_content)
            result["feature_file"] = str(feature_file)

            result["message"] = f"Feature set up as phase {phase_number}"
            result["next_steps"] = [
                f"Create branch: git checkout -b {branch_name}",
                f"Run /coder:plan-phase {phase_number}",
                f"Run /coder:execute-phase {phase_number}"
            ]

    except Exception as e:
        result["error"] = str(e)

    if output_json:
        print(json.dumps(result, indent=2, default=str))

    return result


def main():
    """CLI entry point."""
    output_json = "--json" in sys.argv

    # Check for --reference flag (new mode)
    reference = None
    if "--reference" in sys.argv:
        idx = sys.argv.index("--reference")
        if idx + 1 < len(sys.argv):
            reference = sys.argv[idx + 1]

    # Filter args
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    # Remove reference value from args if present
    if reference and reference in args:
        args.remove(reference)

    if not args:
        print(json.dumps({
            "error": "Feature description required",
            "usage": {
                "standard": "add_feature <description>",
                "reference": 'add_feature <target-program> <feature-name> "<description>" --reference <source>/<section>'
            },
            "examples": {
                "standard": 'add_feature "Add user authentication"',
                "reference": 'add_feature eritrainer sana "Sana model training" --reference onetrainer/models/sana'
            }
        }, indent=2))
        sys.exit(1)

    if reference:
        # Reference mode: target_program feature_name description
        if len(args) < 3:
            print(json.dumps({
                "error": "Reference mode requires: <target-program> <feature-name> <description>",
                "example": 'add_feature eritrainer sana "Sana model training" --reference onetrainer/models/sana'
            }, indent=2))
            sys.exit(1)

        target_program = args[0]
        feature_name = args[1]
        description = " ".join(args[2:])

        add_feature(
            description,
            target_program=target_program,
            feature_name=feature_name,
            reference=reference,
            output_json=output_json
        )
    else:
        # Standard mode
        description = " ".join(args)
        add_feature(description, output_json=output_json)


if __name__ == "__main__":
    main()
