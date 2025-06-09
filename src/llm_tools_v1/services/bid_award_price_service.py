from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
from llm_tools_v1.db.models import BidAwardPrice, Bidding, BiddingPackage
from sqlalchemy import join

class BidAwardPriceCreate(BaseModel):
    """
    中标价格创建参数 Schema
    """
    bidding_no: str
    subject: str
    package_name: str
    candidate: str
    price_type: str
    price_value: Optional[float] = None
    price_percent: Optional[float] = None
    remark: Optional[str] = None
    url: str  # 新增字段，用于保存中标公告页面 URL

class BidAwardPriceInfo(BaseModel):
    """
    中标公示详细信息返回模型
    """
    bidding_no: str  # 招标编号
    project: Optional[str] = None  # 项目名称
    subject: str  # 标的名称
    package_name: str  # 标包名称
    price_type: str  # 价格类型
    price_value: Optional[float] = None  # 价格数值
    price_percent: Optional[float] = None  # 价格百分比
    estimated_amount: Optional[float] = None  # 招标价格
    max_bid_amount: Optional[float] = None  # 最高限价
    owner: Optional[str] = None  # 招标单位
    award_url: Optional[str] = None  # 中标公告页面 URL
    bidding_url: Optional[str] = None  # 招标公告页面 URL

class BidAwardPriceService:
    """
    中标价格（BidAwardPrice）业务服务层，负责插入、查询、删除等操作
    """
    @staticmethod
    async def create_price(data: BidAwardPriceCreate, db: AsyncSession) -> BidAwardPrice:
        """
        插入一条中标价格记录
        :param data: 中标价格 Pydantic schema
        :param db: 异步数据库会话
        :return: 新建的 BidAwardPrice 对象
        :raises: IntegrityError 唯一约束冲突等
        """
        price = BidAwardPrice(**data.model_dump())
        db.add(price)
        try:
            await db.commit()
            await db.refresh(price)
            return price
        except IntegrityError as e:
            await db.rollback()
            raise e

    @staticmethod
    async def get_price_by_bidding_no_and_package(
        bidding_no: str, package_name: str, db: AsyncSession
    ) -> Optional[BidAwardPrice]:
        """
        查询指定公告编号和标包名称的中标价格记录
        :param bidding_no: 公告编号
        :param package_name: 标包名称
        :param db: 异步数据库会话
        :return: BidAwardPrice 或 None
        """
        stmt = select(BidAwardPrice).where(
            BidAwardPrice.bidding_no == bidding_no,
            BidAwardPrice.package_name == package_name
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_by_bidding_no(bidding_no: str, db: AsyncSession) -> int:
        """
        删除指定公告编号的所有中标价格记录
        :param bidding_no: 公告编号
        :param db: 异步数据库会话
        :return: 删除的记录数
        """
        stmt = delete(BidAwardPrice).where(BidAwardPrice.bidding_no == bidding_no)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def create_multi_prices(data_list: List[BidAwardPriceCreate], db: AsyncSession) -> List[BidAwardPrice]:
        """
        批量插入中标价格记录（不 commit，由外部统一 commit）
        :param data_list: 中标价格 Pydantic schema 列表
        :param db: 异步数据库会话
        :return: 新建的 BidAwardPrice 对象列表
        """
        prices = []
        for data in data_list:
            price = BidAwardPrice(**data.model_dump())
            db.add(price)
            prices.append(price)
        await db.flush()
        return prices

    @staticmethod
    async def list_award_price_infos(db: AsyncSession, owner: str = None) -> List[BidAwardPriceInfo]:
        """
        查询所有中标公示详细信息，可按招标单位过滤
        :param db: 异步数据库会话
        :param owner: 招标单位名称（可选）
        :return: BidAwardPriceInfo 列表
        """
        j1 = join(
            BidAwardPrice, Bidding, BidAwardPrice.bidding_no == Bidding.bidding_no, isouter=True
        )
        j2 = join(
            j1,
            BiddingPackage,
            (BiddingPackage.bidding_id == Bidding.id) &
            (BiddingPackage.subject == BidAwardPrice.subject) &
            (BiddingPackage.package_name == BidAwardPrice.package_name),
            isouter=True
        )
        stmt = select(
            BidAwardPrice.bidding_no,
            Bidding.project,
            BidAwardPrice.subject,
            BidAwardPrice.package_name,
            BidAwardPrice.price_type,
            BidAwardPrice.price_value,
            BidAwardPrice.price_percent,
            BiddingPackage.estimated_amount,
            BiddingPackage.max_bid_amount,
            Bidding.owner,
            BidAwardPrice.url.label("award_url"),
            Bidding.url.label("bidding_url")
        ).select_from(j2)
        if owner:
            stmt = stmt.where(Bidding.owner.contains(owner))
        result = await db.execute(stmt)
        rows = result.all()
        return [
            BidAwardPriceInfo(
                bidding_no=row.bidding_no,
                project=row.project,
                subject=row.subject,
                package_name=row.package_name,
                price_type=row.price_type,
                price_value=row.price_value,
                price_percent=row.price_percent,
                estimated_amount=row.estimated_amount,
                max_bid_amount=row.max_bid_amount,
                owner=row.owner,
                award_url=row.award_url,
                bidding_url=row.bidding_url
            ) for row in rows
        ] 