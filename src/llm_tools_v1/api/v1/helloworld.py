from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from fastapi.openapi.models import Response as OpenAPIResponse

router = APIRouter()

@router.get(
    "/helloworld",
    summary="Hello World 示例接口",
    response_class=PlainTextResponse,
    response_description="返回 hello world 字符串",
    responses={
        200: {
            "description": "成功返回 hello world 字符串",
            "content": {
                "text/plain": {
                    "example": "hello world"
                }
            }
        }
    }
)
async def helloworld():
    """
    返回 hello world 字符串
    - **返回**: 纯文本 "hello world"
    """
    return "hello world" 