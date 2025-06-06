from fastapi import APIRouter, Request
from fastapi import Depends, status
from fastapi.responses import JSONResponse
from services.auth.user_service import UserService
from services.auth.dependencies import RoleChecker
from models.pydantic.reddit import RedditPostModel, RedditPostFormatForSubredditModel
from starlette.responses import StreamingResponse
#from services.ai.ollama.ollama_service import OllamaService
from services.ai.utils import (
    stream_subreddits_suggestion_and_rules_formatted,
    stream_openrouter_response,
)
from services.ai.prompts import (
    create_subreddit_suggestion_prompt,
    create_format_post_for_subreddit_prompt,
)
from services.reddit.utils import get_subreddit_rules, subreddit_exists
from api.utils import limiter
import re
from fastapi import HTTPException


#ai_service = OllamaService()

router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


@router.post("/suggest_subreddits")
@limiter.limit("1/second")
async def find_subreddit(request: Request, post_data: RedditPostModel, _ : bool = Depends(role_checker)):
    prompt = create_subreddit_suggestion_prompt(post_data.post)

    return StreamingResponse(
        stream_subreddits_suggestion_and_rules_formatted(prompt),
        media_type="text/event-stream"
    )

@router.post("/format_post")
@limiter.limit("1/second")
async def format_post(request: Request, data: RedditPostFormatForSubredditModel, _ : bool = Depends(role_checker)):
    subreddit = data.subreddit_name.strip().strip("r/")
    if not data.subreddit_rules:
        print(subreddit)
        if subreddit or await subreddit_exists(subreddit):
            data.subreddit_rules = await get_subreddit_rules(subreddit)
        else:
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subreddit not found")
        
    if not data.subreddit_rules:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subreddit has no rules")
    prompt = create_format_post_for_subreddit_prompt(data.post, data.subreddit_name, data.subreddit_rules)

    return StreamingResponse(
        stream_openrouter_response(prompt),
        media_type="text/event-stream"
    )