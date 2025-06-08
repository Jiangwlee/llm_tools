from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
from src.llm_tools_v1.db.models import BidAwardPrice

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