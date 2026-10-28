# This is the first phase : ShvetVarni Reusable FastAPI Backend Template — Production-Oriented Architecture
# ShvetVarni Reusable FastAPI Backend Template — Production-Oriented Architecture

Your objective is to build a reusable backend foundation for ShvetVarni that you can clone for different client projects without repeatedly implementing registration, authentication, authorization, database configuration, migrations, security controls, logging, and deployment infrastructure.

We should treat this as an internal engineering product, not just a collection of FastAPI files.

The goal is that a developer can clone the template, configure environment variables, start PostgreSQL and Redis, run database migrations, execute tests, and begin implementing the client's actual business logic.

## 1. Define the final objective

Your template should provide the following foundation out of the box.

Database foundation

PostgreSQL, SQLAlchemy 2.x async ORM, async database sessions, Alembic migrations, connection pooling, and transaction management.

Authentication and security

Registration, login, password hashing, JWT access tokens, refresh-token rotation, logout, token revocation, and secure configuration.

Authorization and RBAC

Admin and user roles, reusable permission dependencies, protected routes, account-status checks, and tests proving which requests are allowed or denied.

Production operations

Structured logging, request IDs, centralized exception handling, health checks, CORS, Docker, automated tests, and deployment documentation.

Background processing

Celery workers, Redis as a broker, email verification, and retryable background tasks without blocking API requests.

Important engineering principle: asynchronous database access must be part of the architecture from Phase 1. We should not build a synchronous application and attempt to convert it later.

Also, async alone does not make a backend production-ready. We must separately address security, transaction boundaries, token lifecycle, database migrations, testing, deployment, and operational monitoring.

## 2. Review of your proposed folder structure

Your structure is a good starting point because it separates API routes, database models, schemas, repositories, services, and dependencies. I recommend refining it before we begin writing code.

### 2.1 What should change and why?

| Your current design               | Recommended change                                                                     | Reason                                                        |
| --------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `models/` and `db/models/`        | Keep ORM models in `db/models/` and use `schemas/` for Pydantic models                 | Avoid duplicate or ambiguous model locations                  |
| `repositories/auth_repository.py` | Remove initially; use `user_repository.py` and `refresh_token_repository.py` as needed | Authentication logic belongs mainly in the service layer      |
| `core/security.py`                | Keep; implement password hashing and JWT utilities                                     | Centralized security primitives                               |
| `dependencies/auth.py`            | Split into authentication and authorization dependencies                               | Makes permission rules reusable                               |
| `dependencies/permissions.py`     | Keep; define role and permission checks                                                | Avoid repeating access-control logic                          |
| `workers/celery_app.py`           | Keep; add organized task modules                                                       | Separates background processing from HTTP requests            |
| `middleware/`                     | Add request ID, request logging, and security-related configuration as needed          | Improves traceability and operations                          |
| `tests/`                          | Organize into unit, integration, API, and security tests                               | Ensures changes do not silently break authentication          |
| `config.py`                       | Use validated settings with separate development and production configurations         | Prevents missing or unsafe configuration from going unnoticed |

### 2.2 Additional components worth including

- `core/constants.py` — shared role names and stable application constants.
- `core/lifespan.py` — manage application startup and shutdown resources.
- `core/responses.py` — only if a consistent API response envelope is required.
- `db/base.py` — shared SQLAlchemy declarative base and model metadata.
- `db/session.py` — async engine and session factory.
- `schemas/common.py` — reusable pagination or generic response schemas when needed.
- `services/` — business rules and orchestration.
- `repositories/` — database queries, with explicit async methods.
- `api/routes/health.py` — health and readiness endpoints.
- `scripts/` — bootstrap scripts, such as creating the first administrator.
- `tests/` — RBAC matrix, refresh-token lifecycle, migration, and security tests.
- `alembic/versions/` — version-controlled schema migrations.
- `.dockerignore`, `.gitignore`, and CI configuration — protect secrets, keep images small, and automate quality checks.

One especially important decision: the initial administrator must not be created through public signup by supplying `"role": "admin"`. We will create the first administrator through a controlled bootstrap command or another trusted provisioning process.

## 3. Recommended final folder structure

This is the structure I recommend for the first reusable version. We will add implementation files progressively instead of trying to build everything in one step.

```

shvetvarni-fastapi-template/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── exceptions.py
│   │   ├── exception_handlers.py
│   │   ├── logging_config.py
│   │   ├── constants.py
│   │   └── lifespan.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── user.py
│   │       └── refresh_token.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   └── common.py
│   ├── api/
│   │   ├── router.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── admin.py
│   │       └── health.py
│   ├── repositories/
│   │   ├── user_repository.py
│   │   └── refresh_token_repository.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   └── email_service.py
│   ├── dependencies/
│   │   ├── database.py
│   │   ├── auth.py
│   │   └── permissions.py
│   ├── middleware/
│   │   ├── request_id.py
│   │   └── logging.py
│   └── workers/
│       ├── celery_app.py
│       └── tasks/
│           ├── __init__.py
│           └── email_tasks.py
├── alembic/
│   ├── env.py
│   └── versions/
├── scripts/
│   └── create_admin.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── security/
├── .env.example
├── .gitignore
├── .dockerignore
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md

```

Architecture rule: API routes should not contain raw database queries or all the business logic. Routes call services, services coordinate the use cases, and repositories handle database operations. Authentication dependencies identify the current user; permission dependencies decide whether that user may perform a particular action.

This separation makes the template easier to test, extend, and reuse across unrelated client applications.

## 4. Technology stack and implementation decisions

I checked the relevant official documentation and security guidance. These are the architectural choices I recommend for the first version.

| Component        | Recommended technology              | Purpose                                                 |
| ---------------- | ----------------------------------- | ------------------------------------------------------- |
| API framework    | FastAPI                             | REST API and dependency injection                       |
| Python           | Python 3.12+                        | Modern typing and async support                         |
| Database         | PostgreSQL                          | Persistent application data                             |
| ORM              | SQLAlchemy 2.x async                | Non-blocking database access                            |
| Database driver  | `asyncpg`                           | Async PostgreSQL connections                            |
| Migrations       | Alembic                             | Version-controlled schema changes                       |
| Validation       | Pydantic v2 and `pydantic-settings` | Request validation and configuration                    |
| Password hashing | `pwdlib[argon2]`                    | Argon2-based password hashing                           |
| JWT              | PyJWT                               | Access-token creation and validation                    |
| Token lifecycle  | Redis + PostgreSQL                  | Revocation support and persistent refresh-token records |
| Background jobs  | Celery + Redis                      | Email and other background tasks                        |
| Testing          | pytest + HTTPX                      | API, async integration, and security testing            |
| Containers       | Docker Compose                      | Repeatable local development and deployment             |

### Why these choices?

Async database access: SQLAlchemy's official documentation supports `AsyncEngine`, `AsyncSession`, and `async_sessionmaker`. Each concurrent request or task must have its own session; an `AsyncSession` must not be shared across concurrent tasks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation+1



Migrations: Alembic supports running migrations using an async SQLAlchemy engine. We will create migrations explicitly rather than creating production tables automatically when the application starts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Password security: Use Argon2id rather than plain text or fast general-purpose hashes such as SHA-256 for passwords.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cheatsheetseries.owasp.org\&sz=32)

OWASP Cheat Sheet Series+1



Background tasks: Celery supports retries and exponential backoff. Tasks should be designed to tolerate duplicate execution, particularly when sending emails or processing events.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.celeryq.dev\&sz=32)

Celery 5.6.3 documentation+1



One distinction matters: Celery is a task queue, not a replacement for async API endpoints. FastAPI endpoints and database operations remain asynchronous. Celery workers handle tasks independently and may use synchronous task functions where appropriate.

## 5. Authentication architecture

We need to design the token lifecycle before writing the login endpoint.

1\. Register / Login

Validate input, verify credentials, check account status

2\. Issue tokens

Short-lived JWT access token + opaque refresh token

3\. Authenticate each request

Validate signature, expiry, token type, user ID and account status

4\. Authorize the action

Check role, permissions and resource ownership

5\. Execute business logic

Service → repository → async database

### 5.1 Access and refresh tokens

We will use these starting defaults, configurable through environment variables.

| Setting                | Initial default                                       |
| ---------------------- | ----------------------------------------------------- |
| Access-token lifetime  | 15 minutes                                            |
| Refresh-token lifetime | 7 days                                                |
| Password hashing       | Argon2id                                              |
| Access-token signing   | HS256 with a strong, randomly generated secret        |
| Refresh-token storage  | Store a cryptographic hash in PostgreSQL              |
| Token revocation       | Redis-backed access-token denylist, with expiration   |
| Refresh-token rotation | Issue a new refresh token on every successful refresh |

These are initial engineering defaults, not universal security requirements. The actual settings depend on the client application's threat model and deployment environment.

The refresh-token hash in PostgreSQL allows us to persist session state, track revocation, and rotate tokens. Redis can provide a fast revocation check for access tokens. A logout must revoke the refresh session and invalidate the current access token according to the chosen token policy.

Important: a JWT is signed, not encrypted by default. We must never put passwords, secrets, or other confidential data inside its payload.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fastapi.tiangolo.com\&sz=32)

FastAPI+1



### 5.2 Authentication endpoints

| Method | Endpoint                    | Access                         | Purpose                                         |
| ------ | --------------------------- | ------------------------------ | ----------------------------------------------- |
| POST   | `/api/v1/auth/register`     | Public                         | Register a normal user                          |
| POST   | `/api/v1/auth/login`        | Public                         | Authenticate and issue tokens                   |
| POST   | `/api/v1/auth/refresh`      | Valid refresh session          | Rotate refresh token and issue new access token |
| POST   | `/api/v1/auth/logout`       | Authenticated                  | Revoke the current session                      |
| POST   | `/api/v1/auth/logout-all`   | Authenticated                  | Revoke all sessions for the current user        |
| GET    | `/api/v1/users/me`          | Authenticated                  | Retrieve the current user's profile             |
| PATCH  | `/api/v1/users/me`          | Authenticated                  | Update permitted profile fields                 |
| POST   | `/api/v1/auth/verify-email` | Public with verification token | Verify the user's email                         |

We will also add rate limiting to login and other abuse-prone endpoints, generic login errors to reduce account enumeration, and appropriate validation for passwords and email addresses.

For production, we should additionally decide whether refresh tokens are sent in secure, HttpOnly cookies or returned to a trusted client for controlled storage. That decision depends on whether the client is a browser application, mobile application, or server-to-server integration.

## 6. RBAC: the most important part to test

Role-based access control must be enforced on the server, not merely by hiding buttons in the frontend.

For our first version, we will implement two roles:

- `user` — can access their own profile and normal-user endpoints.
- `admin` — can access normal-user functionality and administrator-only endpoints.

Later, we can introduce granular permissions, such as `users:read`, `users:update`, and `users:delete`, without redesigning the whole application.

### 6.1 RBAC test endpoints

We will build dedicated endpoints that let you verify the access-control system.

| Method | Endpoint                             | Anonymous | User  | Admin                        |
| ------ | ------------------------------------ | --------- | ----- | ---------------------------- |
| GET    | `/api/v1/health/live`                | Allow     | Allow | Allow                        |
| GET    | `/api/v1/users/me`                   | Deny      | Allow | Allow                        |
| GET    | `/api/v1/test-rbac/public`           | Allow     | Allow | Allow                        |
| GET    | `/api/v1/test-rbac/user`             | Deny      | Allow | Allow                        |
| GET    | `/api/v1/test-rbac/admin`            | Deny      | Deny  | Allow                        |
| GET    | `/api/v1/admin/users`                | Deny      | Deny  | Allow                        |
| PATCH  | `/api/v1/admin/users/{user_id}/role` | Deny      | Deny  | Allow, subject to validation |

The `/api/v1/test-rbac/*` routes are diagnostic endpoints for development and automated tests. We can omit them from production deployments or place them behind an explicit configuration flag. The actual admin routes remain protected in every environment.

### 6.2 Expected HTTP responses

| Scenario                                    | Expected result                                                               |
| ------------------------------------------- | ----------------------------------------------------------------------------- |
| No access token on a protected route        | `401 Unauthorized`                                                            |
| Malformed, expired, or revoked access token | `401 Unauthorized`                                                            |
| Valid user token on a user endpoint         | `200 OK`                                                                      |
| Valid user token on an admin-only endpoint  | `403 Forbidden`                                                               |
| Valid admin token on an admin-only endpoint | `200 OK`                                                                      |
| Valid token for a disabled account          | `403 Forbidden` or the project's consistently defined account-policy response |

A `401` means the request has not established valid authentication. A `403` means authentication succeeded, but the authenticated principal lacks permission.

Important security test: modifying `"role": "user"` to `"role": "admin"` inside a JWT must not grant administrator access. A modified signature must fail validation. The role used for authorization should be obtained from trusted server-side state, or be validated against an explicitly designed and securely managed authorization-token policy.

We must also test object-level permissions. A normal user who changes a resource ID in a URL must not be able to read or update another user's private resource simply because they have a valid token.

### 6.3 RBAC architecture

```

# Architectural example — not the complete implementation.

from typing import Annotated

from fastapi import Depends, HTTPException, status

# get_current_user will be implemented in Phase 3.
# get_current_active_user will validate account status.


async def require_admin(
    current_user: Annotated[
        "User",
        Depends(get_current_active_user),
    ],
) -> "User":
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return current_user

```

This demonstrates the authorization rule, not a file that we should copy and run yet. The referenced dependencies and `User` model will be implemented in the appropriate phases. In the final template, we will use a reusable role-checking dependency rather than hard-coding this logic into every endpoint.

## 7. Custom exceptions and centralized error handling

We should establish a consistent error contract for all applications built from the template.

Example response:

```

{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "You do not have permission to perform this action.",
    "request_id": "req_example_123"
  }
}

```

This is an illustrative response format; we will implement it in Phase 6.

We should create a small, intentional exception hierarchy:

| Exception                        | Typical HTTP status |
| -------------------------------- | ------------------- |
| `AppException`                   | Defined by subclass |
| `ResourceNotFoundException`      | 404                 |
| `ResourceAlreadyExistsException` | 409                 |
| `AuthenticationException`        | 401                 |
| `AuthorizationException`         | 403                 |
| `ValidationException`            | 422                 |
| Unexpected unhandled exception   | 500                 |

The exception handler will return safe, client-facing messages while logging technical details internally. It must not expose stack traces, database connection strings, SQL statements containing sensitive data, or secrets.

We should preserve FastAPI's normal request-validation behavior unless we have a specific reason to standardize it under our error contract.

## 8. The complete phase-by-phase development roadmap

We will build the template incrementally. Each phase must have a working deliverable, verification steps, and a clear completion condition before we move forward.

## 01

Project setup and async PostgreSQL

Start here

Python environment, FastAPI application factory or entry point, settings, PostgreSQL, SQLAlchemy async engine, session dependency, Alembic, initial migration, and database connectivity.

Completion: the API starts, the database connects, and migrations run successfully.

## 02

User module

User ORM model, UUID primary key, unique normalized email, password hash field, account status, profile schemas, repository and service, signup and profile endpoints.

Completion: registration works and password hashes are never returned in API responses.

## 03

Authentication

Argon2id hashing, login, JWT access tokens, refresh-token storage, rotation, Redis revocation, logout, logout-all, and token validation.

Completion: valid credentials work, invalid credentials fail, and revoked sessions cannot continue using the protected APIs.

## 04

RBAC and authorization

Role model, current-user dependency, admin dependency, protected test endpoints, role provisioning, object-level authorization, and automated access-control tests.

Completion: the entire RBAC matrix passes for anonymous, user, and admin requests.

## 05

Celery and email verification

Redis broker, worker configuration, email service, verification tokens, retries, failure handling, and an email-provider abstraction.

Completion: registration can trigger a real or sandbox email through a background worker, and failures are handled safely.

## 06

Production hardening

Custom exceptions, request IDs, structured logs, health and readiness checks, strict CORS, request limits, security headers where appropriate, rate limiting, secret validation, and security tests.

Completion: failures are observable, unsafe configurations are rejected, and security tests pass.

## 07

Docker, CI and documentation

Dockerfile, Docker Compose, separate API and Celery worker processes, migrations, environment example, automated checks, README, and clone-and-run instructions.

Completion: a fresh developer environment can be initialized and verified from documented commands.

### A small but important refinement

Your Phase 6 includes configuration, logging, and exceptions. We should create the basic versions of those components in Phase 1, then harden them in Phase 6. Likewise, Docker can be introduced during development to verify reproducibility, even though final deployment packaging and documentation belong to Phase 7.

This avoids building a weak foundation and trying to retrofit it later.

## 9. Security hardening checklist

A reusable template should not be called production-ready simply because login and role checks work.

We will use the following checklist before releasing version 1.0.

## Version 1.0 release checklist

0/17 checked

### Identity and access

Passwords use Argon2id and are never logged or returned.

Public signup cannot assign an administrator role.

JWT signatures, expiry, issuer, audience and token type are validated as configured.

Refresh tokens rotate, and reuse of a revoked token is detected.

Logout and account disablement have defined revocation behavior.

Object-level ownership is checked for private resources.

### API and application

Login and verification endpoints have rate limits.

CORS allows only configured frontend origins.

Request payloads and password lengths are validated.

Errors do not expose secrets or internal stack traces.

Request IDs connect API errors with application logs.

### Infrastructure and delivery

Secrets are not committed to Git or baked into container images.

Database migrations run as a controlled deployment step.

Database, Redis and worker health are monitored.

Tests cover success, denial, token expiry, refresh reuse and account disablement.

Production runs with debug mode disabled and a non-root container user.

Dependencies are pinned and scanned; CI runs tests and static checks.

Copy checklist

This is our release checklist, not proof that the system has passed a security audit. In particular, session revocation and token storage must be evaluated against the actual deployment model. OWASP's guidance on JWTs, session management, and password storage will inform those decisions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cheatsheetseries.owasp.org\&sz=32)

OWASP Cheat Sheet Series+2



## 10. Phase 1 — Start implementing the foundation

Now we should stop expanding the design and begin building the actual application. Our first objective is a working FastAPI application connected to PostgreSQL using asynchronous SQLAlchemy sessions and Alembic migrations.

We will not implement authentication in this phase. Instead, we will establish the database and configuration patterns that all later modules will reuse.

### 10.1 Create the project

Since you are working on Windows, open PowerShell and execute:

```
mkdir shvetvarni-fastapi-template
cd shvetvarni-fastapi-template

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
```

If PowerShell blocks virtual-environment activation, you can use the environment's Python executable directly:

```
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Create the initial directory structure:

```
$dirs = @(
    "app/core",
    "app/db/models",
    "app/schemas",
    "app/api/routes",
    "app/repositories",
    "app/services",
    "app/dependencies",
    "app/middleware",
    "app/workers/tasks",
    "alembic/versions",
    "scripts",
    "tests/unit",
    "tests/integration",
    "tests/api",
    "tests/security"
)

$dirs | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}

New-Item -ItemType File -Force -Path `
    "app/__init__.py", `
    "app/main.py", `
    "app/core/__init__.py", `
    "app/db/__init__.py", `
    "app/db/models/__init__.py", `
    "app/api/__init__.py", `
    "app/api/routes/__init__.py", `
    "app/repositories/__init__.py", `
    "app/services/__init__.py", `
    "app/dependencies/__init__.py", `
    "tests/__init__.py" | Out-Null
```

### 10.2 Install the initial dependencies

Create `requirements.txt` with the following initial dependencies:

```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]>=2.0,<3.0
asyncpg
alembic
pydantic-settings
python-dotenv
```

These are intentionally unpinned development constraints for the first setup. Before the template is released, we will generate a tested, exact dependency lock or pinned requirements file and establish an update process.

Install them:

```
python -m pip install -r requirements.txt
```

Verify the installed environment:

```
python --version
python -m pip check
```

### 10.3 Configure the environment

Create `.env.example`:

```
APP_NAME=ShvetVarni FastAPI Template
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+asyncpg://app_user:replace_me@localhost:5432/shvetvarni_db

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

Copy it to `.env` and replace the database credentials with your local PostgreSQL credentials.

```
Copy-Item .env.example .env
```

Add the following to `.gitignore`:

```
.venv/
__pycache__/
*.py[cod]
.env
.pytest_cache/
.coverage
htmlcov/
dist/
build/
```

Never commit `.env` or real credentials to Git. Later, Docker Compose will provide the PostgreSQL and Redis services so developers can initialize the environment consistently.

### 10.4 Create the settings module

Create `app/core/config.py`:

```
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShvetVarni FastAPI Template"
    app_env: Literal["development", "test", "staging", "production"] = (
        "development"
    )
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

This gives us validated environment configuration and a single settings entry point. We will expand it later for JWT secrets, Redis, email, token lifetimes, and production security policies.

For production, we will also reject unsafe settings such as debug mode being enabled, weak or missing secrets, and inappropriate CORS configuration.

### 10.5 Create the asynchronous database engine

Create `app/db/session.py`:

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

Why this design matters:

- `create_async_engine()` provides the asynchronous database engine.
- `async_sessionmaker` provides a consistent session factory.
- `get_db_session()` gives each request its own session.
- `pool_pre_ping=True` helps detect stale connections before using them.
- `expire_on_commit=False` avoids automatically expiring ORM attributes after a commit.

The dependency owns session cleanup. We will explicitly define transaction ownership in the service layer when we implement registration and other write operations. We will not share sessions between concurrent tasks or use blocking database drivers in async routes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation+1



### 10.6 Create the initial FastAPI application

Create `app/main.py`:

```
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.get("/api/v1/health/live", tags=["Health"])
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {
        "message": "ShvetVarni FastAPI Template",
        "status": "running",
    }
```

The liveness endpoint confirms that the API process is responding. It does not prove that PostgreSQL is healthy. We will add a separate readiness check that verifies database connectivity in the production-readiness phase.

### 10.7 Run the application

Make sure PostgreSQL is running and that the database and user specified in `.env` exist.

Start FastAPI:

```
python -m uvicorn app.main:app --reload
```

Open these URLs in your browser:

- API root: `http://127.0.0.1:8000/`
- Liveness check: `http://127.0.0.1:8000/api/v1/health/live`
- Swagger documentation: `http://127.0.0.1:8000/docs`

At this stage, the API should start and the health endpoints should respond. The database engine is configured but has not yet been tested by an actual database query.

### 10.8 Initialize Alembic

Stop the server, then run:

```
python -m alembic init -t async alembic
```

Alembic's async template provides the migration infrastructure for an async SQLAlchemy application.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Next, we will configure `alembic.ini` and `alembic/env.py` to load the validated settings, use the async database URL, and reference the application's SQLAlchemy metadata.

Do not run `alembic upgrade head` yet. We must first configure the migration environment and create the initial SQLAlchemy declarative base. We will do those in the next implementation step.

## 11. Phase 1 acceptance criteria

Before moving to Phase 2, we should verify each item below.

## Phase 1 verification

0/10

Python virtual environment is working.

Initial dependencies install without conflicts.

Environment settings load and validate.

FastAPI starts and the Swagger page opens.

Liveness endpoint returns HTTP 200.

Async SQLAlchemy engine and session factory are configured.

PostgreSQL connection succeeds through a real query.

Alembic uses the asynchronous migration template.

Initial migration creates the expected schema successfully.

A clean database can be upgraded using documented commands.

## 12. What I recommend you do now

Complete the initial setup through Step 10.7 first. Then send me the output of these commands:

```
python --version
python -m pip check
python -m uvicorn app.main:app --reload
```

Also tell me whether PostgreSQL is installed locally or you prefer to run it through Docker.

We will then finish the async database connection test, configure Alembic properly, create the first migration, and verify the setup before building the user module. This approach keeps the project incremental and testable instead of introducing authentication, Redis, Celery, and Docker all at once.