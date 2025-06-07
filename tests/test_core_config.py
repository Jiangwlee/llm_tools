from src.llm_tools_v1.core.config import get_settings, get_current_llm_config, LLMModelConfig


def test_default_llm_config():
    settings = get_settings()
    # 默认当前模型
    assert settings.llm_current == "doubao"
    # 默认模型配置存在
    assert "doubao" in settings.llm_models
    assert isinstance(settings.llm_models["doubao"], LLMModelConfig)
    # 检查默认参数
    doubao = settings.llm_models["doubao"]
    assert doubao.api_url.startswith("https://")
    assert doubao.max_tokens == 32768


def test_switch_llm_config():
    settings = get_settings()
    # 切换到 deepseek
    settings.llm_current = "deepseek"
    llm = get_current_llm_config(settings)
    assert llm.api_url == "https://api.deepseek.com"
    assert llm.max_tokens == 4096
    assert llm.model == "deepseek-chat"


def test_env_override(monkeypatch):
    monkeypatch.setenv("DOUBAO_API_KEY", "test-doubao-key")
    monkeypatch.setenv("LLM_CURRENT", "doubao")
    # 重新加载配置
    from importlib import reload
    import src.llm_tools_v1.core.config as config_mod
    reload(config_mod)
    settings = config_mod.get_settings()
    doubao = settings.llm_models["doubao"]
    assert doubao.api_key == "test-doubao-key"
    assert settings.llm_current == "doubao" 