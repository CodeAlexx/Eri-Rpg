"""
CLI Python template for command-line applications.

Creates a Python CLI project structure with Click:
    {project}/
    ├── src/{name}/
    │   ├── __init__.py
    │   ├── cli.py            # Click CLI entry
    │   └── main.py           # Core logic stub
    ├── tests/
    │   ├── __init__.py
    │   └── test_cli.py
    ├── pyproject.toml
    └── README.md
"""

from typing import TYPE_CHECKING, List

from erirpg.templates.base import BaseTemplate, ScaffoldFile

if TYPE_CHECKING:
    from erirpg.specs import ProjectSpec


class CLIPythonTemplate(BaseTemplate):
    """Python CLI application template with Click."""

    @property
    def name(self) -> str:
        return "cli-python"

    @property
    def description(self) -> str:
        return "Python CLI application with Click"

    @property
    def languages(self) -> List[str]:
        return ["python"]

    @property
    def default_framework(self) -> str:
        return "click"

    def get_directories(self, spec: "ProjectSpec") -> List[str]:
        slug = self._slugify(spec.name)
        return [
            "src",
            f"src/{slug}",
            "tests",
        ]

    def get_dependencies(self, spec: "ProjectSpec") -> List[str]:
        return [
            "click>=8.1.0",
        ]

    def get_dev_dependencies(self, spec: "ProjectSpec") -> List[str]:
        return [
            "pytest>=8.0.0",
            "ruff>=0.3.0",
        ]

    def get_files(self, spec: "ProjectSpec") -> List[ScaffoldFile]:
        name = spec.name
        slug = self._slugify(name)
        desc = self._format_description(spec)

        return [
            # Source package
            ScaffoldFile(
                path=f"src/{slug}/__init__.py",
                content=self._init_py(name, desc),
                phase="001",
                description="Package init with version",
            ),
            ScaffoldFile(
                path=f"src/{slug}/cli.py",
                content=self._cli_py(name, slug, desc),
                phase="001",
                description="CLI entry point with Click",
            ),
            ScaffoldFile(
                path=f"src/{slug}/main.py",
                content=self._main_py(desc),
                phase="001",
                description="Core application logic",
            ),

            # Tests
            ScaffoldFile(
                path="tests/__init__.py",
                content='"""Test package."""\n',
                phase="001",
            ),
            ScaffoldFile(
                path="tests/test_cli.py",
                content=self._test_cli_py(slug),
                phase="001",
                description="CLI tests",
            ),

            # Project files
            ScaffoldFile(
                path="pyproject.toml",
                content=self._pyproject_toml(name, slug, desc, spec),
                phase="001",
                description="Project configuration",
            ),
            ScaffoldFile(
                path="README.md",
                content=self._readme_md(name, slug, desc),
                phase="001",
                description="Project README",
            ),
        ]

    def _init_py(self, name: str, desc: str) -> str:
        return f'''"""
{name}

{desc}
"""

__version__ = "0.1.0"
'''

    def _cli_py(self, name: str, slug: str, desc: str) -> str:
        return f'''"""
CLI Entry Point

Command-line interface for {name}.
{desc}
"""

import click

from {slug} import __version__
from {slug}.main import run


@click.group()
@click.version_option(version=__version__)
def cli():
    """{desc}"""
    pass


@cli.command()
@click.argument("name", default="World")
def hello(name: str):
    """Say hello to NAME."""
    result = run(name)
    click.echo(result)


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def status(verbose: bool):
    """Show application status."""
    click.echo(f"{{__name__}} v{{__version__}}")
    if verbose:
        click.echo("All systems operational.")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
'''

    def _main_py(self, desc: str) -> str:
        return f'''"""
Core Application Logic

{desc}
"""


def run(name: str) -> str:
    """Main entry point for the application.

    Args:
        name: Name to greet

    Returns:
        Greeting message
    """
    return f"Hello, {{name}}!"


def process(data: dict) -> dict:
    """Process input data.

    Args:
        data: Input data dictionary

    Returns:
        Processed data dictionary
    """
    # TODO: Implement data processing
    return {{"status": "processed", "input": data}}
'''

    def _test_cli_py(self, slug: str) -> str:
        return f'''"""
CLI Tests

Tests for the command-line interface.
"""

from click.testing import CliRunner

from {slug}.cli import cli


def test_version():
    """Test version option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_hello():
    """Test hello command with default name."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output


def test_hello_with_name():
    """Test hello command with custom name."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hello", "Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output


def test_status():
    """Test status command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0


def test_status_verbose():
    """Test status command with verbose flag."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--verbose"])
    assert result.exit_code == 0
    assert "operational" in result.output
'''

    def _pyproject_toml(self, name: str, slug: str, desc: str, spec: "ProjectSpec") -> str:
        deps = self.get_dependencies(spec)
        dev_deps = self.get_dev_dependencies(spec)

        deps_str = ",\n    ".join(f'"{d}"' for d in deps)
        dev_deps_str = ",\n    ".join(f'"{d}"' for d in dev_deps)

        return f'''[project]
name = "{name}"
version = "0.1.0"
description = "{desc}"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    {deps_str},
]

[project.optional-dependencies]
dev = [
    {dev_deps_str},
]

[project.scripts]
{name} = "{slug}.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{slug}"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
'''

    def _readme_md(self, name: str, slug: str, desc: str) -> str:
        return f'''# {name}

{desc}

## Installation

```bash
# From source (development)
pip install -e ".[dev]"

# Or using uv
uv pip install -e ".[dev]"
```

## Usage

```bash
# Show help
{name} --help

# Say hello
{name} hello
{name} hello Alice

# Show status
{name} status
{name} status --verbose
```

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov={slug}

# Lint
ruff check src tests
```

## License

MIT
'''
