# 2. Phase 2 architecture — User module

We will implement the user module using the architecture already established in your project. The user module will remain independent of JWT authentication so we can verify registration, database integrity, password hashing, and API responses before moving to Phase 3.

The request flow will be:

FastAPI route

Validate request with Pydantic

User service

Normalize email, hash password, manage transaction

User repository

Async SQLAlchemy queries and persistence

PostgreSQL

UUID, unique email constraint, password hash and account status

## 2.1 Files we will create or update

| File                                  | Responsibility                                         |
| ------------------------------------- | ------------------------------------------------------ |
| `app/db/models/user.py`               | SQLAlchemy user model                                  |
| `app/db/models/__init__.py`           | Register ORM models with Alembic metadata              |
| `app/schemas/user.py`                 | Registration, profile update and safe response schemas |
| `app/core/security.py`                | Password hashing and verification utilities            |
| `app/repositories/user_repository.py` | Async database operations                              |
| `app/services/user_service.py`        | Registration and profile business rules                |
| `app/api/routes/users.py`             | User API endpoints                                     |
| `app/api/router.py`                   | Register the user router                               |
| `alembic/versions/`                   | Migration to create the user table                     |
| `tests/api/test_users.py`             | Registration and response-security tests               |

We will reuse your existing `app/core/config.py`, `app/db/base.py`, `app/db/session.py`, and database dependency.

### One important security decision

A current-user profile endpoint cannot be secured properly until we have authentication. We should not add an unauthenticated `/users/me` endpoint or trust a user ID supplied by the client.

In this phase, we will implement registration and the profile data model, along with profile update validation. We will add the actual authenticated `GET /users/me` and `PATCH /users/me` endpoints in Phase 3 when the current-user dependency is available. That keeps the phase boundary clean without introducing a temporary security weakness.

# 3. Install Phase 2 dependencies

We need two additional dependencies:

- `pwdlib[argon2]` — password hashing using a modern Argon2 implementation.
- `email-validator` — validation support for Pydantic's `EmailStr`.

The `pwdlib` documentation recommends `PasswordHash.recommended()` for password hashing, and Pydantic documents `email-validator` as the dependency required by `EmailStr`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Run these commands in your existing project virtual environment:

```
python -m pip install "pwdlib[argon2]" email-validator
python -m pip check
```

Add the two installed packages to your existing `requirements.txt` with the exact versions reported by:

```
python -m pip show pwdlib email-validator
```

Keep your existing Phase 1 dependencies. Do not replace the entire requirements file with only these two packages.

# 4. Create the user database model

## 4.1 Create `app/db/models/user.py`

This model defines the user table and its database constraints.

```

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index(
            "uq_users_email_lower",
            func.lower(text("email")),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

```

### Why these fields?

| Field             | Reason                                                  |
| ----------------- | ------------------------------------------------------- |
| `id`              | UUID primary key, suitable for distributed applications |
| `email`           | Normalized email address used for identification        |
| `full_name`       | Optional user profile information                       |
| `hashed_password` | Stores a password hash, never the original password     |
| `is_active`       | Supports account deactivation                           |
| `created_at`      | Records account creation time                           |
| `updated_at`      | Tracks profile changes                                  |

### Why a case-insensitive unique index?

Application code will normalize email addresses before storing them. The PostgreSQL unique index on `lower(email)` adds another layer of protection: even if a future script bypasses the normalization logic, PostgreSQL will reject conflicting email addresses that differ only by letter case.

The database constraint is essential because two concurrent registration requests can both check for an email before either transaction commits. Only the database can reliably enforce uniqueness under that race.

## 4.2 Register the model

Replace the contents of `app/db/models/__init__.py` with:

```

from app.db.models.user import User

__all__ = ["User"]

```

Your existing `alembic/env.py` imports `app.db.models`, so Alembic will now discover the `User` model through this package.

# 5. Create the request and response schemas

Create `app/schemas/user.py`.

```

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=12,
        max_length=128,
    )
    full_name: str | None = Field(
        default=None,
        max_length=120,
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        max_length=120,
    )

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

```

## 5.1 Understand the security boundary

`UserCreate` accepts the password because registration requires it.

`UserRead` does not contain either `password` or `hashed_password`. FastAPI will serialize the response according to `response_model=UserRead`, rather than returning every ORM field.

`UserProfileUpdate` deliberately does not permit changing `email`, `is_active`, or administrator privileges. We can introduce a separate, authenticated workflow for those changes when appropriate.

The minimum password length of 12 characters is a starting policy for this template, not a substitute for rate limiting and secure authentication. OWASP recommends adaptive password hashing, including Argon2id, instead of storing plaintext or using fast general-purpose hashes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://cheatsheetseries.owasp.org\&sz=32)

OWASP Cheat Sheet Series



One detail: `EmailStr` validates email syntax; it does not prove that the address exists or belongs to the user. Email verification will be added in Phase 5.

# 6. Implement password hashing

Create `app/core/security.py`.

```

from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a secure password hash."""
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its stored hash."""
    return password_hasher.verify(
        plain_password,
        hashed_password,
    )

```

We will reuse these functions in Phase 3 when implementing login.

Why not hash passwords directly inside an async endpoint? Argon2 hashing is CPU- and memory-intensive by design. We will execute hashing through `asyncio.to_thread()` in the service layer so the expensive hashing operation does not block the event loop while it runs. Database access remains asynchronous.

# 7. Implement the asynchronous user repository

Create `app/repositories/user_repository.py`.

```

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        statement = select(User).where(
            func.lower(User.email) == email.casefold()
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        return await self.session.get(User, user_id)

    async def create(
        self,
        *,
        email: str,
        full_name: str | None,
        hashed_password: str,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
        )

        self.session.add(user)

        # Send the INSERT to PostgreSQL without committing
        # the surrounding service transaction.
        await self.session.flush()
        await self.session.refresh(user)

        return user

```

### Repository design

The repository handles database queries and persistence, but it does not decide how the API should respond to duplicate registrations.

Notice that `create()` uses `flush()` rather than `commit()`. The service layer will own the transaction, so multiple database operations can be grouped into a single atomic operation.

SQLAlchemy's async documentation supports this separation and recommends using an independent `AsyncSession` for each concurrent task.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.0 Documentation+1



# 8. Implement the user service

Create `app/services/user_service.py`.

This is where we normalize input, hash passwords, enforce business rules, and handle duplicate-email races.

```

import asyncio

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class UserAlreadyExistsError(Exception):
    """Raised when an email address is already registered."""


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    async def register_user(
        self,
        payload: UserCreate,
    ) -> User:
        email = str(payload.email).strip().casefold()

        try:
            async with self.session.begin():
                existing_user = (
                    await self.repository.get_by_email(email)
                )

                if existing_user is not None:
                    raise UserAlreadyExistsError(
                        "An account with this email already exists."
                    )

                hashed_password = await asyncio.to_thread(
                    hash_password,
                    payload.password,
                )

                user = await self.repository.create(
                    email=email,
                    full_name=payload.full_name,
                    hashed_password=hashed_password,
                )

            return user

        except IntegrityError as exc:
            # PostgreSQL's unique index remains the final
            # protection against concurrent registrations.
            raise UserAlreadyExistsError(
                "An account with this email already exists."
            ) from exc

```

## 8.1 Why this service is designed this way

1. Normalize first. The same email address should not create separate accounts just because its letter case differs.
2. Check for an existing user. This produces a clear business-level error for ordinary duplicate attempts.
3. Hash the password. Only the resulting hash is passed to the repository.
4. Use a transaction. The database insertion either commits successfully or rolls back.
5. Handle the uniqueness race. PostgreSQL's unique index protects against simultaneous requests that both pass the initial lookup.

We catch `IntegrityError` here because the user creation operation is expected to encounter a unique-email conflict. In a larger service with several unrelated database constraints, we would inspect the violated constraint and translate only known conflicts, allowing unexpected integrity failures to propagate as server errors.

The service deliberately does not assign roles. Public registration cannot choose administrator privileges. RBAC and controlled administrator provisioning will be implemented in later phases.

# 9. Implement the registration endpoint

Create or replace `app/api/routes/users.py`.

```

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db_session
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import (
    UserAlreadyExistsError,
    UserService,
)


router = APIRouter()


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
)
async def register_user(
    payload: UserCreate,
    session: DatabaseSession,
) -> UserRead:
    service = UserService(session)

    try:
        user = await service.register_user(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserRead.model_validate(user)

```

The endpoint returns HTTP `201 Created` on successful registration and `409 Conflict` for a duplicate email.

It never returns the password hash.

## 9.1 Register the router

Update `app/api/router.py` to include the new user router. Preserve your existing health router.

```

from fastapi import APIRouter

from app.api.routes import health, users


api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

```

Because your `main.py` already includes `api_router` under `/api/v1`, the registration endpoint is:

`POST http://127.0.0.1:8000/api/v1/users`

No changes to `main.py` should be necessary if your Phase 1 router setup matches the version we implemented.

## 9.2 Example registration request

In Swagger UI, open `POST /api/v1/users` and submit:

```

{
  "email": "Developer@Example.com",
  "password": "Example-Strong-Passphrase-2026",
  "full_name": "Demo Developer"
}

```

This is a development example only; do not reuse the sample password for an actual account.

Expected successful response:

```

{
  "id": "9b4f0e7d-1e9b-4e65-baa7-7fba3cb02f80",
  "email": "developer@example.com",
  "full_name": "Demo Developer",
  "is_active": true,
  "created_at": "2026-10-28T10:00:00Z",
  "updated_at": "2026-10-28T10:00:00Z"
}

```

The UUID and timestamps above are illustrative. Your API will return actual database-generated values.

The important result is that the email is normalized, a UUID is returned, and neither `password` nor `hashed_password` appears in the response.

# 10. Generate the user-table migration

Now that the model is registered, we can generate the Alembic migration.

Do not edit your existing baseline migration. It records the original Phase 1 schema state. We will add a new revision for the user table.

From the project root, run:

```
python -m alembic revision --autogenerate -m "create users table"
```

Alembic compares `Base.metadata` with the current database schema and generates a candidate migration. Autogeneration is not infallible, so inspect the generated file before applying it.

## 10.1 What the migration should contain

The generated revision should create:

- A `users` table.
- A UUID primary key.
- A non-null email column.
- An optional full name.
- A non-null password-hash column.
- An account-status column with a database default.
- Creation and update timestamps.
- The unique functional index `uq_users_email_lower`.

The generated migration should be similar in structure to this:

```

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )

    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_users_email_lower",
        table_name="users",
    )
    op.drop_table("users")

```

This is an illustrative migration, not a replacement for the actual file generated in your project. Keep Alembic's generated revision ID and `down_revision`, and check the generated SQL for compatibility with your installed SQLAlchemy and Alembic versions.

## 10.2 Apply the migration

After reviewing the generated migration, run:

```
python -m alembic upgrade head
python -m alembic current
python -m alembic heads
python -m alembic check
```

Then verify the table and index directly in PostgreSQL:

```
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'users'
ORDER BY ordinal_position;
```

Verify the index:

```
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'users';
```

You should see the expected columns and the unique case-insensitive email index.

Migration success means the schema exists in PostgreSQL. It does not yet prove registration works; that requires API tests.

# 11. Add Phase 2 API tests

We will test the actual API against your PostgreSQL database, using the existing database configuration and migrations. These are integration tests, so PostgreSQL must be running and the `users` migration must already be applied.

## 11.1 Create `tests/api/test_users.py`

```

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models.user import User
from app.db.session import AsyncSessionFactory
from app.main import app


def make_email() -> str:
    return f"phase2-{uuid4().hex}@example.com"


def test_register_user_success() -> None:
    email = make_email()
    password = "Example-Strong-Passphrase-2026"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "email": email.upper(),
                "password": password,
                "full_name": "Phase Two Test",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["full_name"] == "Phase Two Test"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Sensitive values must never appear in the response.
    assert "password" not in data
    assert "hashed_password" not in data


def test_duplicate_email_is_rejected() -> None:
    email = make_email()

    payload = {
        "email": email,
        "password": "Example-Strong-Passphrase-2026",
        "full_name": "First User",
    }

    with TestClient(app) as client:
        first = client.post("/api/v1/users", json=payload)

        second = client.post(
            "/api/v1/users",
            json={
                **payload,
                "email": email.upper(),
            },
        )

    assert first.status_code == 201
    assert second.status_code == 409


def test_invalid_email_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "email": "not-an-email",
                "password": "Example-Strong-Passphrase-2026",
            },
        )

    assert response.status_code == 422


def test_short_password_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "email": make_email(),
                "password": "short",
            },
        )

    assert response.status_code == 422


def test_password_is_hashed_in_database() -> None:
    email = make_email()
    password = "Example-Strong-Passphrase-2026"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={
                "email": email,
                "password": password,
            },
        )

    assert response.status_code == 201

    async def fetch_user() -> User | None:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()

    user = asyncio.run(fetch_user())

    assert user is not None
    assert user.hashed_password != password
    assert user.hashed_password.startswith("$argon2")

```

These tests cover registration, email normalization, duplicate rejection, invalid inputs, and password-hash storage. The final test reads the stored record to verify that the original password was not persisted.

## 11.2 Run the tests

From the project root:

```
python -m pytest tests/api/test_users.py -v
```

Then run the complete API test suite:

```
python -m pytest tests/api -v
```

Expected results: all tests pass against your local PostgreSQL database.

If you see a failure, do not change the expected status code just to make the test pass. Inspect the error and correct the underlying issue.

# 12. Verify Phase 2 end to end

Run the following sequence from your project root after implementing the files above.

```
# 1. Check installed dependencies
python -m pip check

# 2. Apply all migrations
python -m alembic upgrade head

# 3. Confirm the current migration
python -m alembic current
python -m alembic heads

# 4. Verify no model/schema migration is missing
python -m alembic check

# 5. Run user-module tests
python -m pytest tests/api/test_users.py -v

# 6. Run all API tests
python -m pytest tests/api -v

# 7. Start the application
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and test `POST /api/v1/users`.

## 12.1 Expected behavior

| Test scenario                                            | Expected result                         |
| -------------------------------------------------------- | --------------------------------------- |
| Register with a valid email and password                 | `201 Created`                           |
| Register again using the same email                      | `409 Conflict`                          |
| Register using the same email with different letter case | `409 Conflict`                          |
| Submit an invalid email                                  | `422 Unprocessable Entity`              |
| Submit a password shorter than 12 characters             | `422 Unprocessable Entity`              |
| Inspect the successful response                          | No password or password hash            |
| Inspect the database record                              | Argon2 password hash stored             |
| Submit an invalid request                                | No user created                         |
| Run Alembic migration                                    | User table and unique email index exist |

## 12.2 Phase 2 completion checklist

## Phase 2 verification

0/14

pwdlib Argon2 and email-validator are installed and recorded in requirements.

User ORM model uses a UUID primary key.

PostgreSQL enforces case-insensitive email uniqueness.

Account status and timestamps are present.

Password hashes are generated outside the event-loop thread.

Registration and profile schemas are implemented.

Async user repository and service are implemented.

Registration endpoint returns HTTP 201.

Duplicate email registration returns HTTP 409.

Invalid email and short password return HTTP 422.

Successful API responses never expose password hashes.

Database inspection confirms an Argon2 hash is stored.

Alembic migration creates the user table and index.

All Phase 2 API tests pass.

Copy verification report

Only mark an item complete after verifying it in your local environment.

# 13. What comes after Phase 2?

Once the user module and migration pass, we can begin Phase 3 — Authentication.

That phase will build on this exact user model and introduce:

1. Login using email and password.
2. JWT access-token creation and validation.
3. A protected current-user dependency.
4. Authenticated `GET /api/v1/users/me` and `PATCH /api/v1/users/me` profile endpoints.
5. Refresh-token persistence and rotation.
6. Redis-backed access-token revocation.
7. Logout and logout-all.
8. Authentication tests for missing, invalid, expired, and revoked tokens.

We will not need to convert the database layer from synchronous to asynchronous because we are keeping the async architecture from the beginning.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.0 Documentation+1



Your next action: implement the files, generate and inspect the Alembic migration, and run the tests. If anything fails, share the traceback, the relevant file, and the command you ran. We will fix the specific issue before proceeding to authentication.