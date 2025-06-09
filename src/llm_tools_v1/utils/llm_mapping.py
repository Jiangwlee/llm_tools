"""
LLM 中文结构化输出到 ORM/Pydantic schema 的字段映射与转换工具
"""

# 主表字段映射
BIDDING_FIELD_MAP = {
    "招标编号": "bidding_no",
    "招标人": "owner",
    "招标代理机构": "agent",
    "招标项目": "project",
    "项目概述": "description",
    "招标文件获取开始时间": "doc_start_time",
    "招标文件获取结束时间": "doc_end_time",
    "投标文件递交截止时间": "submit_deadline",
    "开标时间": "open_time",
    "开标地点": "open_location",
}

# 标包字段映射
PACKAGE_FIELD_MAP = {
    "标的": "subject",
    "标包": "package_name",
    "标的概述": "subject_desc",
    "预计采购金额": "estimated_amount",
    "最高投标限价": "max_bid_amount",
}

# 中标价格字段映射
BID_AWARD_PRICE_FIELD_MAP = {
    "招标编号": "bidding_no",
    "评标情况": "prices",
    "标的": "subject",
    "标包": "package_name",
    "候选人": "candidate",
    "价格类型": "price_type",
}

def map_llm_bidding_to_schema(llm_data: dict, url: str = None) -> dict:
    """
    将 LLM 返回的中文字段 dict 转为 BiddingCreate schema dict
    :param llm_data: LLM 输出的 dict
    :param url: 招标公告原始 URL
    :return: schema 字段 dict
    """
    mapped = {schema_key: llm_data.get(llm_key) for llm_key, schema_key in BIDDING_FIELD_MAP.items()}
    if url:
        mapped["url"] = url
    return mapped

def map_llm_package_to_schema(pkg: dict, bidding_id: int) -> dict:
    """
    将 LLM 返回的标包中文字段 dict 转为 BiddingPackageCreate schema dict
    :param pkg: LLM 输出的标包 dict
    :return: schema 字段 dict
    """
    mapped =  {schema_key: pkg.get(llm_key) for llm_key, schema_key in PACKAGE_FIELD_MAP.items()} 
    if mapped.get("max_bid_amount") and isinstance(mapped.get("max_bid_amount"), str):
        mapped["max_bid_amount"] = mapped["estimated_amount"]
    if bidding_id:
        mapped["bidding_id"] = bidding_id
    return mapped

def map_llm_bid_award_price_to_schema(llm_data: dict, url: str = None, bid_no: str = None) -> dict:
    """
    将 LLM 返回的中标价格 dict 转为 BidAwardPriceCreate schema dict
    :param llm_data: LLM 输出的中标价格 dict
    :return: schema 字段 dict
    """
    mapped = {schema_key: llm_data.get(llm_key) for llm_key, schema_key in BID_AWARD_PRICE_FIELD_MAP.items()}
    if url:
        mapped["url"] = url
    if bid_no:
        mapped["bidding_no"] = bid_no
    if mapped.get("price_type") and isinstance(mapped.get("price_type"), str):
        if mapped.get("price_type") == "数字":
            mapped["price_value"] = llm_data.get("中标价格")
        elif mapped.get("price_type") == "百分比":
            mapped["price_percent"] = llm_data.get("中标价格")
    return mapped