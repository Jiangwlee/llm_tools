from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os

class LLMModelConfig(BaseModel):
    api_url: str
    api_key: str
    model: str  # provider/model 格式
    timeout: int = 30
    max_tokens: int = 4096
    extra: Dict[str, Any] = {}

LLM_DICT = {
    # doubao 目前 liteLLM 官方未直接支持，保留配置但不推荐直接调用
    "doubao": LLMModelConfig(
        api_url="https://ark.cn-beijing.volces.com/api/v3/",
        api_key=os.getenv("DOUBAO_API_KEY", None),
        model="openai/doubao-1.5-pro-32k-250115",  # 暂不支持 provider/model 格式
        max_tokens=16384
    ),
    "deepseek": LLMModelConfig(
        api_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY", None),
        model="deepseek/deepseek-chat",  # 推荐 provider/model 格式
        max_tokens=4096
    )
}

class Settings(BaseSettings):
    # 多大模型参数配置
    llm_models: Dict[str, LLMModelConfig] = LLM_DICT
    llm_current: str = Field("doubao", validation_alias="LLM_CURRENT")  # 当前激活模型

    # 目录路径
    llm_tools_home: Path = Field(os.path.expanduser("~/.llm_tools"), validation_alias="LLM_TOOLS_HOME")

    # 其他配置
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    env: str = Field("dev", validation_alias="ENV")

    # 数据库配置
    db_type: str = Field("sqlite", validation_alias="DB_TYPE")
    db_async_url: str | None = Field(None, validation_alias="DB_ASYNC_URL")
    db_echo: bool = Field(False, validation_alias="DB_ECHO")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    def model_post_init(self, __context):
        if not self.db_async_url:
            os.makedirs(self.llm_tools_home / "data" / "db", exist_ok=True)
            db_path = self.llm_tools_home / "data" / "db" / "llm_tools.db"
            self.db_async_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"


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

def set_current_llm(model_name: str):
    """
    一键切换当前激活大模型，并清理缓存
    :param model_name: 目标模型名（如 deepseek/openai/qwen）
    """
    os.environ["LLM_CURRENT"] = model_name
    get_settings.cache_clear() 

class LlmToolsDirs:
    @staticmethod
    def get_llm_tools_home() -> Path:
        path = get_settings().llm_tools_home
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_data_dir() -> Path:
        path = LlmToolsDirs.get_llm_tools_home() / "data"
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_log_dir() -> Path:
        path = LlmToolsDirs.get_data_dir() / "logs"
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_db_dir() -> Path:
        path = LlmToolsDirs.get_data_dir() / "db"
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_cache_dir() -> Path:
        path = LlmToolsDirs.get_data_dir() / "cache"
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path