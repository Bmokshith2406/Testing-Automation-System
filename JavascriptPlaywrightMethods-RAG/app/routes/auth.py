from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.schemas import UserCreate, UserOut, Token
from app.models.users import (
    create_user,
    get_user_by_username,
    authenticate_user,
    user_to_out,
)
from app.core.security import create_access_token
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=UserOut)
async def register_user(payload: UserCreate):
    try:
        try:
            existing = await get_user_by_username(payload.username)
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="User lookup failed",
            ) from err

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already taken",
            )

        try:
            user = await create_user(
                payload.username,
                payload.password,
                payload.role,
            )
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="User creation failed",
            ) from err

        try:
            return user_to_out(user)
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="User response formatting failed",
            ) from err

    except HTTPException:
        raise

    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail="Unexpected registration error",
        ) from err


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):

    try:
        try:
            user = await authenticate_user(
                form_data.username,
                form_data.password,
            )
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="Authentication service failure",
            ) from err

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        try:
            token_data = {
                "sub": str(user["_id"]),
                "username": user["username"],
                "role": user.get("role", "viewer"),
            }
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="User token payload build failed",
            ) from err

        try:
            expires = timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="JWT expiry configuration invalid",
            ) from err

        try:
            access_token = create_access_token(
                data=token_data,
                expires_delta=expires,
            )
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="Token generation failed",
            ) from err

        try:
            return Token(access_token=access_token)
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail="Token response formatting failed",
            ) from err

    except HTTPException:
        raise

    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail="Unexpected login error",
        ) from err
