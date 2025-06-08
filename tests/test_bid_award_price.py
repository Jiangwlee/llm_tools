import pytest
from datetime import datetime, timezone
from src.llm_tools_v1.db.models import BidAwardPrice

# 1. 实例化测试（所有字段赋值）
def test_bid_award_price_full_fields():
    now = datetime.now(timezone.utc)
    obj = BidAwardPrice(
        id=1,
        bidding_no="CG2700022002045865",
        subject="标的3：便携式发电车无感退出装备及关键技术研究（技术开发）",
        package_name="便携式发电车无感退出装备及关键技术研究（技术开发）",
        candidate="广州知在科技有限公司",
        price_type="数字",
        price_value=75.33,
        price_percent=None,
        currency="CNY",
        remark="测试数据",
        created_at=now,
        updated_at=now
    )
    # 字段断言
    assert obj.bidding_no == "CG2700022002045865"
    assert obj.price_type == "数字"
    assert obj.price_value == 75.33
    assert obj.price_percent is None
    assert obj.currency == "CNY"
    assert obj.created_at == now
    assert obj.updated_at == now

# 2. 实例化测试（部分字段缺省）
def test_bid_award_price_partial_fields():
    obj = BidAwardPrice(
        bidding_no="CG2700022002045865",
        subject="标的4",
        package_name="标包4",
        candidate="三峡大学",
        price_type="百分比",
        price_percent=0.85
    )
    assert obj.price_value is None
    assert obj.price_percent == 0.85
    assert obj.currency is None
    assert obj.remark is None
    assert isinstance(obj.created_at, datetime)
    assert obj.created_at.tzinfo is not None

# 3. SQLModel 表名和主键校验
def test_bid_award_price_table_meta():
    assert BidAwardPrice.__tablename__ == "bidawardprice" or BidAwardPrice.__tablename__ == "bid_award_price"
    pk_fields = [f.name for f in BidAwardPrice.__table__.primary_key.columns]
    assert "id" in pk_fields

# 4. 字段类型校验
def test_bid_award_price_field_types():
    obj = BidAwardPrice(
        bidding_no="CG2700022002045865",
        subject="标的5",
        package_name="标包5",
        candidate="珠江水利委员会珠江水利科学研究院",
        price_type="数字",
        price_value=123.45
    )
    assert isinstance(obj.bidding_no, str)
    assert isinstance(obj.subject, str)
    assert isinstance(obj.price_value, float)
    assert obj.price_percent is None

# 5. 兼容 pytest 运行
def test_bid_award_price_compatibility():
    # 这里需要根据实际情况编写兼容 pytest 运行的测试用例
    pass 