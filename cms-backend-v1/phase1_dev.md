# Phase 1 — CMS Backend Setup with Asynchronous Database Access

We will build your Content Management System (CMS) using FastAPI + PostgreSQL + SQLAlchemy 2.x async + Alembic + asyncpg from the very beginning.

Your decision to introduce asynchronous database access in Phase 1 is sensible. It means we can establish the correct database architecture now instead of converting synchronous sessions, database dependencies, and query code later.

One important point: async does not automatically make every database query faster. Its main benefit is that FastAPI can handle other work while an asynchronous database operation is waiting for a response, which can improve concurrency for I/O-heavy applications.

## 1. Final technology stack

| Technology                    | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| Python 3.12+                  | Backend programming                       |
| FastAPI                       | API framework                             |
| Uvicorn                       | ASGI development server                   |
| PostgreSQL                    | Relational database                       |
| SQLAlchemy 2.x async          | ORM and asynchronous database access      |
| `asyncpg`                     | Asynchronous PostgreSQL driver            |
| Alembic                       | Database migrations                       |
| `pydantic-settings`           | Environment configuration                 |
| `python-dotenv`               | Environment file support through settings |
| `pytest` and `pytest-asyncio` | Future automated testing                  |

We will use Python 3.12 or another supported Python version compatible with your dependencies. We will use `create_async_engine`, `async_sessionmaker`, `AsyncSession`, and asynchronous SQLAlchemy queries.

## 2. Architecture we will implement

Client

Browser / Postman / frontend

FastAPI + Uvicorn

Async API endpoints

AsyncSession + SQLAlchemy ORM

Async database dependencies and queries

asyncpg driver

PostgreSQL

Alembic runs schema migrations separately using the same async database configuration.

The key design decision is to use one asynchronous database pattern throughout the application, including the health check, database dependency, ORM models, and migration configuration.

## 3. Create the project and install dependencies

### Step 3.1 — Create the project

Open Windows PowerShell:

```
mkdir cms-backend
cd cms-backend

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If Python 3.12 is not installed, check your installed versions with `py --list` and use a supported version instead.

### Step 3.2 — Install the packages

```
python -m pip install --upgrade pip

pip install "fastapi[standard]" "sqlalchemy[asyncio]>=2.0,<3.0" "alembic>=1.13" "asyncpg>=0.30" "pydantic-settings>=2.0"
```

The `sqlalchemy[asyncio]` extra ensures the dependencies needed for SQLAlchemy's asyncio support are installed. SQLAlchemy's official documentation describes the async engine, session factory, and async PostgreSQL driver setup.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.0 Documentation+2



Save the dependencies:

```
pip freeze > requirements.txt
```

Verify the installation:

```
python -c "import fastapi, sqlalchemy, asyncpg, alembic, pydantic_settings; print('All dependencies imported successfully')"
```

## 4. Create the project structure

Use this structure for Phase 1:

```
cms-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   └── models/
│       ├── __init__.py
│       └── content.py
├── alembic/
│   ├── versions/
│   └── env.py
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
└── requirements.txt
```

Create the folders and Python package files:

```
mkdir app, app\api, app\db, app\models

New-Item app\__init__.py
New-Item app\api\__init__.py
New-Item app\db\__init__.py
New-Item app\models\__init__.py
```

## 5. Configure environment variables

Create `.env` in the project root:

```
APP_NAME=CMS Backend
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://cms_user:YOUR_PASSWORD@localhost:5432/cms_db
```

Replace `YOUR_PASSWORD` with your actual PostgreSQL password.

Create `.env.example`:

```
APP_NAME=CMS Backend
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://cms_user:YOUR_PASSWORD@localhost:5432/cms_db
```

Create `.gitignore`:

```
.venv/
__pycache__/
*.py[cod]
.env
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
```

### Create `app/config.py`

```
from functools import lru_cachefrom pydantic_settings import BaseSettings, SettingsConfigDictclass Settings(BaseSettings):    app_name: str = "CMS Backend"    app_env: str = "development"    database_url: str    model_config = SettingsConfigDict(        env_file=".env",        env_file_encoding="utf-8",        case_sensitive=False,        extra="ignore",    )@lru_cachedef get_settings() -> Settings:    return Settings()settings = get_settings()
```

Important: `postgresql+asyncpg://` is intentional. It tells SQLAlchemy to use the asynchronous PostgreSQL driver. If you accidentally use `postgresql://` or `postgresql+psycopg://` here, you will not be using the asyncpg connection path we want for the application.

For passwords containing special characters such as `@`, `/`, or `:`, encode them appropriately in the URL or construct the SQLAlchemy URL programmatically.

## 6. Set up PostgreSQL

You can use your existing local PostgreSQL installation or run PostgreSQL in Docker. The application code is the same either way.

If PostgreSQL is installed locally, connect as an administrator using `psql` or pgAdmin and create a dedicated database user and database:

```
CREATE USER cms_user WITH PASSWORD 'YOUR_STRONG_PASSWORD';

CREATE DATABASE cms_db OWNER cms_user;
```

Replace the example password with a strong password, and use the same password in `.env`.

Test the connection:

```
psql -h localhost -U cms_user -d cms_db
```

Then run:

```
SELECT version();
```

Exit with:

```
\q
```

If `psql` is not available in your terminal, use pgAdmin's Query Tool or configure the PostgreSQL `bin` directory in your PATH.

## 7. Implement the asynchronous SQLAlchemy database layer

This is the most important part of your requested change.

### Step 7.1 — Create `app/db/base.py`

```
from sqlalchemy.orm import DeclarativeBaseclass Base(DeclarativeBase):    pass
```

All ORM models will inherit from `Base`. Alembic will use `Base.metadata` to discover the tables for autogenerated migrations.

### Step 7.2 — Create `app/db/session.py`

```
from collections.abc import AsyncGeneratorfrom sqlalchemy.ext.asyncio import (    AsyncSession,    async_sessionmaker,    create_async_engine,)from app.config import settingsengine = create_async_engine(    settings.database_url,    pool_pre_ping=True,)AsyncSessionLocal = async_sessionmaker(    bind=engine,    class_=AsyncSession,    autoflush=False,    expire_on_commit=False,)async def get_db() -> AsyncGenerator[AsyncSession, None]:    async with AsyncSessionLocal() as session:        yield session
```

Understand these components:

- `create_async_engine()` creates the asynchronous database engine.
- `async_sessionmaker()` creates a reusable factory for database sessions.
- `AsyncSession` provides asynchronous SQLAlchemy operations.
- `async with` ensures that the session is closed after use.
- `expire_on_commit=False` lets you access already-loaded ORM attributes after committing without automatically expiring them.

SQLAlchemy recommends passing `AsyncSession` explicitly to the functions that need it. An `AsyncSession` is mutable and should not be shared across concurrent tasks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.0 Documentation+1



A rule for all future phases: database I/O must use `await` where the SQLAlchemy API requires it. Never run blocking synchronous SQLAlchemy queries inside your async route handlers.

### Step 7.3 — Create `app/models/content.py`

We will create one minimal table to prove the migration process works.

```
from datetime import datetimefrom sqlalchemy import DateTime, String, Text, funcfrom sqlalchemy.orm import Mapped, mapped_columnfrom app.db.base import Baseclass Content(Base):    __tablename__ = "contents"    id: Mapped[int] = mapped_column(        primary_key=True,        index=True,    )    title: Mapped[str] = mapped_column(        String(200),        nullable=False,    )    body: Mapped[str] = mapped_column(        Text,        nullable=False,        default="",    )    created_at: Mapped[datetime] = mapped_column(        DateTime(timezone=True),        server_default=func.now(),        nullable=False,    )
```

Create `app/models/__init__.py`:

```
from app.models.content import Content__all__ = ["Content"]
```

The model describes the database table, but it does not create the table by itself. We will use Alembic to generate and apply the schema migration.

## 8. Configure Alembic for asynchronous PostgreSQL

Alembic's migration operations use a synchronous migration API internally, but it can run migrations through SQLAlchemy's async engine using `run_sync()`. The official Alembic documentation supports an `async` environment template for this purpose.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation+1



### Step 8.1 — Initialize the asynchronous Alembic template

Run this from the project root:

```
alembic init -t async alembic
```

Use `-t async` rather than the default template. It generates an Alembic environment designed for an asynchronous database driver.

### Step 8.2 — Update `alembic.ini`

Find the generated line beginning with `sqlalchemy.url` and replace the example URL with an empty value:

```
sqlalchemy.url =
```

The actual URL will be supplied from `.env`, so you do not need to duplicate credentials in this file.

### Step 8.3 — Replace `alembic/env.py`

Use the following complete version:

```
import asynciofrom logging.config import fileConfigfrom alembic import contextfrom sqlalchemy import poolfrom sqlalchemy.engine import Connectionfrom sqlalchemy.ext.asyncio import async_engine_from_configfrom app.config import settingsfrom app.db.base import Basefrom app.models import Content  # noqa: F401config = context.configif config.config_file_name is not None:    fileConfig(config.config_file_name)config.set_main_option(    "sqlalchemy.url",    settings.database_url.replace("%", "%%"),)target_metadata = Base.metadatadef run_migrations_offline() -> None:    url = config.get_main_option("sqlalchemy.url")    context.configure(        url=url,        target_metadata=target_metadata,        literal_binds=True,        dialect_opts={"paramstyle": "named"},        compare_type=True,    )    with context.begin_transaction():        context.run_migrations()def do_run_migrations(connection: Connection) -> None:    context.configure(        connection=connection,        target_metadata=target_metadata,        compare_type=True,    )    with context.begin_transaction():        context.run_migrations()async def run_async_migrations() -> None:    connectable = async_engine_from_config(        config.get_section(config.config_ini_section, {}),        prefix="sqlalchemy.",        poolclass=pool.NullPool,    )    try:        async with connectable.connect() as connection:
```

### How this works

1. `async_engine_from_config()` builds an async SQLAlchemy engine using the database URL.
2. `async with connectable.connect()` opens an asynchronous database connection.
3. `await connection.run_sync(do_run_migrations)` adapts that connection for Alembic's migration operations.
4. `await connectable.dispose()` releases the engine's resources after the migration run.

This is the migration path we want from Phase 1 onward.

## 9. Generate and apply the first migration

### Step 9.1 — Generate the migration

```
alembic revision --autogenerate -m "create contents table"
```

Alembic should create a new file inside `alembic/versions/`.

Open that file and inspect the generated `upgrade()` and `downgrade()` functions. Confirm that `upgrade()` creates `contents` and `downgrade()` removes it.

### Step 9.2 — Apply the migration

```
alembic upgrade head
```

### Step 9.3 — Verify the migration

```
alembic current
alembic history
alembic check
```

You should see the current revision, the migration history, and no pending autogenerated schema changes.

Verify the table directly in PostgreSQL:

```
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'contents';
```

The result should include `contents`.

Important: review every autogenerated migration before applying it. Do not replace Alembic with `Base.metadata.create_all()` or routinely delete migration history to resolve errors.

## 10. Create the asynchronous FastAPI endpoints

### Step 10.1 — Create `app/api/health.py`

```
from fastapi import APIRouter, Depends, HTTPExceptionfrom sqlalchemy import textfrom sqlalchemy.exc import SQLAlchemyErrorfrom sqlalchemy.ext.asyncio import AsyncSessionfrom app.db.session import get_dbrouter = APIRouter(tags=["Health"])@router.get("/health")async def health_check():    return {        "status": "healthy",        "service": "cms-backend",    }@router.get("/health/database")async def database_health_check(    db: AsyncSession = Depends(get_db),):    try:        await db.execute(text("SELECT 1"))        return {            "status": "healthy",            "database": "connected",        }    except SQLAlchemyError as exc:        raise HTTPException(            status_code=503,            detail="Database connection failed",        ) from exc
```

Notice the difference from synchronous database code:

```
# Synchronous — not our chosen approachdb.execute(text("SELECT 1"))# Asynchronous — our approachawait db.execute(text("SELECT 1"))
```

Database operations that perform I/O must be awaited. The route functions are also declared with `async def`.

### Step 10.2 — Create `app/main.py`

```
from contextlib import asynccontextmanagerfrom fastapi import FastAPIfrom app.api.health import router as health_routerfrom app.config import settingsfrom app.db.session import engine@asynccontextmanagerasync def lifespan(app: FastAPI):    yield    await engine.dispose()app = FastAPI(    title=settings.app_name,    version="0.1.0",    description="Backend API for a Content Management System",    lifespan=lifespan,)app.include_router(health_router, prefix="/api/v1")@app.get("/")async def root():    return {        "message": "Welcome to the CMS Backend API",        "docs": "/docs",    }
```

The lifespan handler disposes of the asynchronous engine when the application shuts down. It does not create database tables; migrations remain a separate operation.

Your application now has these endpoints:

| Method | Endpoint                  | Purpose                       |
| ------ | ------------------------- | ----------------------------- |
| GET    | `/`                       | Application welcome response  |
| GET    | `/api/v1/health`          | API health check              |
| GET    | `/api/v1/health/database` | Async PostgreSQL query        |
| GET    | `/docs`                   | Interactive API documentation |

## 11. Run the application and verify Phase 1

### Step 11.1 — Start FastAPI

Run this command from the project root:

```
uvicorn app.main:app --reload
```

Notice that we use `app.main:app`, not `main:app`, because our application entry point is now inside the `app/` package.

### Step 11.2 — Test these endpoints

1\. Application root

`http://127.0.0.1:8000/`

Expected response:

```
{
  "message": "Welcome to the CMS Backend API",
  "docs": "/docs"
}
```

2\. API health

`http://127.0.0.1:8000/api/v1/health`

Expected: `"status": "healthy"`.

3\. Async database health

`http://127.0.0.1:8000/api/v1/health/database`

Expected: `"database": "connected"`.

4\. Swagger documentation

`http://127.0.0.1:8000/docs`

Expected: interactive documentation listing the API endpoints.

### Step 11.3 — Verify migrations again

Stop the development server if necessary, then run:

```
alembic current
alembic check
```

Your initial database migration should already be applied, and Alembic should not detect any additional autogenerated schema changes.

### Step 11.4 — Verify the installed async stack

Run:

```
python -c "from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession; from app.db.session import engine; print('Async engine:', isinstance(engine, AsyncEngine)); print('Driver:', engine.url.drivername)"
```

Expected output:

```
Async engine: True
Driver: postgresql+asyncpg
```

This verifies that the application is using the asynchronous SQLAlchemy engine and the intended PostgreSQL driver.

## 12. Troubleshooting the most likely errors

| Error                                       | Solution                                                                                                                   |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError`                       | Activate `.venv` and install dependencies.                                                                                 |
| `connection refused`                        | Start PostgreSQL and verify host and port.                                                                                 |
| `password authentication failed`            | Check the credentials in `.env`.                                                                                           |
| `NoSuchModuleError` or missing async driver | Install `asyncpg` and verify the URL uses `postgresql+asyncpg://`.                                                         |
| `Target database is not up to date`         | Inspect `alembic current` and `alembic history`.                                                                           |
| Autogenerate detects no tables              | Ensure `Content` is imported into `app/models/__init__.py` and `alembic/env.py`.                                           |
| `asyncio.run()` error in migration          | Run Alembic as a normal terminal command rather than calling the migration entry point from an already-running event loop. |

If your PostgreSQL password contains URL-reserved characters, encode them correctly. For production applications, also review connection-pool sizing, database credentials, TLS requirements, and migration deployment procedures.

## 13. Phase 1 completion checklist

## Phase 1 verification

0 of 10

FastAPI project and virtual environment created

Dependencies installed and requirements.txt saved

Environment configuration and .gitignore created

PostgreSQL database and user configured

SQLAlchemy async engine and AsyncSession implemented

Content ORM model created

Alembic async environment configured

Initial migration generated and applied

API health and database health endpoints tested

alembic check completed successfully

## 14. What comes next?

Once Phase 1 works, we can progress to Phase 2: CMS domain design and database modeling.

That phase should establish the real CMS entities and relationships before implementing the CRUD endpoints. Likely entities include:

- Users and authors
- Content and drafts
- Categories and tags
- Publishing status and timestamps

We should define these carefully before generating their migrations, rather than adding unnecessary tables now.

Your immediate assignment: implement Phase 1, run the database health endpoint, and verify that `alembic current` and `alembic check` work.

When you finish, share your project structure and any errors you encounter. We will debug the actual implementation and then move to the next phase without changing the asynchronous architecture unnecessarily.