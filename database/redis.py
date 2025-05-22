import redis.asyncio as aioredis

from core.config import settings
from datetime import datetime, timezone
import json
import time

redis = aioredis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True,
)

async def add_token_to_storage(name: str, exp_time: int, value: str = "") -> None:
    await redis.setex(name, exp_time, value)

async def get_token_from_storage(name: str) -> str:
    return await redis.get(name)

async def add_email_verification_cooldown(email: str) -> None:
    await redis.setex(
        f"email_verification:{email}",
        settings.MAIL_VERIFICATION_COOLDOWN,
        json.dumps(
            {
                "time": time.time()
            }
        )
    )

async def add_password_reset_email_cooldown(email: str) -> None:
    await redis.setex(
        f"password_reset_email:{email}",
        settings.MAIL_VERIFICATION_COOLDOWN,
        json.dumps(
            {
                "time": time.time()
            }
        )
    )

async def save_jwt_tokens_with_state(state: str, value: str) -> None:
    await redis.setex(
        f"tokens:{state}",
        300,
        value
    )

async def delete_from_storage(name: str) -> None:
    await redis.delete(name)


async def revoke_user_tokens(user_id: str):
    # Находим все ключи токенов пользователя
    access_keys = await redis.keys(f"{user_id}:access:*")
    refresh_keys = await redis.keys(f"{user_id}:refresh:*")
    mapping_keys = await redis.keys(f"{user_id}:refresh_to_access:*")
    
    # Удаляем все токены
    for key in access_keys + refresh_keys + mapping_keys:
        await redis.delete(key)

async def token_in_storage(name: str) -> bool:
    return True if await redis.exists(name) else False