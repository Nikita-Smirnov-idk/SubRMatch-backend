from typing import Any, List

from fastapi import Depends, Request, status
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from database.db import get_session
from models.db.users import User
from database.redis import token_in_storage

from services.auth.user_service import user_service
from .utils.token_utils import decode_token
from services.errors.permission_errors import (
    InvalidToken,
    RefreshTokenRequired,
    AccessTokenRequired,
    InsufficientPermission,
    AccountNotVerified,
    UserNotFound,
)
import uuid


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request, session: AsyncSession = Depends(get_session)) -> HTTPAuthorizationCredentials | None:
        creds = await super().__call__(request)

        token = creds.credentials

        token_data = decode_token(token)

        if token_data is None:
            raise InvalidToken()
        
        self.verify_token_data(token_data)

        user = await user_service.get_user_by_email(token_data['user']['email'], session)

        if user is None:
            raise UserNotFound()
        
        await self.check_token_in_blocklist(token_data, user.uid)

        return token_data

    def verify_token_data(self, token_data):
        raise NotImplementedError("Please Override this method in child classes")
    
    def check_token_in_blocklist(self, token_data: str, uid: uuid.UUID) -> None:
        raise NotImplementedError("Please Override this method in child classes")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data["refresh"]:
            raise AccessTokenRequired()
        
    async def check_token_in_blocklist(self, token_data: dict, uid: uuid.UUID) -> None:
        name = f"{uid}:access:{token_data['jti']}"

        if not await token_in_storage(name):
            raise InvalidToken()


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data["refresh"]:
            raise RefreshTokenRequired()
        
    async def check_token_in_blocklist(self, token_data: dict, uid: uuid.UUID) -> None:
        name = f"{uid}:refresh:{token_data['jti']}"

        if not await token_in_storage(name):
            raise InvalidToken()


async def get_current_user(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_email = token_details["user"]["email"]

    user = await user_service.get_user_by_email(user_email, session)

    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> Any:
        if not current_user.is_verified:
            raise AccountNotVerified()
        if current_user.role in self.allowed_roles:
            return True

        raise InsufficientPermission()