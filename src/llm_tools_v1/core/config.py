from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os

class LLMModelConfig(BaseModel):
    api_url: str
    api_key: str
    model: str
    timeout: int = 30
    max_tokens: int = 4096
    extra: Dict[str, Any] = {}

LLM_DICT = {
    "doubao": LLMModelConfig(
        api_url="https://ark.cn-beijing.volces.com/api/v3/",
        api_key=os.getenv("DOUBAO_API_KEY", None),
        model="doubao-1.5-pro-32k-250115",
        max_tokens=32768
    ),
    "deepseek": LLMModelConfig(
        api_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY", None),
        model="deepseek-chat",
        max_tokens=4096
    )
}

class Settings(BaseSettings):
    # 多大模型参数配置
    llm_models: Dict[str, LLMModelConfig] = LLM_DICT
    llm_current: str = Field("doubao", validation_alias="LLM_CURRENT")  # 当前激活模型

    # 目录路径
    data_dir: Path = Field("data", validation_alias="DATA_DIR")
    log_dir: Path = Field("data/logs", validation_alias="LOG_DIR")
    db_dir: Path = Field("data/db", validation_alias="DB_DIR")
    cache_dir: Path = Field("data/cache", validation_alias="CACHE_DIR")

    # 其他配置
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    env: str = Field("dev", validation_alias="ENV")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

@lru_cache()
def get_settings() -> Settings:
    """
    获取全局唯一配置实例
    """
    return Settings()

def get_current_llm_config(settings: Settings = None) -> LLMModelConfig:
    """
    获取当前激活大模型的配置
    """
    if settings is None:
        settings = get_settings()
    return settings.llm_models[settings.llm_current] 