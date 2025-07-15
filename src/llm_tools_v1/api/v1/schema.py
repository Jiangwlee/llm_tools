from typing import Any, Optional
from pydantic import BaseModel


class ResponseBase(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class SuccessResponse(ResponseBase):
    code: int = 200
    message: str = "success"

class ErrorResponse(ResponseBase):
    code: int = 500
    message: str = "error"
