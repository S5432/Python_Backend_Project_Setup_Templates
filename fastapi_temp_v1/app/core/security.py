import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hasher.verify(
        plain_password,
        hashed_password,
    )


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return await asyncio.to_thread(
        verify_password,
        plain_password,
        hashed_password,
    )


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


# def create_access_token(
#     *,
#     user_id: uuid.UUID,
#     token_version: int,
# ) -> tuple[str, str, datetime]:
#     settings = get_settings()
#     now = datetime.now(timezone.utc)
#     expires_at = now + timedelta(
#         minutes=settings.access_token_minutes
#     )
#     jti = str(uuid.uuid4())

#     payload = {
#         "sub": str(user_id),
#         "jti": jti,
#         "ver": token_version,
#         "iss": settings.jwt_issuer,
#         "aud": settings.jwt_audience,
#         "iat": now,
#         "exp": expires_at,
#     }

#     token = jwt.encode(
#         payload,
#         settings.jwt_secret_key.get_secret_value(),
#         algorithm=settings.jwt_algorithm,
#     )

#     return token, jti, expires_at


#phase 3: updated

def create_access_token(
    *,
    user_id: uuid.UUID,
    token_version: int,
    family_id: uuid.UUID | None = None,
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.access_token_minutes
    )
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(user_id),
        "jti": jti,
        "sid": str(family_id or uuid.uuid4()),
        "ver": token_version,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    return token, jti, expires_at


def decode_access_token(token: str) -> dict:
    settings = get_settings()

    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={
            "require": [
                "sub", "jti", "ver", "iss",
                "aud", "iat", "exp",
            ],
        },
    )