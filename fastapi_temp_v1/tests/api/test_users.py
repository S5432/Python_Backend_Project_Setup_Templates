
import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models.user import User
from app.db.session import AsyncSessionFactory
from app.main import app


def make_email() -> str:
    return f"phase2-{uuid4().hex}@gmail.com"


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
