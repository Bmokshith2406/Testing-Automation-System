from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logging import logger

# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

MAX_BCRYPT_BYTES = 72

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# ---------------------------------------------------------------------
# Internal safety
# ---------------------------------------------------------------------

def _safe_password(password: str) -> str:
    """
    Ensure all passwords:
    - Encode safely
    - Are truncated to bcrypt's byte limit
    - Never crash hashing or verification
    """
    try:
        pw_bytes = password.encode("utf-8")
    except Exception:
        logger.error("Password encoding failure", exc_info=True)
        pw_bytes = str(password).encode("utf-8", errors="ignore")

    if len(pw_bytes) > MAX_BCRYPT_BYTES:
        logger.warning("Password >72 bytes detected — truncating safely")
        pw_bytes = pw_bytes[:MAX_BCRYPT_BYTES]

    return pw_bytes.decode("utf-8", errors="ignore")

# ---------------------------------------------------------------------
# Password utils
# ---------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash a password safely using bcrypt.

    Guaranteed to:
    - Not exceed bcrypt byte limits
    - Fail loudly but gracefully if bcrypt breaks
    """
    try:
        safe_password = _safe_password(password)
        return pwd_context.hash(safe_password)
    except Exception:
        logger.critical(
            "CRITICAL: bcrypt hashing failure",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Password hashing service unavailable"
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password safely & crash-free.
    """
    try:
        safe_password = _safe_password(plain_password)
        return pwd_context.verify(safe_password, hashed_password)
    except Exception:
        logger.error("bcrypt verification failure", exc_info=True)
        return False

# ---------------------------------------------------------------------
# JWT utils
# ---------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:

    try:
        to_encode = data.copy()
    except Exception:
        to_encode = {}

    try:
        expire = datetime.utcnow() + (
            expires_delta or timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    except Exception:
        expire = datetime.utcnow()

    to_encode.update({"exp": expire})

    try:
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
    except Exception:
        logger.exception("JWT encoding failure")
        raise HTTPException(
            status_code=500,
            detail="Token generation failed",
        )


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception:
        logger.exception("Unexpected JWT decode failure")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ---------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> dict:

    try:
        payload = decode_token(token)
    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    try:
        user_id = payload.get("sub")
    except Exception:
        user_id = None

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )

    return {
        "id": user_id,
        "username": payload.get("username"),
        "role": payload.get("role", "viewer"),
    }


def require_role(*allowed_roles: str):

    async def _checker(
        current_user: dict = Depends(get_current_user)
    ):
        try:
            if current_user["role"] not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid role permissions"
            )

        return current_user

    return _checker
