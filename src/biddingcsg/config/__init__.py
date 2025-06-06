"""
配置管理模块

统一管理系统配置，包括LLM模型配置、数据库配置、UI配置等。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

from . import global_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SimpleBiddingConfigManager:
    """简化的 BiddingCSG 配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_dir = Path.home() / ".biddingcsg"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "simple_config.json"
        
        # 默认配置
        self.default_config = {
            "default_model": {
                "provider": self._get_default_provider(),
                "name": self._get_default_model()
            }
        }
        
        self.config_data = self.load_config()
    
    def _get_default_provider(self) -> str:
        """获取默认提供商"""
        # 优先级顺序：DEEPSEEK > DOUBAO > SILICONFLOW
        priority_order = ["DEEPSEEK", "DOUBAO", "SILICONFLOW"]
        
        for provider_key in priority_order:
            if provider_key in global_config.PROVIDERS:
                provider_config = global_config.PROVIDERS[provider_key]
                if provider_config.get("API_KEY"):
                    return provider_key
        
        # 如果没有可用的，返回第一个
        if global_config.PROVIDERS:
            return next(iter(global_config.PROVIDERS))
        
        return "DEEPSEEK"
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        provider = self._get_default_provider()
        if provider in global_config.PROVIDERS:
            return global_config.PROVIDERS[provider]["MODEL"]
        return "deepseek-chat"
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                # 合并默认配置
                return {**self.default_config, **config_data}
            else:
                # 首次使用，创建默认配置
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self.default_config.copy()
    
    def save_config(self, config_data: Dict[str, Any] = None) -> bool:
        """保存配置"""
        try:
            data_to_save = config_data or self.config_data
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get_current_model_info(self) -> Dict[str, str]:
        """获取当前模型信息"""
        provider = self.config_data.get("default_model", {}).get("provider", self._get_default_provider())
        model = self.config_data.get("default_model", {}).get("name", self._get_default_model())
        
        return {
            "provider": provider,
            "model": model,
            "display_name": f"{provider} - {model}",
            "available": provider in global_config.PROVIDERS and bool(global_config.PROVIDERS[provider].get("API_KEY"))
        }


# 全局配置管理器实例
_simple_config_manager = None


def get_biddingcsg_config_manager() -> SimpleBiddingConfigManager:
    """获取全局配置管理器实例（单例模式）"""
    global _simple_config_manager
    if _simple_config_manager is None:
        _simple_config_manager = SimpleBiddingConfigManager()
    return _simple_config_manager


def reset_config_manager():
    """重置配置管理器实例（用于测试或重新初始化）"""
    global _simple_config_manager
    _simple_config_manager = None


# 暂时注释导入，等实现后再启用
# from .config import Config
# from .settings import Settings, LLMSettings, CrawlerSettings, UISettings
# from .manager import ConfigManager

__all__ = [
    "get_biddingcsg_config_manager",
    "SimpleBiddingConfigManager",
    "reset_config_manager"
    # "Config",
    # "Settings",
    # "LLMSettings", 
    # "CrawlerSettings",
    # "UISettings",
    # "ConfigManager"
] 