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

#ai_service = OllamaService()

router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


@router.post("/suggest_subreddits")
async def find_subreddit(post_data: RedditPostModel, access_token: str = Depends(get_reddit_access_token), _ : bool = Depends(role_checker)):
    prompt = create_subreddit_suggestion_prompt(post_data.title, post_data.body)
    return StreamingResponse(
        stream_openrouter_response(prompt),
        media_type="text/event-stream"
    )

@router.post("/format_post")
async def format_post(subreddit: str, _: bool = Depends(role_checker)):
    pass