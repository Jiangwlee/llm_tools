from typing import Optional
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlmodel import select
from src.llm_tools_v1.db.models import Bidding, BiddingPackage

class BiddingCreate(BaseModel):
    """
    招标公告创建参数 Schema
    """
    bidding_no: str
    url: str
    owner: Optional[str] = None
    agent: Optional[str] = None
    project: Optional[str] = None
    description: Optional[str] = None
    doc_start_time: Optional[str] = None
    doc_end_time: Optional[str] = None
    submit_deadline: Optional[str] = None
    open_time: Optional[str] = None
    open_location: Optional[str] = None

class BiddingPackageCreate(BaseModel):
    """
    标包创建参数 Schema
    """
    bidding_id: Optional[int] = None
    subject: Optional[str] = None
    package_name: Optional[str] = None
    subject_desc: Optional[str] = None
    estimated_amount: Optional[float] = None
    max_bid_amount: Optional[float] = None

class BiddingService:
    """
    招标公告（Bidding）业务服务层，负责插入和删除操作
    """
    @staticmethod
    async def create_bidding(data: BiddingCreate, db: AsyncSession) -> Bidding:
        """
        插入一条招标公告记录
        :param data: 招标公告 Pydantic schema
        :param db: 异步数据库会话
        :return: 新建的 Bidding 对象
        :raises: IntegrityError 唯一约束冲突等
        """
        bidding = Bidding(**data.model_dump())
        db.add(bidding)
        try:
            await db.commit()
            await db.refresh(bidding)
            return bidding
        except IntegrityError as e:
            await db.rollback()
            raise e

    @staticmethod
    async def delete_bidding(bidding_id: int, db: AsyncSession) -> bool:
        """
        删除指定 ID 的招标公告（级联删除标包）
        :param bidding_id: 招标公告主键
        :param db: 异步数据库会话
        :return: 删除成功返回 True，未找到返回 False
        """
        result = await db.execute(select(Bidding).where(Bidding.id == bidding_id))
        bidding = result.scalar_one_or_none()
        if not bidding:
            return False
        await db.delete(bidding)
        await db.commit()
        return True
    
    @staticmethod
    async def get_bidding_by_date(date: str, db: AsyncSession) -> list[Bidding]:
        """
        根据日期获取招标公告
        :param date: 日期（YYYY-MM-DD）
        :param db: 异步数据库会话
        :return: 招标公告列表
        """
        result = await db.execute(
            select(Bidding).where(func.date(Bidding.created_at) == date)
        )
        return result.scalars().all()

class BiddingPackageService:
    """
    标包（BiddingPackage）业务服务层，负责插入和删除操作
    """
    @staticmethod
    async def create_package(data: BiddingPackageCreate, db: AsyncSession) -> BiddingPackage:
        """
        插入一条标包记录
        :param data: 标包 Pydantic schema
        :param db: 异步数据库会话
        :return: 新建的 BiddingPackage 对象
        :raises: IntegrityError 外键/唯一约束冲突等
        """
        package = BiddingPackage(**data.model_dump())
        db.add(package)
        try:
            await db.commit()
            await db.refresh(package)
            return package
        except IntegrityError as e:
            await db.rollback()
            raise e

    @staticmethod
    async def delete_package(package_id: int, db: AsyncSession) -> bool:
        """
        删除指定 ID 的标包
        :param package_id: 标包主键
        :param db: 异步数据库会话
        :return: 删除成功返回 True，未找到返回 False
        """
        result = await db.execute(select(BiddingPackage).where(BiddingPackage.id == package_id))
        package = result.scalar_one_or_none()
        if not package:
            return False
        await db.delete(package)
        await db.commit()
        return True

    @staticmethod
    async def create_multi_packages(data_list: list["BiddingPackageCreate"], db: AsyncSession) -> list[BiddingPackage]:
        """
        批量插入标包记录（不 commit，由外部统一 commit）
        :param data_list: 标包 Pydantic schema 列表
        :param db: 异步数据库会话
        :return: 新建的 BiddingPackage 对象列表
        """
        packages = []
        for data in data_list:
            package = BiddingPackage(**data.model_dump())
            db.add(package)
            packages.append(package)
        await db.flush()  # 确保主键 id 可用
        return packages 
    
    @staticmethod
    async def get_bidding_package_by_bidding_id(bidding_id: int, db: AsyncSession) -> list[BiddingPackage]:
        """
        根据招标公告 ID 获取标包列表
        :param bidding_id: 招标公告主键
        :param db: 异步数据库会话
        :return: 标包列表
        """
        result = await db.execute(select(BiddingPackage).where(BiddingPackage.bidding_id == bidding_id))
        return result.scalars().all()