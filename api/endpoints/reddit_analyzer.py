from fastapi import APIRouter
from fastapi import Depends
from services.reddit.utils import get_reddit_access_token, get_subreddit_rules
from services.auth.user_service import UserService
from services.auth.dependencies import RoleChecker
from fastapi.responses import JSONResponse
from services.reddit.utils import get_reddit_access_token, get_subreddit_rules
from models.pydantic.reddit import RedditPostModel
from starlette.responses import StreamingResponse
#from services.ai.ollama.ollama_service import OllamaService
from services.ai.utils import stream_openrouter_response, create_subreddit_suggestion_prompt
import json
from typing import AsyncGenerator
from core.config import settings

#ai_service = OllamaService()

router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


@router.post("/suggest_subreddits")
async def find_subreddit(post_data: RedditPostModel, access_token: str = Depends(get_reddit_access_token), _ : bool = Depends(role_checker)):
    prompt = create_subreddit_suggestion_prompt(post_data.title, post_data.body)
    
    async def process_stream() -> AsyncGenerator[str, None]:
        subreddits = []
        async for chunk in stream_openrouter_response(prompt):
            if chunk.startswith("data: {\"subreddits\":"):
                # Извлекаем список сабреддитов из финального чанка
                subreddits = json.loads(chunk[6:])["subreddits"]
            else:
                yield chunk

    return StreamingResponse(
        process_stream(),
        media_type="text/event-stream"
    )

@router.post("/format_post")
async def format_post():
    print(settings.REDDIT_BASE_URL)
    token = await get_reddit_access_token()
    print(token)
    return await get_subreddit_rules("marketing", token)