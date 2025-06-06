import httpx
from core.config import settings
from typing import Dict, List
import asyncpraw
import json
import logging
from asyncprawcore.exceptions import Forbidden


reddit = asyncpraw.Reddit(
    client_id=settings.REDDIT_CLIENT_ID,
    client_secret=settings.REDDIT_CLIENT_SECRET,
    user_agent=settings.REDDIT_USER_AGENT,
)


async def subreddit_exists(subreddit_name: str) -> bool:
    try:
        await reddit.subreddit(subreddit_name)
        return True
    except Exception as e:
        logging.error(e)
        return False


async def get_subreddit_rules(subreddit_name: str):
    """
    Получает правила для списка сабреддитов.
    Args:
        subreddit_name: название сабреддита.
    Returns:
        JSON-объект с правилами для сабреддита.
    """
    
    try:
        subreddit = await reddit.subreddit(subreddit_name)
        subreddit_rules = []

        async for rule in subreddit.rules:
            subreddit_rules.append(rule)

        rule_list = [
            {
                "rule_number": idx + 1,
                "short_name": rule.short_name,
                "description": rule.description,
            }
            for idx, rule in enumerate(subreddit_rules)
        ]
        await subreddit.load()
        
        return json.dumps({
            "name": subreddit_name,
            "subscribers": subreddit.subscribers,
            "status": "success",
            "rules": rule_list
        })
        
    except Exception as e:
        logging.error(e)
        return json.dumps({
            "name": subreddit_name,
            "status": "failed",
        })

# async def get_reddit_access_token() -> str:
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             settings.REDDIT_BASE_URL + "api/v1/access_token",
#             auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
#             data={"grant_type": "client_credentials"},
#             headers={"User-Agent": settings.REDDIT_USER_AGENT}
#         )
#         response.raise_for_status()
#         return response.json()["access_token"]

# async def get_subreddit_rules(subreddit: str, token: str) -> Dict:
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             settings.REDDIT_BASE_URL + f"r/{subreddit}/about/rules",
#             headers={"Authorization": f"Bearer {token}", "User-Agent": settings.REDDIT_USER_AGENT}
#         )
#         if response.status_code != 200:
#             return {"error": f"Failed to get rules for r/{subreddit}"}
#         return response.json()