from fastapi import FastAPI
from fastapi.requests import Request
import time
import logging


logging = logging.getLogger('uvicorn.access')
logging.disabled = True


def register_logging_middleware(app: FastAPI) -> None:

    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        process_time = time.time() - start_time

        message = f"{request.client.host}:{request.client.port} - {request.method} - {request.url.path} - completed after {process_time}"

        print(message)

        return response
        