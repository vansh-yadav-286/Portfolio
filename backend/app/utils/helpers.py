from typing import Any

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "Operation successful", status_code: int = status.HTTP_200_OK) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": jsonable_encoder(data)},
    )


def api_error(message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)
