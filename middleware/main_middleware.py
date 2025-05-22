from fastapi import FastAPI
from .logging_middleware import register_logging_middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from core.config import settings

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]

def setup_middlewares(app: FastAPI) :
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=3600,  # Session expires in 1 hour
    )

    # register here your middlewares ---->

    register_logging_middleware(app)

    # <----

    # Basic Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins = origins,
        allow_credentials=True,
        allow_methods = ["*"],
        allow_headers = ["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts = ["*"],
    )