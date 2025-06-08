from typing import Optional
from dataclasses import dataclass
from .llm import LLMClient
from .logging import get_logger

logger = get_logger()

@dataclass
class LLMResult:
    content: Optional[str]
    success: bool
    error: Optional[str] = None

def chat(system_prompt: str, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    通用大模型同步调用函数，结构化返回结果。
    Args:
        system_prompt (str): 系统提示词
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:
        LLMResult: 结构化返回内容、状态和错误信息
    """
    if llm_client is None:
        llm_client = LLMClient(model_name="doubao")
    try:
        logger.info(f"调用大模型，Prompt 摘要: {system_prompt[:50]}...")
        messages = [{"role": "system", "content": system_prompt}]
        resp = llm_client.chat(messages, temperature=0.1)
        content = resp.get("choices", [{}])[0].get("message", {}).get("content")
        if content:
            return LLMResult(content=content, success=True)
        else:
            return LLMResult(content=None, success=False, error="模型未返回内容")
    except (KeyError, TypeError) as ex:
        logger.warning(f"chat 返回格式异常: {ex}")
        return LLMResult(content=None, success=False, error=f"返回格式异常: {ex}")
    except Exception as ex:
        logger.warning(f"chat 调用大模型出错, 错误信息: {ex}")
        return LLMResult(content=None, success=False, error=str(ex))

async def achat(system_prompt: str, llm_client: Optional[LLMClient] = None) -> LLMResult:
    """
    通用大模型异步调用函数，结构化返回结果。
    Args:
        system_prompt (str): 系统提示词
        llm_client (Optional[LLMClient]): 可注入的 LLMClient 实例
    Returns:
        LLMResult: 结构化返回内容、状态和错误信息
    """
    if llm_client is None:
        llm_client = LLMClient(model_name="doubao")
    try:
        logger.info(f"调用大模型，Prompt 摘要: {system_prompt[:50]}...")
        messages = [{"role": "system", "content": system_prompt}]
        resp = await llm_client.achat(messages, temperature=0.1)
        content = resp.get("choices", [{}])[0].get("message", {}).get("content")
        if content:
            return LLMResult(content=content, success=True)
        else:
            return LLMResult(content=None, success=False, error="模型未返回内容")
    except (KeyError, TypeError) as ex:
        logger.warning(f"achat 返回格式异常: {ex}")
        return LLMResult(content=None, success=False, error=f"返回格式异常: {ex}")
    except Exception as ex:
        logger.warning(f"achat 调用大模型出错, 错误信息: {ex}")
        return LLMResult(content=None, success=False, error=str(ex)) 