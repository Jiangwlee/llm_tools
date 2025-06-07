import pytest
from unittest.mock import patch
from src.llm_tools_v1.core.llm import LLMClient

messages = [
    {"role": "user", "content": "你好"}
]

def test_llm_chat_doubao(monkeypatch):
    # 切换到 doubao
    client = LLMClient(model_name="doubao")
    # mock litellm.completion
    with patch("litellm.completion") as mock_completion:
        mock_completion.return_value = {"choices": [{"message": {"content": "你好，我是豆包。"}}]}
        response = client.chat(messages)
        mock_completion.assert_called_once()
        args = mock_completion.call_args.kwargs
        assert args["model"] == client.model_config.model
        assert args["api_key"] == client.model_config.api_key
        assert args["api_base"] == client.model_config.api_url
        assert args["messages"] == messages
        assert response["choices"][0]["message"]["content"] == "你好，我是豆包。"

def test_llm_chat_deepseek(monkeypatch):
    # 切换到 deepseek
    client = LLMClient(model_name="deepseek")
    with patch("litellm.completion") as mock_completion:
        mock_completion.return_value = {"choices": [{"message": {"content": "你好，我是DeepSeek。"}}]}
        response = client.chat(messages)
        mock_completion.assert_called_once()
        args = mock_completion.call_args.kwargs
        assert args["model"] == client.model_config.model
        assert args["api_key"] == client.model_config.api_key
        assert args["api_base"] == client.model_config.api_url
        assert args["messages"] == messages
        assert response["choices"][0]["message"]["content"] == "你好，我是DeepSeek。"

@pytest.mark.asyncio
async def test_llm_achat_doubao(monkeypatch):
    client = LLMClient(model_name="doubao")
    with patch("litellm.acompletion") as mock_acompletion:
        mock_acompletion.return_value = {"choices": [{"message": {"content": "异步豆包。"}}]}
        response = await client.achat(messages)
        mock_acompletion.assert_called_once()
        args = mock_acompletion.call_args.kwargs
        assert args["model"] == client.model_config.model
        assert args["api_key"] == client.model_config.api_key
        assert args["api_base"] == client.model_config.api_url
        assert args["messages"] == messages
        assert response["choices"][0]["message"]["content"] == "异步豆包。" 