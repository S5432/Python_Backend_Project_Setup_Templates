"""Provision an administrator from a trusted command line.

Examples:
  python -m scripts.create_admin --email admin@example.com
  The password is prompted securely if the account does not already exist.
"""
import argparse
import asyncio
import getpass

from sqlalchemy import func, select

from app.core.constants import ROLE_ADMIN, ROLE_USER
from app.core.security import hash_password
from app.db.models.role import Role
from app.db.models.user import User
from app.db.session import AsyncSessionFactory, engine


async def provision_admin(email: str, password: str | None) -> None:
    normalized_email = email.strip().casefold()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # roles_result = await session.execute(
            #     select(Role).where(Role.name.in_([ROLE_USER, ROLE_ADMIN]))
            # )
            # roles = {role.name: role for role in roles_result.scalars()}
            # if ROLE_USER not in roles or ROLE_ADMIN not in roles:
            #     raise RuntimeError(
            #         "Roles are missing. Run `alembic upgrade head` first."
            #     )

            # Ensure the built-in roles exist.
            # The schema migration creates the tables, but may not seed the rows.
            roles_result = await session.execute(
                select(Role).where(Role.name.in_([ROLE_USER, ROLE_ADMIN]))
            )
            roles = {role.name: role for role in roles_result.scalars()}

            role_descriptions = {
                ROLE_USER: "Standard authenticated user",
                ROLE_ADMIN: "Administrator with elevated permissions",
            }

            for role_name, description in role_descriptions.items():
                if role_name not in roles:
                    role = Role(
                        name=role_name,
                        description=description,
                    )
                    session.add(role)
                    await session.flush()
                    roles[role_name] = role

            user_result = await session.execute(
                select(User).where(func.lower(User.email) == normalized_email)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                if not password:
                    password = getpass.getpass("New admin password: ")
                if len(password) < 8:
                    raise ValueError("Password must contain at least 8 characters.")
                user = User(
                    email=normalized_email,
                    hashed_password=hash_password(password),
                    is_active=True,
                )
                user.roles.append(roles[ROLE_USER])
                session.add(user)
                await session.flush()
            if not any(role.name == ROLE_ADMIN for role in user.roles):
                user.roles.append(roles[ROLE_ADMIN])
            print(f"Administrator role provisioned for {normalized_email}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a FastAPI administrator.")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument(
        "--password",
        help="Optional password for a newly created account; prefer secure prompt",
    )
    args = parser.parse_args()
    asyncio.run(provision_admin(args.email, args.password))


if __name__ == "__main__":
    main()
