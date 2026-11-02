from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
  http_exception_handler as _http_exception_handler,
  request_validation_exception_handler as _request_validation_exception_handler
)
from starlette.exceptions import HTTPException
from templating import templates


async def http_exception_handler(request: Request, exception: HTTPException):
  if request.url.path.startswith("/api"):
    return await _http_exception_handler(request, exception)

  message = (
    exception.detail
    if exception.detail
    else "An error occurred. Please check your request and try again."
  )

  return templates.TemplateResponse(
    request,
    "error.html",
    {
      "status_code": exception.status_code,
      "title": exception.status_code,
      "message": message,
    },
    status_code=exception.status_code,
  )


async def request_validation_handler(request: Request, exception: RequestValidationError):
  if request.url.path.startswith("/api"):
    return await _request_validation_exception_handler(request, exception)

  return templates.TemplateResponse(
    request,
    "error.html",
    {
      "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
      "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
      "message": "Invalid request. Please check your input and try again.",
    },
    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
  )
