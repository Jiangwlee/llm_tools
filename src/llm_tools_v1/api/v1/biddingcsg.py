from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from src.llm_tools_v1.services.biddingcsg_service import (
    BiddingCSGService, BiddingSearchParams, BiddingSearchResponse, BiddingUrl
)

router = APIRouter(prefix="/biddingcsg", tags=["biddingcsg"])

@router.post("/search", response_model=BiddingSearchResponse)
async def search_bidding_notices(
    search_params: BiddingSearchParams,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: BiddingCSGService = Depends(BiddingCSGService)
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
    notice_id: str,
    service: BiddingCSGService = Depends(BiddingCSGService)
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