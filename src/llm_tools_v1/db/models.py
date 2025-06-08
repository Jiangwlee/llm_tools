from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

class Bidding(SQLModel, table=True):
    """
    招标公告主表
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="主键")
    bidding_no: str = Field(index=True, unique=True, nullable=False, description="招标编号，唯一")
    url: str = Field(nullable=False, description="招标公告来源URL")
    owner: Optional[str] = Field(default=None, description="招标人")
    agent: Optional[str] = Field(default=None, description="招标代理机构")
    project: Optional[str] = Field(default=None, description="招标项目")
    description: Optional[str] = Field(default=None, description="项目概述")
    doc_start_time: Optional[str] = Field(default=None, description="招标文件获取开始时间")
    doc_end_time: Optional[str] = Field(default=None, description="招标文件获取结束时间")
    submit_deadline: Optional[str] = Field(default=None, description="投标文件递交截止时间")
    open_time: Optional[str] = Field(default=None, description="开标时间")
    open_location: Optional[str] = Field(default=None, description="开标地点")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="数据创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="数据最后修改时间")
    packages: List["BiddingPackage"] = Relationship(back_populates="bidding", cascade_delete=True)

class BiddingPackage(SQLModel, table=True):
    """
    标包信息表
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="主键")
    bidding_id: Optional[int] = Field(default=None, foreign_key="bidding.id", ondelete="CASCADE", description="关联招标公告ID")
    subject: Optional[str] = Field(default=None, description="标的")
    package_name: Optional[str] = Field(default=None, description="标包")
    subject_desc: Optional[str] = Field(default=None, description="标的概述")
    estimated_amount: Optional[float] = Field(default=None, description="预计采购金额")
    max_bid_amount: Optional[float] = Field(default=None, description="最高投标限价")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="数据创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="数据最后修改时间")
    bidding: Optional[Bidding] = Relationship(back_populates="packages") 