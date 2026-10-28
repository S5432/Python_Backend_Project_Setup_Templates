# 1. Phase 1 Implementation — ShvetVarni FastAPI Template

I reviewed the code you shared. You have already completed the initial project structure, created the settings module, configured the asynchronous SQLAlchemy engine, and confirmed that the FastAPI liveness endpoint works.

We will continue from your existing code rather than rebuild the project. Our next goal is to complete Phase 1 and prove that the database and migration workflow work correctly.

Your project location is:

```
D:\Company_Development_Resource\Coding Related Resource\
Python_Backend_Project_Setup_Templates\fastapi_temp_v1
```

## 1.1 What is already implemented?

| Component             | Current status                               | Next action                                                               |
| --------------------- | -------------------------------------------- | ------------------------------------------------------------------------- |
| `app/core/config.py`  | Implemented                                  | Add production-safe validation and improve configuration handling         |
| `app/db/session.py`   | Async engine and session factory implemented | Verify connectivity, transactions, and session cleanup                    |
| `app/main.py`         | FastAPI and liveness endpoint work           | Add database readiness and organized routing                              |
| `requirements.txt`    | Dependencies are pinned                      | Check installed versions and establish reproducible dependency management |
| PostgreSQL connection | Not demonstrated by the supplied code        | Execute a real asynchronous database query                                |
| `app/db/base.py`      | Not shared                                   | Create the declarative base and metadata                                  |
| Alembic configuration | Not shared                                   | Configure async migrations and environment settings                       |
| Initial migration     | Not demonstrated                             | Generate and apply a migration                                            |
| Automated tests       | Not shared                                   | Add tests for the API and database connectivity                           |

The important distinction: a successful liveness endpoint proves that FastAPI is running. It does not prove that PostgreSQL is reachable, the credentials are valid, or migrations can run.

Our Phase 1 completion criteria are therefore:

1. FastAPI starts successfully.
2. PostgreSQL connectivity is verified through an actual query.
3. SQLAlchemy uses asynchronous sessions throughout the request lifecycle.
4. Alembic can discover the application's model metadata.
5. The initial migration runs against PostgreSQL.
6. A fresh developer can reproduce the setup.

# 2. Step 1 — Refine the project configuration

Before we add database migrations, I recommend two improvements.

1. Keep the current settings and async engine approach. They are appropriate for this architecture.
2. Avoid duplicating the API prefix and database configuration across files. We will use the settings module as the source of configuration.

The official SQLAlchemy documentation confirms that `AsyncSession` is designed for async database work and that each concurrent task should have its own session. Alembic also officially supports asynchronous migration environments through its `async` template.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation+1



## 2.1 Update `app/core/config.py`

Replace your current settings file with this version:

```

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShvetVarni FastAPI Template"

    app_env: Literal[
        "development",
        "test",
        "staging",
        "production",
    ] = "development"

    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: SecretStr

    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: int = Field(default=30, ge=1)

    cors_origins: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

```

This remains intentionally simple. We will add stronger production validation when implementing Phase 6.

## 2.2 Verify `.env`

For local PostgreSQL, use a dedicated database for this template rather than connecting to an unrelated application database.

Example `.env`:

```
APP_NAME=ShvetVarni FastAPI Template
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/shvetvarni_template

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

Replace `YOUR_PASSWORD` with your actual PostgreSQL password. If the password contains characters such as `@`, `/`, or `#`, encode them appropriately in the URL.

Pydantic Settings reads environment variables and `.env` files and validates their values against the declared field types.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Do not paste your real database password into this conversation.

# 3. Step 2 — Implement the SQLAlchemy async database layer

Your current `session.py` is already close to the desired design. We will retain its main approach and make the lifecycle and typing explicit.

## 3.1 Create `app/db/base.py`

```

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": (
        "fk_%(table_name)s_%(column_0_name)s_"
        "%(referred_table_name)s"
    ),
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention=NAMING_CONVENTION,
    )

```

Why use a naming convention? It gives database constraints and indexes predictable names. This makes Alembic migrations easier to review and maintain.

All future SQLAlchemy models must inherit from this `Base`. We will use UUID primary keys for application entities in Phase 2.

## 3.2 Update `app/db/session.py`

```

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


settings = get_settings()

engine = create_async_engine(
    settings.database_url.get_secret_value(),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session

```

This is a suitable Phase 1 database session implementation.

Keep the following rules as we build the rest of the application:

- All database operations in async routes and services use `await`.
- Every concurrent request or independent task gets its own `AsyncSession`.
- Do not share an `AsyncSession` between concurrent tasks.
- Repositories execute queries; services own business transactions.
- The session dependency closes the session when the request finishes.
- The application lifespan disposes the engine when the application shuts down.

These rules follow SQLAlchemy's documented async session model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation+1



## 3.3 Create `app/dependencies/database.py`

Because your final folder structure includes `dependencies/database.py`, we should expose the database dependency from that location.

```

from app.db.session import get_db_session

__all__ = ["get_db_session"]

```

This re-export keeps database dependencies organized. Route modules will import from `app.dependencies.database`, while the underlying session implementation stays in `app.db.session`.

## 3.4 Create `app/db/models/__init__.py`

For Phase 1, no business tables are required yet. Use:

```

# Import ORM models here as they are added.
# This package will expose the models needed by Alembic.

```

When we implement the user module, we will import `User` here. Alembic needs those model classes to be imported before it inspects `Base.metadata`.

# 4. Step 3 — Implement health and database readiness endpoints

We will separate two concepts:

- Liveness: Is the FastAPI process responding?
- Readiness: Can the application execute a database query successfully?

A process can be alive while PostgreSQL is unavailable. The readiness endpoint makes that difference visible.

## 4.1 Create `app/api/routes/health.py`

```

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db_session


router = APIRouter(tags=["Health"])

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check(
    session: DatabaseSession,
) -> dict[str, str]:
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar_one()

    except SQLAlchemyError as exc:
        # Keep database details out of the public response.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from exc

    return {
        "status": "ready",
        "database": "connected",
    }

```

The query `SELECT 1` verifies that a database connection can execute a statement without requiring any application tables.

The exception handler intentionally returns a generic message. In Phase 6, we will add structured logging and a centralized exception handler so database failures can be diagnosed securely.

## 4.2 Create `app/api/router.py`

```

from fastapi import APIRouter

from app.api.routes import health


api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
)

```

## 4.3 Update `app/main.py`

```

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import engine


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    @application.get("/", tags=["Health"])
    async def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "status": "running",
        }

    return application


app = create_app()

```

This introduces a small application factory, `create_app()`, which makes testing and future application customization easier. The lifespan also ensures that the async engine is disposed of during shutdown.

Your endpoints will now be:

| Endpoint                   | Expected result             |
| -------------------------- | --------------------------- |
| `GET /`                    | API process information     |
| `GET /api/v1/health/live`  | Liveness response           |
| `GET /api/v1/health/ready` | Database readiness response |
| `/docs`                    | Swagger UI                  |

Do not proceed to migrations until these files have been saved and the application starts successfully.

# 5. Step 4 — Configure Alembic for async PostgreSQL

This is the most important remaining part of Phase 1. We need to ensure Alembic uses the same database configuration as the application and sees the same SQLAlchemy metadata.

Official Alembic documentation recommends the async migration template for applications using asynchronous database drivers such as `asyncpg`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation+1



## 5.1 Check whether Alembic is already initialized

From the project root, run:

```
Test-Path .\alembic\env.py
Test-Path .\alembic\script.py.mako
Test-Path .\alembic.ini
```

If `env.py`, `script.py.mako`, and `alembic.ini` already exist, do not initialize Alembic again. We will update the existing files.

If they do not exist, initialize Alembic once:

```
python -m alembic init -t async alembic
```

This generates the migration environment and configuration files.

## 5.2 Update `alembic/env.py`

Replace the generated `alembic/env.py` with this implementation:

```

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

# Alembic's ConfigParser requires percent signs in URLs
# to be escaped before storing them in configuration.
database_url = settings.database_url.get_secret_value()
config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

```

### Why these details matter

- `target_metadata = Base.metadata` makes Alembic compare the application's ORM metadata against the database schema.
- Importing `app.db.models` ensures that models registered with that package become visible to Alembic.
- `async_engine_from_config()` provides an asynchronous migration engine.
- `connection.run_sync()` allows Alembic's migration context to use SQLAlchemy's synchronous-style migration API over the async connection.
- `compare_type=True` enables detection of column type changes during autogeneration.
- `NullPool` avoids maintaining a persistent connection pool for short-lived migration commands.

Alembic is not a separate async migration API; it uses SQLAlchemy's async connection support to run the migration machinery.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation+1



## 5.3 Check `alembic.ini`

Ensure the existing `alembic.ini` contains these essential settings:

```
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://placeholder:placeholder@localhost/placeholder
```

Keep any other settings generated by Alembic. The URL above is only a placeholder: `env.py` replaces it with the value from `DATABASE_URL` before running migrations.

Never place your real production database credentials in `alembic.ini`.

## 5.4 Confirm model metadata is importable

Your `app/db/base.py` must define the shared declarative base, and your `app/db/models/__init__.py` must import every ORM model as we add them.

At the end of Phase 1, there are no application tables yet. The first baseline migration will verify the migration workflow. Phase 2 will introduce the user table and generate a new migration for it.

# 6. Step 5 — Create and verify the PostgreSQL database

We will test locally first, following the approach you have used for your previous backend work, and introduce Docker once the local database and migrations are verified.

## 6.1 Create the database

If PostgreSQL is already installed and running on Windows, open PowerShell and run:

```
psql -U postgres -h localhost -p 5432 -d postgres
```

Enter your PostgreSQL password when prompted. Then execute:

```
CREATE DATABASE shvetvarni_template;
```

Exit the PostgreSQL shell:

```
\q
```

If the database already exists, do not create it again. You can verify it with:

```
psql -U postgres -h localhost -p 5432 -d shvetvarni_template -c "SELECT current_database();"
```

If `psql` is not recognized, use pgAdmin's Query Tool to create the database or run the command from your PostgreSQL installation's `bin` directory.

The database name in this command must match the database name in `.env`.

## 6.2 Test the API's database connection

Start the application:

```
python -m uvicorn app.main:app --reload
```

Open:

`http://127.0.0.1:8000/api/v1/health/ready`

Expected response:

```
{
  "status": "ready",
  "database": "connected"
}
```

If PostgreSQL is unavailable or the credentials are incorrect, the endpoint should return HTTP `503 Service Unavailable`.

This is the first meaningful verification of your async database configuration.

## 6.3 Troubleshooting common connection errors

| Error                                       | Likely cause                                              | What to check                                           |
| ------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------- |
| Connection refused                          | PostgreSQL is stopped or listening elsewhere              | PostgreSQL service and port `5432`                      |
| Password authentication failed              | Incorrect username or password                            | `.env` and PostgreSQL credentials                       |
| Database does not exist                     | Database name mismatch                                    | Database creation and `DATABASE_URL`                    |
| Missing `asyncpg`                           | Driver is not installed in the active environment         | `python -m pip show asyncpg`                            |
| Missing greenlet / SQLAlchemy async support | Incomplete or incompatible dependency installation        | `python -m pip check` and SQLAlchemy async dependencies |
| Settings validation error                   | `DATABASE_URL` is missing or invalid                      | `.env` location and field values                        |
| Alembic cannot import `app`                 | Command run from the wrong directory or import path issue | Run commands from the project root                      |

Do not work around connection errors by switching to a synchronous PostgreSQL driver. We are deliberately keeping the application asynchronous from the start.

# 7. Step 6 — Run the initial Alembic migration

Once the database connection works, run these commands from the project root.

## 7.1 Confirm Alembic recognizes the configuration

```
python -m alembic history
python -m alembic heads
```

These commands inspect the migration history and current migration head. If the repository has no revisions yet, an empty history is expected.

## 7.2 Create the baseline revision

Because we have not added any business models in Phase 1, create an intentionally empty baseline migration:

```
python -m alembic revision -m "initial schema baseline"
```

Open the generated Python file in `alembic/versions/`. It should contain an `upgrade()` and a `downgrade()` function.

At this stage, both can be empty:

```
def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

Keep the generated revision ID, `down_revision`, imports, and other Alembic metadata intact.

This baseline records the initial schema version; it does not create application tables. That is intentional. The user table will be introduced in Phase 2 through a real schema migration.

## 7.3 Apply the migration

```
python -m alembic upgrade head
```

Then verify the migration state:

```
python -m alembic current
python -m alembic heads
python -m alembic check
```

Expected results:

- `upgrade head` completes without errors.
- `current` reports the applied revision.
- `heads` reports the same revision.
- `check` reports that no new upgrade operations are detected.

Alembic creates its own `alembic_version` table to record the applied revision.

Do not manually create application tables or use `Base.metadata.create_all()` as a replacement for migrations. We want one controlled schema-management process across local development, testing, and deployment.

## 7.4 Verify the database directly

Run:

```
psql -U postgres -h localhost -p 5432 -d shvetvarni_template -c "SELECT version_num FROM alembic_version;"
```

The output should contain the revision ID of your baseline migration.

At this point, the API, PostgreSQL connection, async SQLAlchemy setup, and migration tracking have been verified separately.

# 8. Step 7 — Add Phase 1 automated tests

The final verification should include tests, not just manual browser checks.

## 8.1 Create `requirements-dev.txt`

Keep your existing `requirements.txt` for the runtime dependencies. Create a separate development dependency file:

```
-r requirements.txt
pytest
httpx
```

Install the development dependencies:

```
python -m pip install -r requirements-dev.txt
```

Your existing runtime requirements are pinned, which is useful for reproducibility. Later, we should distinguish direct dependencies from transitive dependencies and establish a tested lockfile workflow.

## 8.2 Create `tests/api/test_health.py`

```
from fastapi.testclient import TestClient

from app.main import app


def test_liveness_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_database_readiness_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }
```

These are integration-oriented smoke tests: the readiness test requires a running PostgreSQL instance with valid credentials.

Run the tests:

```
python -m pytest tests/api/test_health.py -v
```

Expected result: both tests pass.

If the readiness test fails, diagnose the database connection rather than weakening the test.

# 9. Final Phase 1 verification

Use this sequence from the project root:

```
# 1. Verify dependencies
python -m pip check

# 2. Inspect migration history
python -m alembic history

# 3. Apply migrations
python -m alembic upgrade head

# 4. Verify migration state
python -m alembic current
python -m alembic check

# 5. Run automated tests
python -m pytest tests/api/test_health.py -v

# 6. Start the API
python -m uvicorn app.main:app --reload
```

Then verify these endpoints:

| URL                                         | Expected result                       |
| ------------------------------------------- | ------------------------------------- |
| `http://127.0.0.1:8000/`                    | HTTP 200                              |
| `http://127.0.0.1:8000/api/v1/health/live`  | HTTP 200                              |
| `http://127.0.0.1:8000/api/v1/health/ready` | HTTP 200 when PostgreSQL is available |
| `http://127.0.0.1:8000/docs`                | Swagger UI loads                      |

## 9.1 Phase 1 acceptance checklist

## Phase 1 completion

0/9 verified

Settings load successfully from .env.

FastAPI starts and the liveness endpoint responds.

Async SQLAlchemy connects to PostgreSQL using SELECT 1.

Each request receives its own async database session.

Alembic uses the application's Base.metadata.

The initial migration upgrades successfully.

alembic current and heads show the expected revision.

alembic check reports no pending schema changes.

Both automated health tests pass.

Copy verification report

Only mark a criterion complete after you have run the relevant command or test and verified its output.

# 10. What comes next?

After Phase 1 passes, we will start Phase 2 — User Module.

The next implementation will include:

1. A SQLAlchemy `User` model with a UUID primary key.
2. Normalized, unique email addresses enforced by PostgreSQL.
3. Password-hash storage without exposing hashes in responses.
4. Pydantic request and response schemas.
5. An asynchronous user repository and service.
6. Registration and current-user profile endpoints.
7. An Alembic migration that creates the user table.
8. Tests for duplicate registration, invalid inputs, and sensitive-field exposure.

We will not start JWT authentication until the user module and its migration are verified.

Your immediate next action: execute the Phase 1 steps in order. If any command fails, share the complete error message and the relevant file. We will correct that specific issue and verify it before moving forward.