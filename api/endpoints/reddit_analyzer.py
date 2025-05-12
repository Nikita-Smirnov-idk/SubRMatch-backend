from fastapi import APIRouter
from fastapi import Depends
from services.reddit.utils import get_reddit_access_token, get_subreddit_rules
from services.auth.user_service import UserService
from services.auth.dependencies import RoleChecker
from fastapi.responses import JSONResponse
from services.ai.utils import get_suggested_subreddits
from services.reddit.utils import get_reddit_access_token, get_subreddit_rules
from models.pydantic.reddit import RedditPostModel

router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(["admin", "user"])


@router.post("/suggest_subreddits")
async def find_subreddit(post_data: RedditPostModel, acces_token: str = Depends(get_reddit_access_token), _ : bool = Depends(role_checker)):
    reponse = await get_suggested_subreddits(post_data.title, post_data.body)
    
    return JSONResponse(
        status_code=200,
    )

@router.post("/format_post")
async def format_post(subreddit: str, _: bool = Depends(role_checker)):
    pass