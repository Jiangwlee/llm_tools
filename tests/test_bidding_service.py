import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from src.llm_tools_v1.services.bidding_service import (
    BiddingService, BiddingPackageService, BiddingCreate, BiddingPackageCreate
)
from src.llm_tools_v1.db.models import Bidding, BiddingPackage

# 使用内存数据库，所有 session 复用同一个 engine
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="module")
async def prepare_db():
    """
    创建测试表结构并返回 engine
    """
    engine = create_async_engine(
        DATABASE_URL, echo=False, future=True, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(prepare_db):
    """
    获取异步 Session，所有 session 复用同一个 engine
    """
    engine = prepare_db
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_create_and_delete_bidding(db_session):
    """
    测试招标公告的插入和删除
    """
    data = BiddingCreate(bidding_no="BN001", url="http://test.com")
    bidding = await BiddingService.create_bidding(data, db_session)
    assert bidding.id is not None
    assert bidding.bidding_no == "BN001"

    # 删除
    result = await BiddingService.delete_bidding(bidding.id, db_session)
    assert result is True
    # 再次删除应返回 False
    result2 = await BiddingService.delete_bidding(bidding.id, db_session)
    assert result2 is False

@pytest.mark.asyncio
async def test_create_and_delete_package(db_session):
    """
    测试标包的插入和删除
    """
    # 先插入一个 Bidding 作为外键
    bidding = await BiddingService.create_bidding(BiddingCreate(bidding_no="BN002", url="http://test2.com"), db_session)
    data = BiddingPackageCreate(bidding_id=bidding.id, package_name="包A")
    package = await BiddingPackageService.create_package(data, db_session)
    assert package.id is not None
    assert package.bidding_id == bidding.id

    # 删除
    result = await BiddingPackageService.delete_package(package.id, db_session)
    assert result is True
    # 再次删除应返回 False
    result2 = await BiddingPackageService.delete_package(package.id, db_session)
    assert result2 is False

@pytest.mark.asyncio
async def test_bidding_unique_constraint(db_session):
    """
    测试招标公告唯一约束冲突
    """
    data = BiddingCreate(bidding_no="BN003", url="http://test3.com")
    await BiddingService.create_bidding(data, db_session)
    with pytest.raises(Exception):
        # 再插入相同 bidding_no 应报错
        await BiddingService.create_bidding(data, db_session) 