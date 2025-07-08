from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from datetime import datetime, timezone
from llm_tools_v1.db.models import Bidding, BiddingPackage

# 创建招标公告
# 如果已存在相同 bidding_no，抛出异常
def create_bidding(session: Session, bidding_data: Dict[str, Any]) -> Bidding:
    """
    创建招标公告记录
    """
    bidding = Bidding(**bidding_data)
    session.add(bidding)
    session.commit()
    session.refresh(bidding)
    return bidding

# 根据招标编号查询招标公告
def get_bidding_by_no(session: Session, bidding_no: str) -> Optional[Bidding]:
    """
    根据招标编号查询招标公告
    """
    statement = select(Bidding).where(Bidding.bidding_no == bidding_no)
    result = session.exec(statement).first()
    return result

# 更新招标公告（按 bidding_no）
def update_bidding(session: Session, bidding_no: str, update_data: Dict[str, Any]) -> Optional[Bidding]:
    """
    更新招标公告信息，并自动更新时间戳
    """
    bidding = get_bidding_by_no(session, bidding_no)
    if not bidding:
        return None
    for key, value in update_data.items():
        setattr(bidding, key, value)
    bidding.updated_at = datetime.now(timezone.utc)
    session.add(bidding)
    session.commit()
    session.refresh(bidding)
    return bidding

# 删除招标公告（级联删除子表）
def delete_bidding(session: Session, bidding_no: str) -> None:
    """
    删除招标公告，自动级联删除所有关联的标包信息
    """
    bidding = get_bidding_by_no(session, bidding_no)
    if bidding:
        session.delete(bidding)
        session.commit()

# 创建标包信息
def create_bidding_package(session: Session, package_data: Dict[str, Any]) -> BiddingPackage:
    """
    创建标包信息记录
    """
    package = BiddingPackage(**package_data)
    session.add(package)
    session.commit()
    session.refresh(package)
    return package

# 查询某招标公告下所有标包信息
def get_packages_by_bidding_id(session: Session, bidding_id: int) -> List[BiddingPackage]:
    """
    查询指定招标公告下的所有标包信息
    """
    statement = select(BiddingPackage).where(BiddingPackage.bidding_id == bidding_id)
    result = session.exec(statement).all()
    return result

# 更新标包信息（按主键）
def update_bidding_package(session: Session, package_id: int, update_data: Dict[str, Any]) -> Optional[BiddingPackage]:
    """
    更新标包信息，并自动更新时间戳
    """
    statement = select(BiddingPackage).where(BiddingPackage.id == package_id)
    package = session.exec(statement).first()
    if not package:
        return None
    for key, value in update_data.items():
        setattr(package, key, value)
    package.updated_at = datetime.now(timezone.utc)
    session.add(package)
    session.commit()
    session.refresh(package)
    return package

# 删除标包信息（按主键）
def delete_bidding_package(session: Session, package_id: int) -> None:
    """
    删除指定标包信息
    """
    statement = select(BiddingPackage).where(BiddingPackage.id == package_id)
    package = session.exec(statement).first()
    if package:
        session.delete(package)
        session.commit() 