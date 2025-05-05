from fastapi import FastAPI
from api.endpoints import reddit_analyzer, auth
from database.db import init_db
from contextlib import asynccontextmanager
from services.errors.main_errors import register_all_errors
from middleware.main_middleware import setup_middlewares


VERSION = "1.0"

@asynccontextmanager
async def life_span(app: FastAPI):
    print("Starting up ...")
    await init_db()
    yield
    print("Server has been shut down")


app = FastAPI(
    title="SubRMatch",
    description="Find and format Reddit posts",
    version="1.0.0",
)

register_all_errors(app)
setup_middlewares(app)

# Adding routers
#app.include_router(reddit_analyzer.router, prefix=f"/api/{VERSION}")
app.include_router(auth.auth_router, prefix=f"/api/{VERSION}/auth")