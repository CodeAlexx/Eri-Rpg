"""
FastAPI-only template for backend API projects.

Creates a standard FastAPI project structure:
    {project}/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py           # FastAPI entry
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── routes.py     # API routes stub
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── schemas.py    # Pydantic models stub
    │   └── core/
    │       ├── __init__.py
    │       └── config.py     # Settings
    ├── tests/
    │   ├── __init__.py
    │   └── test_api.py
    ├── requirements.txt
    └── README.md
"""

from typing import TYPE_CHECKING, List

from erirpg.templates.base import BaseTemplate, ScaffoldFile

if TYPE_CHECKING:
    from erirpg.specs import ProjectSpec


class FastAPIOnlyTemplate(BaseTemplate):
    """FastAPI backend template."""

    @property
    def name(self) -> str:
        return "fastapi-only"

    @property
    def description(self) -> str:
        return "FastAPI backend with standard Python structure"

    @property
    def languages(self) -> List[str]:
        return ["python"]

    @property
    def default_framework(self) -> str:
        return "fastapi"

    def get_directories(self, spec: "ProjectSpec") -> List[str]:
        return [
            "app",
            "app/api",
            "app/models",
            "app/core",
            "tests",
        ]

    def get_dependencies(self, spec: "ProjectSpec") -> List[str]:
        return [
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "pydantic>=2.0.0",
            "pydantic-settings>=2.0.0",
        ]

    def get_dev_dependencies(self, spec: "ProjectSpec") -> List[str]:
        return [
            "pytest>=8.0.0",
            "httpx>=0.27.0",  # For TestClient
            "ruff>=0.3.0",
        ]

    def get_files(self, spec: "ProjectSpec") -> List[ScaffoldFile]:
        name = spec.name
        slug = self._slugify(name)
        desc = self._format_description(spec)

        return [
            # Main entry point
            ScaffoldFile(
                path="app/__init__.py",
                content=f'"""App package for {name}."""\n',
                phase="001",
                description="App package init",
            ),
            ScaffoldFile(
                path="app/main.py",
                content=self._main_py(name, desc),
                phase="001",
                description="FastAPI application entry point",
            ),

            # API routes
            ScaffoldFile(
                path="app/api/__init__.py",
                content='"""API routes package."""\n',
                phase="001",
            ),
            ScaffoldFile(
                path="app/api/routes.py",
                content=self._routes_py(desc),
                phase="001",
                description="API routes stub",
            ),

            # Models/schemas
            ScaffoldFile(
                path="app/models/__init__.py",
                content='"""Pydantic models package."""\n',
                phase="001",
            ),
            ScaffoldFile(
                path="app/models/schemas.py",
                content=self._schemas_py(desc),
                phase="001",
                description="Pydantic schemas stub",
            ),

            # Core/config
            ScaffoldFile(
                path="app/core/__init__.py",
                content='"""Core utilities package."""\n',
                phase="001",
            ),
            ScaffoldFile(
                path="app/core/config.py",
                content=self._config_py(name),
                phase="001",
                description="Application settings",
            ),

            # Tests
            ScaffoldFile(
                path="tests/__init__.py",
                content='"""Test package."""\n',
                phase="001",
            ),
            ScaffoldFile(
                path="tests/test_api.py",
                content=self._test_api_py(),
                phase="001",
                description="API tests",
            ),

            # Project files
            ScaffoldFile(
                path="requirements.txt",
                content=self._requirements_txt(spec),
                phase="001",
                description="Python dependencies",
            ),
            ScaffoldFile(
                path="README.md",
                content=self._readme_md(name, desc),
                phase="001",
                description="Project README",
            ),
        ]

    def _main_py(self, name: str, desc: str) -> str:
        return f'''"""
{name} - FastAPI Application

{desc}
"""

from fastapi import FastAPI

from app.api import routes
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="{desc}",
    version="0.1.0",
)

# Include API routes
app.include_router(routes.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {{"status": "ok", "app": settings.app_name}}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "healthy"}}
'''

    def _routes_py(self, desc: str) -> str:
        return f'''"""
API Routes

Main API endpoints for the application.
{desc}
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ItemCreate, ItemResponse

router = APIRouter()


@router.get("/items", response_model=list[ItemResponse])
async def list_items():
    """List all items."""
    # TODO: Implement item listing
    return []


@router.get("/items/{{item_id}}", response_model=ItemResponse)
async def get_item(item_id: int):
    """Get a specific item by ID."""
    # TODO: Implement item retrieval
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate):
    """Create a new item."""
    # TODO: Implement item creation
    return ItemResponse(id=1, **item.model_dump())
'''

    def _schemas_py(self, desc: str) -> str:
        return f'''"""
Pydantic Schemas

Request/response models for the API.
{desc}
"""

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """Base item schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ItemCreate(ItemBase):
    """Schema for creating items."""
    pass


class ItemResponse(ItemBase):
    """Schema for item responses."""
    id: int

    model_config = {{"from_attributes": True}}
'''

    def _config_py(self, name: str) -> str:
        slug = self._slugify(name).upper()
        return f'''"""
Application Configuration

Settings loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "{name}"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database (optional)
    database_url: str | None = None

    # Security (optional)
    secret_key: str = "dev-secret-change-in-production"

    model_config = SettingsConfigDict(
        env_prefix="{slug}_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
'''

    def _test_api_py(self) -> str:
        return '''"""
API Tests

Basic tests for the API endpoints.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint returns healthy status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_items():
    """Test listing items returns empty list initially."""
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert response.json() == []
'''

    def _requirements_txt(self, spec: "ProjectSpec") -> str:
        deps = self.get_dependencies(spec)
        dev_deps = self.get_dev_dependencies(spec)
        lines = ["# Production dependencies"]
        lines.extend(deps)
        lines.append("")
        lines.append("# Development dependencies")
        lines.extend(dev_deps)
        return "\n".join(lines) + "\n"

    def _readme_md(self, name: str, desc: str) -> str:
        return f'''# {name}

{desc}

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Development server
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
pytest
```
'''
