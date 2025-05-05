from datetime import timedelta, datetime
import jwt
from core.config import settings
import uuid
import logging
from database.redis import add_token_to_blocklist


async def create_token(user_data: dict, jti: str, refresh: bool = False) -> str:
    payload = {}
    
    payload['user'] = user_data
    payload['exp'] = datetime.now() + (timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) if refresh else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload['jti'] = jti
    payload['refresh'] = refresh
    
    token = jwt.encode(
        payload=payload,
        key=settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    exp_time = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 if not refresh else settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    name = f"session:{jti}:refresh" if refresh else f"session:{jti}:access"

    await add_token_to_blocklist(name, exp_time, token)

    return token

async def create_both_jwt_tokens(user_data: dict) -> tuple[str, str]:
    jti = str(uuid.uuid4())

    access_token = await create_token(
        user_data=user_data,
        jti=jti,
    )

    refresh_token = await create_token(
        user_data=user_data,
        refresh=True,
        jti=jti,
    )
    return access_token, refresh_token

def decode_token(token: str) -> dict | None:
    try: 
        token_data = jwt.decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_data['token'] = token

        return token_data

    except jwt.PyJWTError as ex:
        logging.exception(ex)
        return None