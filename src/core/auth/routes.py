from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, status

from src.core.auth.jwt import TokenError, create_access_token, decode_access_token
from src.core.auth.password import verify_password
from src.core.auth.user_repository import DuplicateEmailError, UserRepository
from src.core.models.config import AppSettings
from src.core.models.user import TokenResponse, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)


def _user_row_to_response(row: dict) -> UserResponse:  # type: ignore[type-arg]
    return UserResponse(
        id=row["id"],
        email=row["email"],
        tenant_id=row["tenant_id"],
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


def create_auth_router(settings: AppSettings, user_repo: UserRepository) -> APIRouter:
    """Create the /api/auth router for user registration, login, and profile."""
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    async def register(body: UserCreate) -> TokenResponse:
        try:
            row = await user_repo.create_user(email=body.email, password=body.password)
        except DuplicateEmailError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from None

        token = create_access_token(
            user_id=row["id"],
            tenant_id=row["tenant_id"],
            email=row["email"],
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_expire_minutes,
        )
        return TokenResponse(
            access_token=token,
            user=_user_row_to_response(row),
        )

    @router.post("/login", response_model=TokenResponse)
    async def login(body: UserLogin) -> TokenResponse:
        row = await user_repo.get_by_email(body.email)
        if row is None or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        token = create_access_token(
            user_id=row["id"],
            tenant_id=row["tenant_id"],
            email=row["email"],
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_expire_minutes,
        )
        return TokenResponse(
            access_token=token,
            user=_user_row_to_response(row),
        )

    def _get_current_user_id(authorization: str) -> str:
        """Extract and validate user_id from the Authorization header."""
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        token = authorization[7:].strip()
        try:
            payload = decode_access_token(
                token,
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
            )
        except TokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from None
        return payload["sub"]  # type: ignore[no-any-return]

    @router.get("/me", response_model=UserResponse)
    async def me(
        authorization: str = Header(default=""),
    ) -> UserResponse:
        user_id = _get_current_user_id(authorization)
        row = await user_repo.get_by_id(user_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return _user_row_to_response(row)

    return router
