import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import pytest
import pytest_asyncio
import asyncio
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from llm_tools_v1.db.models import BidAwardPrice, Bidding, BiddingPackage
from llm_tools_v1.services.bid_award_price_service import BidAwardPriceService, BidAwardPriceCreate, BidAwardPriceInfo

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="module")
async def async_session():
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

@pytest.mark.asyncio
async def test_create_price(async_session):
    """测试单条插入中标价格"""
    data = BidAwardPriceCreate(
        bidding_no="BID001",
        subject="标的A",
        package_name="包A",
        candidate="公司A",
        price_type="数字",
        price_value=100.0,
        url="http://example.com/award/1"
    )
    price = await BidAwardPriceService.create_price(data, async_session)
    assert price.id is not None
    assert price.bidding_no == "BID001"
    assert price.price_value == 100.0

@pytest.mark.asyncio
async def test_get_price_by_bidding_no_and_package(async_session):
    """测试按公告编号和标包名称查询中标价格"""
    # 先插入
    data = BidAwardPriceCreate(
        bidding_no="BID002",
        subject="标的B",
        package_name="包B",
        candidate="公司B",
        price_type="百分比",
        price_percent=0.85,
        url="http://example.com/award/2"
    )
    await BidAwardPriceService.create_price(data, async_session)
    # 查询
    price = await BidAwardPriceService.get_price_by_bidding_no_and_package("BID002", "包B", async_session)
    assert price is not None
    assert price.candidate == "公司B"
    assert price.price_percent == 0.85

@pytest.mark.asyncio
async def test_delete_by_bidding_no(async_session):
    """测试按公告编号删除中标价格"""
    # 插入多条
    for i in range(3):
        data = BidAwardPriceCreate(
            bidding_no="BID003",
            subject=f"标的{i}",
            package_name=f"包{i}",
            candidate=f"公司{i}",
            price_type="数字",
            price_value=10.0 + i,
            url=f"http://example.com/award/3_{i}"
        )
        await BidAwardPriceService.create_price(data, async_session)
    # 删除
    deleted = await BidAwardPriceService.delete_by_bidding_no("BID003", async_session)
    assert deleted == 3
    # 确认已删除
    price = await BidAwardPriceService.get_price_by_bidding_no_and_package("BID003", "包0", async_session)
    assert price is None

@pytest.mark.asyncio
async def test_create_multi_prices(async_session):
    """测试批量插入中标价格"""
    data_list = [
        BidAwardPriceCreate(
            bidding_no="BID004",
            subject=f"标的{i}",
            package_name=f"包{i}",
            candidate=f"公司{i}",
            price_type="数字",
            price_value=20.0 + i,
            url=f"http://example.com/award/4_{i}"
        ) for i in range(5)
    ]
    prices = await BidAwardPriceService.create_multi_prices(data_list, async_session)
    await async_session.commit()
    assert len(prices) == 5
    # 检查一条
    price = await BidAwardPriceService.get_price_by_bidding_no_and_package("BID004", "包3", async_session)
    assert price is not None
    assert price.price_value == 23.0

@pytest.mark.asyncio
async def test_list_award_price_infos(async_session):
    """
    测试 list_award_price_infos 查询所有中标公示详细信息
    """
    # 插入 Bidding
    bidding = Bidding(bidding_no="BID100", url="http://bidding/100", project="项目100", owner="测试招标单位")
    async_session.add(bidding)
    await async_session.commit()
    await async_session.refresh(bidding)
    # 插入 BiddingPackage
    package = BiddingPackage(
        bidding_id=bidding.id,
        subject="标的100",
        package_name="包100",
        estimated_amount=888.0,
        max_bid_amount=999.0
    )
    async_session.add(package)
    await async_session.commit()
    await async_session.refresh(package)
    # 插入 BidAwardPrice
    price = BidAwardPrice(
        bidding_no="BID100",
        subject="标的100",
        package_name="包100",
        candidate="中标公司",
        price_type="数字",
        price_value=777.0,
        price_percent=None,
        url="http://award/100"
    )
    async_session.add(price)
    await async_session.commit()
    # 查询
    infos = await BidAwardPriceService.list_award_price_infos(async_session, owner="测试招标单位")
    assert len(infos) >= 1
    info = [i for i in infos if i.bidding_no == "BID100" and i.subject == "标的100"]
    assert info, "应能查到插入的数据"
    info = info[0]
    assert info.project == "项目100"
    assert info.estimated_amount == 888.0
    assert info.max_bid_amount == 999.0
    assert info.price_value == 777.0
    assert info.price_type == "数字"
    assert info.owner == "测试招标单位"
    assert info.award_url == "http://award/100"
    assert info.bidding_url == "http://bidding/100"
    # 边界：无匹配数据
    await async_session.execute(text("DELETE FROM bidawardprice"))
    await async_session.commit()
    infos = await BidAwardPriceService.list_award_price_infos(async_session, owner="测试招标单位")
    assert all(i.bidding_no != "BID100" for i in infos) 