from fastapi import APIRouter
from fastapi import Depends
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


#ai_service = OllamaService()

router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


@router.post("/suggest_subreddits")
async def find_subreddit(post_data: RedditPostModel, _ : bool = Depends(role_checker)):
    prompt = create_subreddit_suggestion_prompt(post_data.post)

    return StreamingResponse(
        stream_subreddits_suggestion_and_rules_formatted(prompt),
        media_type="text/event-stream"
    )

@router.post("/format_post")
async def format_post(data: RedditPostFormatForSubredditModel, _ : bool = Depends(role_checker)):
    prompt = create_format_post_for_subreddit_prompt(data.post, data.subreddit_name, data.subreddit_rules)

    return StreamingResponse(
        stream_openrouter_response(prompt),
        media_type="text/event-stream"
    )