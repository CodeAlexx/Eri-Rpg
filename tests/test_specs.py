"""
Test Phase 3: Spec Schema and CLI.

Tests for spec models, validation, normalization, and CLI commands.
"""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path

from erirpg.specs import (
    SPEC_VERSION,
    BaseSpec,
    TaskSpec,
    ProjectSpec,
    TransplantSpec,
    ValidationError,
    create_spec,
    load_spec,
    validate_spec,
    get_spec_template,
    get_specs_dir,
    list_specs,
    save_spec_to_project,
)


class TestBaseSpec:
    """Tests for BaseSpec base class."""

    def test_base_spec_defaults(self):
        """Base spec should have sensible defaults."""
        spec = BaseSpec()
        assert spec.version == SPEC_VERSION
        assert spec.tags == []
        assert spec.notes == ""
        assert isinstance(spec.created_at, datetime)
        assert isinstance(spec.updated_at, datetime)

    def test_base_spec_validate_requires_id(self):
        """Validation should fail without ID."""
        spec = BaseSpec()
        errors = spec.validate()
        assert "id is required" in errors

    def test_base_spec_validate_requires_version(self):
        """Validation should fail without version."""
        spec = BaseSpec(id="test", version="")
        errors = spec.validate()
        assert "version is required" in errors

    def test_base_spec_normalize_cleans_tags(self):
        """Normalization should clean up tags."""
        spec = BaseSpec(id="test", tags=["  Tag1  ", "TAG2", "", "  "])
        spec.normalize()
        assert spec.tags == ["tag1", "tag2"]

    def test_base_spec_to_dict(self):
        """Serialization should produce valid dict."""
        spec = BaseSpec(id="test-123", version="1.0", notes="Test note")
        data = spec.to_dict()
        assert data["id"] == "test-123"
        assert data["version"] == "1.0"
        assert data["notes"] == "Test note"
        assert "created_at" in data
        assert "updated_at" in data

    def test_base_spec_from_dict(self):
        """Deserialization should restore spec."""
        now = datetime.now()
        data = {
            "id": "test-123",
            "version": "1.0",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "tags": ["test"],
            "notes": "A note",
        }
        spec = BaseSpec.from_dict(data)
        assert spec.id == "test-123"
        assert spec.version == "1.0"
        assert spec.tags == ["test"]
        assert spec.notes == "A note"


class TestTaskSpec:
    """Tests for TaskSpec."""

    def test_task_spec_defaults(self):
        """Task spec should have correct defaults."""
        spec = TaskSpec()
        assert spec.spec_type == "task"
        assert spec.priority == "normal"
        assert spec.status == "pending"
        assert spec.blocked_by == []

    def test_task_spec_validate_requires_name(self):
        """Validation should require name."""
        spec = TaskSpec(id="test")
        errors = spec.validate()
        assert "name is required" in errors

    def test_task_spec_validate_task_type(self):
        """Validation should check task_type values."""
        spec = TaskSpec(id="test", name="Test", task_type="invalid")
        errors = spec.validate()
        assert any("task_type" in e for e in errors)

    def test_task_spec_validate_extract_requires_source_and_query(self):
        """Extract tasks need source_project and query."""
        spec = TaskSpec(id="test", name="Test", task_type="extract")
        errors = spec.validate()
        assert "source_project required for extract task" in errors
        assert "query required for extract task" in errors

    def test_task_spec_validate_plan_requires_feature_and_target(self):
        """Plan tasks need feature_file and target_project."""
        spec = TaskSpec(id="test", name="Test", task_type="plan")
        errors = spec.validate()
        assert "feature_file required for plan task" in errors
        assert "target_project required for plan task" in errors

    def test_task_spec_normalize_generates_id(self):
        """Normalization should generate ID from name."""
        spec = TaskSpec(name="My Test Task")
        spec.normalize()
        assert spec.id.startswith("task-my-test-task-")

    def test_task_spec_normalize_cleans_fields(self):
        """Normalization should clean string fields."""
        spec = TaskSpec(
            name="  Test Name  ",
            description="  Desc  ",
            task_type="  EXTRACT  ",
            priority="  HIGH  ",
        )
        spec.normalize()
        assert spec.name == "Test Name"
        assert spec.description == "Desc"
        assert spec.task_type == "extract"
        assert spec.priority == "high"

    def test_task_spec_serialization_roundtrip(self):
        """Task spec should survive serialization roundtrip."""
        spec = TaskSpec(
            id="test-123",
            name="Extract Feature",
            task_type="extract",
            source_project="onetrainer",
            query="loss function",
            priority="high",
            status="in_progress",
            tags=["feature"],
        )
        data = spec.to_dict()
        restored = TaskSpec.from_dict(data)
        assert restored.id == spec.id
        assert restored.name == spec.name
        assert restored.task_type == spec.task_type
        assert restored.source_project == spec.source_project
        assert restored.query == spec.query


class TestProjectSpec:
    """Tests for ProjectSpec."""

    def test_project_spec_defaults(self):
        """Project spec should have correct defaults."""
        spec = ProjectSpec()
        assert spec.spec_type == "project"
        assert spec.language == "python"
        assert spec.directories == []
        assert spec.files == []
        assert spec.dependencies == []

    def test_project_spec_validate_requires_name(self):
        """Validation should require name."""
        spec = ProjectSpec(id="test", core_feature="A feature")
        errors = spec.validate()
        assert "name is required" in errors

    def test_project_spec_validate_requires_core_feature(self):
        """Validation should require core_feature."""
        spec = ProjectSpec(id="test", name="my-project")
        errors = spec.validate()
        assert any("core_feature is required" in e for e in errors)

    def test_project_spec_validate_language(self):
        """Validation should check language values."""
        spec = ProjectSpec(id="test", name="test", core_feature="test", language="javascript")
        errors = spec.validate()
        assert any("language" in e for e in errors)

    def test_project_spec_normalize_generates_id(self):
        """Normalization should generate ID from name."""
        spec = ProjectSpec(name="My Cool Project", core_feature="test")
        spec.normalize()
        assert spec.id.startswith("project-my-cool-project-")

    def test_project_spec_serialization_roundtrip(self):
        """Project spec should survive serialization roundtrip."""
        spec = ProjectSpec(
            id="project-test",
            name="test-app",
            core_feature="CLI tool for testing",
            language="python",
            framework="click",
            directories=["src", "tests"],
            dependencies=["click", "pytest"],
        )
        data = spec.to_dict()
        restored = ProjectSpec.from_dict(data)
        assert restored.name == spec.name
        assert restored.core_feature == spec.core_feature
        assert restored.directories == spec.directories
        assert restored.dependencies == spec.dependencies


class TestTransplantSpec:
    """Tests for TransplantSpec."""

    def test_transplant_spec_defaults(self):
        """Transplant spec should have correct defaults."""
        spec = TransplantSpec()
        assert spec.spec_type == "transplant"
        assert spec.components == []
        assert spec.mappings == []
        assert spec.wiring == []

    def test_transplant_spec_validate_requires_projects(self):
        """Validation should require source and target projects."""
        spec = TransplantSpec(id="test", name="test", feature_name="test")
        errors = spec.validate()
        assert "source_project is required" in errors
        assert "target_project is required" in errors

    def test_transplant_spec_validate_requires_feature(self):
        """Validation should require feature_name or feature_file."""
        spec = TransplantSpec(
            id="test", name="test",
            source_project="a", target_project="b"
        )
        errors = spec.validate()
        assert "feature_name or feature_file is required" in errors

    def test_transplant_spec_normalize_generates_id(self):
        """Normalization should generate ID from name."""
        spec = TransplantSpec(
            name="Transplant Loss Function",
            source_project="a",
            target_project="b",
            feature_name="loss"
        )
        spec.normalize()
        assert spec.id.startswith("transplant-transplant-loss-function-")

    def test_transplant_spec_serialization_roundtrip(self):
        """Transplant spec should survive serialization roundtrip."""
        spec = TransplantSpec(
            id="transplant-test",
            name="loss-transplant",
            source_project="onetrainer",
            target_project="eritrainer",
            feature_name="masked_loss",
            components=["util/loss.py"],
            mappings=[{"source": "compute_loss", "target": "new", "action": "CREATE"}],
        )
        data = spec.to_dict()
        restored = TransplantSpec.from_dict(data)
        assert restored.name == spec.name
        assert restored.source_project == spec.source_project
        assert restored.components == spec.components
        assert restored.mappings == spec.mappings


class TestSpecFactory:
    """Tests for spec factory functions."""

    def test_create_spec_task(self):
        """create_spec should create TaskSpec."""
        spec = create_spec("task", name="Test Task")
        assert isinstance(spec, TaskSpec)
        assert spec.name == "Test Task"
        assert spec.id  # Should be generated

    def test_create_spec_project(self):
        """create_spec should create ProjectSpec."""
        spec = create_spec("project", name="test-project", core_feature="testing")
        assert isinstance(spec, ProjectSpec)
        assert spec.name == "test-project"
        assert spec.core_feature == "testing"

    def test_create_spec_transplant(self):
        """create_spec should create TransplantSpec."""
        spec = create_spec(
            "transplant",
            name="test",
            source_project="a",
            target_project="b",
            feature_name="feat"
        )
        assert isinstance(spec, TransplantSpec)

    def test_create_spec_invalid_type(self):
        """create_spec should raise for unknown type."""
        with pytest.raises(ValueError, match="Unknown spec type"):
            create_spec("invalid")

    def test_validate_spec_valid(self):
        """validate_spec should return True for valid spec."""
        spec = TaskSpec(
            id="test",
            name="Test",
            task_type="extract",
            source_project="proj",
            query="feature"
        )
        is_valid, errors = validate_spec(spec)
        assert is_valid
        assert errors == []

    def test_validate_spec_invalid(self):
        """validate_spec should return False with errors for invalid spec."""
        spec = TaskSpec()  # Missing everything
        is_valid, errors = validate_spec(spec)
        assert not is_valid
        assert len(errors) > 0


class TestSpecTemplates:
    """Tests for spec templates."""

    def test_get_template_task(self):
        """Should return task template."""
        template = get_spec_template("task")
        assert template["spec_type"] == "task"
        assert "name" in template
        assert "task_type" in template

    def test_get_template_project(self):
        """Should return project template."""
        template = get_spec_template("project")
        assert template["spec_type"] == "project"
        assert "language" in template
        assert "core_feature" in template

    def test_get_template_transplant(self):
        """Should return transplant template."""
        template = get_spec_template("transplant")
        assert template["spec_type"] == "transplant"
        assert "source_project" in template
        assert "target_project" in template

    def test_get_template_invalid(self):
        """Should raise for unknown type."""
        with pytest.raises(ValueError, match="Unknown spec type"):
            get_spec_template("invalid")


class TestSpecStorage:
    """Tests for spec storage utilities."""

    def test_get_specs_dir(self, tmp_path):
        """Should return correct specs directory path."""
        specs_dir = get_specs_dir(str(tmp_path))
        assert specs_dir == str(tmp_path / ".eri-rpg" / "specs")

    def test_list_specs_empty(self, tmp_path):
        """Should return empty list for project without specs."""
        specs = list_specs(str(tmp_path))
        assert specs == []

    def test_list_specs_finds_all(self, tmp_path):
        """Should find all spec files."""
        specs_dir = tmp_path / ".eri-rpg" / "specs"
        specs_dir.mkdir(parents=True)

        # Create some specs
        (specs_dir / "task-1.json").write_text(json.dumps({
            "spec_type": "task", "id": "task-1", "name": "Task 1"
        }))
        (specs_dir / "project-1.json").write_text(json.dumps({
            "spec_type": "project", "id": "project-1", "name": "Project 1"
        }))

        specs = list_specs(str(tmp_path))
        assert len(specs) == 2

    def test_list_specs_filters_by_type(self, tmp_path):
        """Should filter specs by type."""
        specs_dir = tmp_path / ".eri-rpg" / "specs"
        specs_dir.mkdir(parents=True)

        (specs_dir / "task-1.json").write_text(json.dumps({
            "spec_type": "task", "id": "task-1", "name": "Task 1"
        }))
        (specs_dir / "project-1.json").write_text(json.dumps({
            "spec_type": "project", "id": "project-1", "name": "Project 1"
        }))

        task_specs = list_specs(str(tmp_path), spec_type="task")
        assert len(task_specs) == 1
        assert "task-1.json" in task_specs[0]

    def test_save_spec_to_project(self, tmp_path):
        """Should save spec to project's specs directory."""
        spec = TaskSpec(id="my-task", name="Test")
        path = save_spec_to_project(spec, str(tmp_path))

        assert os.path.exists(path)
        assert "my-task.json" in path

        # Verify content
        with open(path) as f:
            data = json.load(f)
        assert data["id"] == "my-task"


class TestSpecFilePersistence:
    """Tests for spec file save/load."""

    def test_task_spec_save_load(self, tmp_path):
        """Task spec should persist to file correctly."""
        spec = TaskSpec(
            id="test-task",
            name="Test Task",
            task_type="extract",
            source_project="proj",
            query="feature",
        )
        path = str(tmp_path / "task.json")
        spec.save(path)

        loaded = load_spec(path)
        assert isinstance(loaded, TaskSpec)
        assert loaded.id == "test-task"
        assert loaded.task_type == "extract"

    def test_project_spec_save_load(self, tmp_path):
        """Project spec should persist to file correctly."""
        spec = ProjectSpec(
            id="test-project",
            name="test",
            core_feature="testing",
            language="python",
        )
        path = str(tmp_path / "project.json")
        spec.save(path)

        loaded = load_spec(path)
        assert isinstance(loaded, ProjectSpec)
        assert loaded.id == "test-project"
        assert loaded.language == "python"

    def test_transplant_spec_save_load(self, tmp_path):
        """Transplant spec should persist to file correctly."""
        spec = TransplantSpec(
            id="test-transplant",
            name="test",
            source_project="a",
            target_project="b",
            feature_name="feat",
        )
        path = str(tmp_path / "transplant.json")
        spec.save(path)

        loaded = load_spec(path)
        assert isinstance(loaded, TransplantSpec)
        assert loaded.source_project == "a"
        assert loaded.target_project == "b"


class TestSpecCLI:
    """Tests for spec CLI commands."""

    def test_spec_new_creates_file(self, tmp_path):
        """spec new should create a spec file."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        runner = CliRunner()
        output_path = str(tmp_path / "new-task.json")

        result = runner.invoke(cli, ["spec", "new", "task", "-o", output_path, "-n", "My Task"])
        assert result.exit_code == 0
        assert os.path.exists(output_path)

        # Verify it's valid
        spec = load_spec(output_path)
        assert spec.name == "My Task"
        assert spec.spec_type == "task"

    def test_spec_validate_valid(self, tmp_path):
        """spec validate should pass for valid spec."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        # Create a valid spec
        spec = TaskSpec(
            id="test",
            name="Test",
            task_type="extract",
            source_project="proj",
            query="feature"
        )
        path = str(tmp_path / "valid.json")
        spec.save(path)

        runner = CliRunner()
        result = runner.invoke(cli, ["spec", "validate", path])
        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_spec_validate_invalid(self, tmp_path):
        """spec validate should fail for invalid spec."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        # Create an invalid spec (missing required fields)
        path = str(tmp_path / "invalid.json")
        with open(path, "w") as f:
            json.dump({"spec_type": "task", "id": "", "name": ""}, f)

        runner = CliRunner()
        result = runner.invoke(cli, ["spec", "validate", path])
        assert result.exit_code == 1
        assert "Invalid" in result.output

    def test_spec_show_displays_content(self, tmp_path):
        """spec show should display spec content."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        spec = TaskSpec(
            id="test-task",
            name="Display Test",
            task_type="extract",
            source_project="source-proj",
            query="loss"
        )
        path = str(tmp_path / "show.json")
        spec.save(path)

        runner = CliRunner()
        result = runner.invoke(cli, ["spec", "show", path])
        assert result.exit_code == 0
        assert "Display Test" in result.output
        assert "source-proj" in result.output

    def test_spec_show_json_output(self, tmp_path):
        """spec show --json should output valid JSON."""
        from click.testing import CliRunner
        from erirpg.cli import cli

        spec = TaskSpec(id="test", name="Test")
        path = str(tmp_path / "json.json")
        spec.save(path)

        runner = CliRunner()
        result = runner.invoke(cli, ["spec", "show", path, "--json"])
        assert result.exit_code == 0

        # Should be valid JSON
        data = json.loads(result.output)
        assert data["name"] == "Test"

    def test_spec_list_shows_specs(self, tmp_path, monkeypatch):
        """spec list should show all specs."""
        from click.testing import CliRunner
        from erirpg.cli import cli
        from erirpg.registry import Registry

        # Create some specs
        specs_dir = tmp_path / ".eri-rpg" / "specs"
        specs_dir.mkdir(parents=True)

        TaskSpec(id="task-1", name="Task One").save(str(specs_dir / "task-1.json"))
        ProjectSpec(id="proj-1", name="Project One", core_feature="test").save(
            str(specs_dir / "proj-1.json")
        )

        # Register the temp project (clean up first if exists)
        from erirpg.config import set_tier

        registry = Registry.get_instance()
        if "test-proj" in registry.projects:
            registry.remove("test-proj")
        registry.add("test-proj", str(tmp_path), "python")
        set_tier(str(tmp_path), "full")  # spec-list requires full tier

        try:
            runner = CliRunner()
            result = runner.invoke(cli, ["spec", "list", "test-proj"])
            assert result.exit_code == 0
            assert "Task One" in result.output
            assert "Project One" in result.output
        finally:
            # Cleanup
            registry.remove("test-proj")

    def test_spec_list_filter_by_type(self, tmp_path):
        """spec list -t should filter by type."""
        from click.testing import CliRunner
        from erirpg.cli import cli
        from erirpg.registry import Registry

        specs_dir = tmp_path / ".eri-rpg" / "specs"
        specs_dir.mkdir(parents=True)

        TaskSpec(id="task-1", name="Task One").save(str(specs_dir / "task-1.json"))
        ProjectSpec(id="proj-1", name="Project One", core_feature="test").save(
            str(specs_dir / "proj-1.json")
        )

        # Register the temp project (clean up first if exists)
        from erirpg.config import set_tier

        registry = Registry.get_instance()
        if "test-proj-filter" in registry.projects:
            registry.remove("test-proj-filter")
        registry.add("test-proj-filter", str(tmp_path), "python")
        set_tier(str(tmp_path), "full")  # spec-list requires full tier

        try:
            runner = CliRunner()
            result = runner.invoke(cli, ["spec", "list", "test-proj-filter", "-t", "task"])
            assert result.exit_code == 0
            assert "Task One" in result.output
            assert "Project One" not in result.output
        finally:
            # Cleanup
            registry.remove("test-proj-filter")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
