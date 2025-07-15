from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from llm_tools_v1.core.config import LlmToolsDirs
from llm_tools_v1.core.logging import get_logger
from llm_tools_v1.services.biddingcsg_service import (
    BiddingCSGService,
    BiddingSearchParams,
    BiddingSearchResponse,
    BiddingUrl,
)
from llm_tools_v1.api.v1.schema import ResponseBase, SuccessResponse

logger = get_logger()

router = APIRouter(prefix="/biddingcsg", tags=["biddingcsg"])


def get_latest_summary_file() -> Optional[Path]:
    """
    获取最新的标讯总结文件
    """
    cache_dir = LlmToolsDirs.get_cache_dir()
    summary_files = list(cache_dir.glob("bidding_info_*.md"))

    if not summary_files:
        return None

    # 按文件名排序，获取最新的文件
    latest_file = max(summary_files, key=lambda x: x.name)
    return latest_file


def get_summary_by_date(date: str) -> Optional[Path]:
    """
    根据日期获取标讯总结文件
    """
    cache_dir = LlmToolsDirs.get_cache_dir()
    summary_file = cache_dir / f"bidding_info_{date}.md"

    if summary_file.exists():
        return summary_file
    return None


@router.get(
    "/{date}",
    summary="获取指定日期的标讯总结",
    response_class=PlainTextResponse,
    response_description="返回指定日期的标讯总结内容",
    responses={
        200: {
            "description": "成功返回标讯总结内容",
            "content": {
                "text/plain": {"example": "# 标讯总结\n\n## 项目1\n招标编号：XXX\n..."}
            },
        },
        404: {"description": "指定日期的标讯总结不存在"},
    },
)
async def get_bidding_summary(
    date: str,
    fallback_to_latest: bool = Query(
        True, description="如果指定日期的总结不存在，是否返回最新的总结"
    ),
) -> ResponseBase:
    """
    获取指定日期的标讯总结

    - **date**: 日期格式为 YYYY-MM-DD，例如 2024-01-15
    - **fallback_to_latest**: 如果指定日期的总结不存在，是否返回最新的总结（默认True）

    返回标讯总结的markdown格式内容
    """
    try:
        # 验证日期格式
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式"
        )

    # 尝试获取指定日期的总结
    summary_file = get_summary_by_date(date)

    if summary_file:
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"成功获取 {date} 的标讯总结")
            return SuccessResponse(data={
                "markdown": content,
                "date": date,
            })
        except Exception as e:
            logger.error(f"读取标讯总结文件失败: {e}")
            raise HTTPException(status_code=500, detail="读取标讯总结文件失败")

    # 如果指定日期的总结不存在，且允许回退到最新总结
    if fallback_to_latest:
        latest_file = get_latest_summary_file()
        if latest_file:
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    content = f.read()
                # 从文件名提取日期
                file_date = latest_file.stem.replace("bidding_info_", "")
                logger.info(f"指定日期 {date} 的总结不存在，返回最新总结 {file_date}")
                return SuccessResponse(data={
                    "markdown": content,
                    "date": file_date,
                })
            except Exception as e:
                logger.error(f"读取最新标讯总结文件失败: {e}")
                raise HTTPException(status_code=500, detail="读取最新标讯总结文件失败")

    # 如果都不存在
    raise HTTPException(
        status_code=404, detail=f"未找到 {date} 的标讯总结，且没有可用的最新总结"
    )


@router.get(
    "/",
    summary="获取最新的标讯总结",
    response_class=PlainTextResponse,
    response_description="返回最新的标讯总结内容",
    responses={
        200: {
            "description": "成功返回最新标讯总结内容",
            "content": {
                "text/plain": {"example": "# 标讯总结\n\n## 项目1\n招标编号：XXX\n..."}
            },
        },
        404: {"description": "没有找到任何标讯总结文件"},
    },
)
async def get_latest_bidding_summary() -> ResponseBase:
    """
    获取最新的标讯总结

    返回最新的标讯总结的markdown格式内容
    """
    latest_file = get_latest_summary_file()

    if not latest_file:
        raise HTTPException(status_code=404, detail="没有找到任何标讯总结文件")

    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()
        # 从文件名提取日期
        file_date = latest_file.stem.replace("bidding_info_", "")
        logger.info(f"成功获取最新标讯总结 {file_date}")
        return SuccessResponse(data={
            "markdown": content,
            "date": file_date,
        })
    except Exception as e:
        logger.error(f"读取最新标讯总结文件失败: {e}")
        raise HTTPException(status_code=500, detail="读取标讯总结文件失败")


@router.post("/search", response_model=BiddingSearchResponse)
async def search_bidding_notices(
    search_params: BiddingSearchParams,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: BiddingCSGService = Depends(BiddingCSGService),
) -> BiddingSearchResponse:
    """
    搜索招标公告
    """
    try:
        return await service.search_notices(search_params, page, page_size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notice_id}", response_model=BiddingUrl)
async def get_bidding_notice(
    notice_id: str, service: BiddingCSGService = Depends(BiddingCSGService)
) -> BiddingUrl:
    """
    获取单个招标公告详情
    """
    try:
        notice = await service.get_notice(notice_id)
        if not notice:
            raise HTTPException(status_code=404, detail="公告不存在")
        return notice
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
