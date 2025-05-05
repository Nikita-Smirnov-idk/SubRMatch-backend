from typing import Any, Callable
from fastapi import Request
from fastapi.responses import JSONResponse

def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:

    async def exception_handler(request: Request, exc: BaseException):

        return JSONResponse(content=initial_detail, status_code=status_code)

    return exception_handler