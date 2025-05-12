import httpx
from core.config import settings
from typing import Dict


async def get_reddit_access_token() -> str:
    async with httpx.AsyncClient() as client:
        response = client.post(
            settings.REDDIT_BASE_URL + "access_token",
            auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": settings.REDDIT_USER_AGENT}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    

async def get_subreddit_rules(subreddit: str, token: str) -> Dict:
    async with httpx.AsyncClient() as client:
        response = client.post(
            settings.REDDIT_BASE_URL + f"{subreddit}/about/rules",
            headers={"Authorization": f"Bearer {token}", "User-Agent": settings.REDDIT_USER_AGENT}
        )
        if response.status_code != 200:
            return {"error": f"Failed to get rules for r/{subreddit}"}
        return response.json()