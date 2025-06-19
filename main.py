from fastapi import FastAPI
from api.endpoints import reddit_analyzer, auth
from database.db import init_db
from contextlib import asynccontextmanager
from services.errors.main_errors import register_all_errors
from middleware.main_middleware import setup_middlewares
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.utils import limiter
from services.reddit.utils import reddit

VERSION = "1.0"

@asynccontextmanager
async def life_span(app: FastAPI):
    yield
    await reddit.close()



app = FastAPI(
    title="SubRMatch",
    description="Find and format Reddit posts",
    version="1.0.0",
    lifespan=life_span,
)

templates = Jinja2Templates(directory="templates")

register_all_errors(app)
setup_middlewares(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Adding routers
app.include_router(reddit_analyzer.router, prefix=f"/api/{VERSION}/reddit_analyzer")
app.include_router(auth.auth_router, prefix=f"/api/{VERSION}/auth")