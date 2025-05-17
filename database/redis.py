import redis.asyncio as aioredis

from core.config import settings
from datetime import datetime, timezone
import json
import time

redis = aioredis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
)

async def add_token_to_blocklist(name: str, exp_time: int, value: str = "") -> None:
    await redis.setex(name, exp_time, value)


async def token_in_blocklist(name: str) -> bool:
    return True if await redis.exists(name) else False

async def add_token_to_blocklist_with_timestamp(name: str, exp_time: int = None) -> None:
    ttl = exp_time - int(datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        await redis.setex(name, ttl, value="")

async def get_token_from_blocklist(name: str) -> str:
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

async def delete_from_blocklist(name: str) -> None:
    await redis.delete(name)