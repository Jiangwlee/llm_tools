from typing import List, Dict, Any, Optional
from llm_tools_v1.core.config import get_settings, get_current_llm_config
from llm_tools_v1.core.logging import get_logger
import litellm

class LLMClient:
    """
    统一大模型调用客户端，底层基于 liteLLM
    """
    def __init__(self, model_name: Optional[str] = None):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.llm_current
        self.model_config = get_current_llm_config(self.settings)
        self.logger = get_logger(__name__)

    def _prepare_litellm_args(self, **kwargs) -> dict:
        """
        按 liteLLM 官方文档准备参数
        """
        args = {
            "model": self.model_config.model,
            "api_key": self.model_config.api_key,
            "api_base": getattr(self.model_config, "api_url", None),
            "messages": kwargs.get("messages"),
        }
        # 支持 max_tokens、api_version 等
        if hasattr(self.model_config, "max_tokens"):
            args["max_tokens"] = self.model_config.max_tokens
        if hasattr(self.model_config, "api_version"):
            args["api_version"] = getattr(self.model_config, "api_version", None)
        # 允许用户自定义参数覆盖
        args.update(kwargs)
        return args

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """
        同步大模型对话
        :param messages: 对话历史
        :param kwargs: 其他参数
        :return: 模型响应
        """
        try:
            args = self._prepare_litellm_args(messages=messages, **kwargs)
            response = litellm.completion(**args)
            return response
        except Exception as e:
            self.logger.error(f"LLM调用失败: {str(e)}")
            raise

    async def achat(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """
        异步大模型对话
        :param messages: 对话历史
        :param kwargs: 其他参数
        :return: 模型响应
        """
        try:
            args = self._prepare_litellm_args(messages=messages, **kwargs)
            response = await litellm.acompletion(**args)
            return response
        except Exception as e:
            self.logger.error(f"LLM异步调用失败: {str(e)}")
            raise 