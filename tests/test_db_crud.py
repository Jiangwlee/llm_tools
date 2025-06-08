import pytest
from sqlmodel import SQLModel, Session, create_engine
from datetime import datetime
from src.llm_tools_v1.db.models import Bidding, BiddingPackage
from src.llm_tools_v1.db.crud import (
    create_bidding, get_bidding_by_no, update_bidding, delete_bidding,
    create_bidding_package, get_packages_by_bidding_id,
    update_bidding_package, delete_bidding_package
)
from sqlalchemy import text

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    # 启用 SQLite 外键约束
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
    with Session(engine) as session:
        yield session

def test_crud_bidding_and_package(session):
    """
    测试招标公告和标包的新增、查询、更新、删除
    """
    # 新增招标公告
    bidding_data = {
        "bidding_no": "CG20240010",
        "url": "http://example.com/10",
        "owner": "测试招标人",
        "agent": "测试代理机构",
        "project": "测试项目",
        "description": "测试项目概述"
    }
    bidding = create_bidding(session, bidding_data)
    assert bidding.id is not None
    # 查询
    found = get_bidding_by_no(session, "CG20240010")
    assert found is not None
    assert found.bidding_no == "CG20240010"
    # 更新
    update_bidding(session, "CG20240010", {"owner": "新招标人"})
    updated = get_bidding_by_no(session, "CG20240010")
    assert updated.owner == "新招标人"
    # 新增标包
    pkg_data = {
        "bidding_id": bidding.id,
        "subject": "标的X",
        "package_name": "包X",
        "subject_desc": "描述X",
        "estimated_amount": 200.0,
        "max_bid_amount": 250.0
    }
    pkg = create_bidding_package(session, pkg_data)
    assert pkg.id is not None
    # 查询标包
    pkgs = get_packages_by_bidding_id(session, bidding.id)
    assert len(pkgs) == 1
    # 更新标包
    update_bidding_package(session, pkg.id, {"subject": "标的Y"})
    pkg2 = get_packages_by_bidding_id(session, bidding.id)[0]
    assert pkg2.subject == "标的Y"
    # 删除标包
    delete_bidding_package(session, pkg.id)
    pkgs = get_packages_by_bidding_id(session, bidding.id)
    assert len(pkgs) == 0
    # 删除招标公告
    delete_bidding(session, "CG20240010")
    assert get_bidding_by_no(session, "CG20240010") is None

def test_bidding_no_unique_crud(session):
    """
    测试招标编号唯一性约束
    """
    create_bidding(session, {"bidding_no": "CG20240011", "url": "http://example.com/11"})
    with pytest.raises(Exception):
        create_bidding(session, {"bidding_no": "CG20240011", "url": "http://example.com/12"})

def test_package_foreign_key_crud(session):
    """
    测试标包外键约束
    """
    # 未插入 bidding，直接插入 package 应报错
    pkg_data = {"bidding_id": 999, "subject": "孤立包"}
    with pytest.raises(Exception):
        create_bidding_package(session, pkg_data)

def test_cascade_delete(session):
    """
    测试级联删除：删除招标公告时，子表标包自动删除
    """
    bidding = create_bidding(session, {"bidding_no": "CG20240012", "url": "http://example.com/13"})
    pkg1 = create_bidding_package(session, {"bidding_id": bidding.id, "subject": "A"})
    pkg2 = create_bidding_package(session, {"bidding_id": bidding.id, "subject": "B"})
    pkgs = get_packages_by_bidding_id(session, bidding.id)
    assert len(pkgs) == 2
    # 删除主表
    delete_bidding(session, "CG20240012")
    # 子表应自动删除
    pkgs = get_packages_by_bidding_id(session, bidding.id)
    assert len(pkgs) == 0 