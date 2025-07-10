import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from datetime import datetime, timezone
from sqlalchemy import text
from llm_tools_v1.db.models import Bidding, BiddingPackage

# 使用内存数据库进行测试，并启用外键约束
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    # 启用 SQLite 外键约束
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
    with Session(engine) as session:
        yield session

def test_create_bidding_and_package(session):
    """
    测试招标公告和标包信息的插入与关联
    """
    bidding = Bidding(
        bidding_no="CG20240001",
        url="http://example.com/1",
        owner="测试招标人",
        agent="测试代理机构",
        project="测试项目",
        description="测试项目概述"
    )
    session.add(bidding)
    session.commit()
    session.refresh(bidding)
    # 检查主键和时间戳
    assert bidding.id is not None
    assert isinstance(bidding.created_at, datetime)
    assert isinstance(bidding.updated_at, datetime)

    # 插入标包信息
    pkg = BiddingPackage(
        bidding_id=bidding.id,
        subject="标的A",
        package_name="包A",
        subject_desc="标的A描述",
        estimated_amount=100.0,
        max_bid_amount=120.0
    )
    session.add(pkg)
    session.commit()
    session.refresh(pkg)
    assert pkg.id is not None
    assert pkg.bidding_id == bidding.id
    assert isinstance(pkg.created_at, datetime)
    assert isinstance(pkg.updated_at, datetime)

def test_bidding_no_unique(session):
    """
    测试招标编号唯一性约束
    """
    bidding1 = Bidding(bidding_no="CG20240002", url="http://example.com/2")
    session.add(bidding1)
    session.commit()
    # 尝试插入相同编号
    bidding2 = Bidding(bidding_no="CG20240002", url="http://example.com/3")
    session.add(bidding2)
    with pytest.raises(Exception):
        session.commit()

def test_foreign_key_constraint(session):
    """
    测试标包的外键约束
    """
    # 未插入 bidding，直接插入 package 应报错
    pkg = BiddingPackage(bidding_id=999, subject="标的B")
    session.add(pkg)
    with pytest.raises(Exception):
        session.commit() 