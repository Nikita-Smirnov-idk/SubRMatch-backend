from datetime import timedelta, datetime, timezone
import jwt
from core.config import settings
import uuid
import logging
from database.redis import add_token_to_storage, get_token_from_storage
from services.errors.permission_errors import InvalidToken
from sqlmodel.ext.asyncio.session import AsyncSession
from database.db import get_session
from fastapi import Depends
from services.auth.user_service import user_service


async def create_token(uid: uuid.UUID, user_data: dict, refresh: bool = False) -> tuple[str, str]:
    payload = {}

    jti = str(uuid.uuid4())
    
    payload['user'] = user_data
    payload['exp'] = datetime.now(timezone.utc) + (timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) if refresh else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload['jti'] = jti
    payload['refresh'] = refresh
    
    token = jwt.encode(
        payload=payload,
        key=settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    token_data = jwt.decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
    )

    exp_time = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 if not refresh else settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    name = f"{uid}:refresh:{jti}" if refresh else f"{uid}:access:{jti}"

    await add_token_to_storage(name, exp_time, token)

    return token, jti

async def create_both_jwt_tokens(user_data: dict, session: AsyncSession) -> tuple[str, str]:
    user = await user_service.get_user_by_email(user_data['email'], session)

    access_token, access_jti = await create_token(
        uid=user.uid,
        user_data=user_data,
    )

    refresh_token, refresh_jti = await create_token(
        uid=user.uid,
        user_data=user_data,
        refresh=True,
    )

    await add_token_to_storage(f"{user.uid}:refresh_to_access:{refresh_jti}", 
                           settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, 
                           str(access_jti))

    return access_token, refresh_token

def decode_token(token: str) -> dict | None:
    try: 
        token_data = jwt.decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        return token_data

    except jwt.PyJWTError as ex:
        logging.exception(ex)
        return None