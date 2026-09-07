"""
JWT auth utilities — VirtualFit Phase 2
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-long-random-secret")
JWT_ALGO   = "HS256"
JWT_DAYS   = 30


def _get_secret() -> str:
    return os.environ.get("JWT_SECRET", JWT_SECRET)


def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user_id: int, email: str, is_admin: bool) -> str:
    import jwt
    payload = {
        "sub":      str(user_id),
        "email":    email,
        "is_admin": is_admin,
        "exp":      datetime.now(timezone.utc) + timedelta(days=JWT_DAYS),
    }
    return jwt.encode(payload, _get_secret(), algorithm=JWT_ALGO)


def decode_token(token: str) -> Optional[dict]:
    """Returns payload dict or None."""
    import jwt
    try:
        return jwt.decode(token, _get_secret(), algorithms=[JWT_ALGO])
    except Exception as e:
        logger.debug(f"JWT decode failed: {e}")
        return None


def extract_token(authorization_header: Optional[str]) -> Optional[dict]:
    """Parse 'Bearer <token>' header → decoded payload or None."""
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None
    token = authorization_header[7:]
    return decode_token(token)
