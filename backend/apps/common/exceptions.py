import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    response = exception_handler(exc, context)

    if response is not None:
        detail = exc.detail if hasattr(exc, "detail") else str(exc)
        if isinstance(detail, dict):
            message = detail
        elif isinstance(detail, list):
            message = detail
        else:
            message = str(detail)

        response.data = {
            "success": False,
            "error": {
                "code": type(exc).__name__,
                "message": message,
                "status_code": response.status_code,
            },
        }
    else:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        response = Response(
            {
                "success": False,
                "error": {
                    "code": "InternalServerError",
                    "message": "服务器内部错误",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
