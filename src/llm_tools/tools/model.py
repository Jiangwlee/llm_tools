from pydantic import BaseModel, Field


# Define the schema for the bidding notice
class BiddingNoticeInfo(BaseModel):
    project: str = Field(..., description="项目名称")
    project_code: str = Field(..., description="项目编号")
    bid_inviter: str = Field(..., description="招标人")