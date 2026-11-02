
"""RBAC matrix and object-level authorization integration tests.

These tests use the configured PostgreSQL database and Redis service.

Run database migrations before executing the test suite.
"""

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from asgi_lifespan import LifespanManager

from app.core.constants import ROLE_ADMIN
from app.db.models.role import Role
from app.db.models.user import User
from app.db.session import AsyncSessionFactory
from app.main import app


PASSWORD = "RBAC-Test-Strong-Passphrase-2026"


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


async def _register_and_login(
    client: AsyncClient,
    email: str,
) -> tuple[str, str]:
    """Register a user and return access token and user ID."""

    registered = await client.post(
        "/api/v1/users",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "RBAC Test",
        },
    )

    assert registered.status_code == 201, registered.text

    logged_in = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert logged_in.status_code == 200, logged_in.text

    return (
        logged_in.json()["access_token"],
        registered.json()["id"],
    )


async def _grant_admin(user_id: str) -> None:
    """Assign the admin role to a user for integration testing."""

    async with AsyncSessionFactory() as session:
        async with session.begin():

            result = await session.execute(
                select(User)
                .options(selectinload(User.roles))
                .where(User.id == UUID(user_id))
            )

            user = result.scalar_one_or_none()

            assert user is not None, "Test user does not exist"

            role_result = await session.execute(
                select(Role).where(Role.name == ROLE_ADMIN)
            )

            admin_role = role_result.scalar_one_or_none()

            assert admin_role is not None, (
                "Admin role does not exist. "
                "Run the RBAC role provisioning migration first."
            )

            if all(role.name != ROLE_ADMIN for role in user.roles):
                user.roles.append(admin_role)


async def _has_admin_role(user_id: str) -> bool:
    """Verify that a user does not have admin privileges."""

    async with AsyncSessionFactory() as session:

        result = await session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == UUID(user_id))
        )

        user = result.scalar_one_or_none()

        return user is not None and all(
            role.name != ROLE_ADMIN for role in user.roles
        )


@pytest.mark.asyncio
async def test_rbac_matrix_and_object_level_authorization() -> None:

    user_email = _email("rbac-user")
    admin_email = _email("rbac-admin")

    # Manage application startup and shutdown.
    async with LifespanManager(app) as manager:

        transport = ASGITransport(app=manager.app)

        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:

            # --------------------------------------------------
            # 1. Register normal user and admin test user
            # --------------------------------------------------

            user_token, user_id = await _register_and_login(
                client,
                user_email,
            )

            admin_token, admin_id = await _register_and_login(
                client,
                admin_email,
            )

            # --------------------------------------------------
            # 2. Assign admin role directly through the database
            # --------------------------------------------------

            await _grant_admin(admin_id)

            # Login again to verify the newly assigned database role.
            admin_login = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": admin_email,
                    "password": PASSWORD,
                },
            )

            assert admin_login.status_code == 200, admin_login.text

            admin_token = admin_login.json()["access_token"]

            # --------------------------------------------------
            # 3. Public endpoint
            # --------------------------------------------------

            health_response = await client.get(
                "/api/v1/health/live"
            )

            assert health_response.status_code == 200

            # --------------------------------------------------
            # 4. Anonymous access tests
            # --------------------------------------------------

            assert (
                await client.get("/api/v1/users/me")
            ).status_code == 401

            assert (
                await client.get("/api/v1/rbac/user-area")
            ).status_code == 401

            assert (
                await client.get("/api/v1/rbac/me")
            ).status_code == 401

            assert (
                await client.get(
                    f"/api/v1/rbac/resources/{user_id}"
                )
            ).status_code == 401

            # --------------------------------------------------
            # 5. Normal user access tests
            # --------------------------------------------------

            user_headers = {
                "Authorization": f"Bearer {user_token}"
            }

            assert (
                await client.get(
                    "/api/v1/users/me",
                    headers=user_headers,
                )
            ).status_code == 200

            assert (
                await client.get(
                    "/api/v1/rbac/user-area",
                    headers=user_headers,
                )
            ).status_code == 200

            # Normal user cannot access admin endpoint.
            assert (
                await client.get(
                    "/api/v1/rbac/me",
                    headers=user_headers,
                )
            ).status_code == 403

            # Normal user can access their own resource.
            assert (
                await client.get(
                    f"/api/v1/rbac/resources/{user_id}",
                    headers=user_headers,
                )
            ).status_code == 200

            # Normal user cannot access another user's resource.
            assert (
                await client.get(
                    f"/api/v1/rbac/resources/{admin_id}",
                    headers=user_headers,
                )
            ).status_code == 403

            # --------------------------------------------------
            # 6. Admin access tests
            # --------------------------------------------------

            admin_headers = {
                "Authorization": f"Bearer {admin_token}"
            }

            assert (
                await client.get(
                    "/api/v1/users/me",
                    headers=admin_headers,
                )
            ).status_code == 200

            assert (
                await client.get(
                    "/api/v1/rbac/user-area",
                    headers=admin_headers,
                )
            ).status_code == 200

            # Admin can access admin-only endpoint.
            assert (
                await client.get(
                    "/api/v1/rbac/me",
                    headers=admin_headers,
                )
            ).status_code == 200

            # Admin can access another user's resource.
            assert (
                await client.get(
                    f"/api/v1/rbac/resources/{user_id}",
                    headers=admin_headers,
                )
            ).status_code == 200

            # --------------------------------------------------
            # 7. Prevent public role escalation
            # --------------------------------------------------

            untrusted_email = _email("rbac-no-escalation")

            response = await client.post(
                "/api/v1/users",
                json={
                    "email": untrusted_email,
                    "password": PASSWORD,
                    "role": "admin",
                },
            )

            assert response.status_code == 201, response.text

            registered_id = response.json()["id"]

            # Public registration must never grant admin privileges.
            assert await _has_admin_role(registered_id)
