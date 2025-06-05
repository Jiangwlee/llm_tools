import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from src.llm_tools import config
from src.llm_tools.logger import get_logger

# 获取日志记录器
logger = get_logger()

class ConfigManager:
    """Web UI 配置管理器"""
    
    def __init__(self, config_file: str = "web_ui_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件名称，支持 .json 和 .yaml/.yml 格式
        """
        self.config_dir = Path.home() / ".llm_tools"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / config_file
        self.config_data = {}
        
        # 默认配置（使用 config.py 中的第一个可用提供商）
        default_provider = self._get_default_provider()
        self.default_config = {
            "default_model": {
                "provider": default_provider["key"],
                "name": default_provider["model"]
            },
            "ui_settings": {
                "theme": "light",
                "language": "zh-CN",
                "page_size": 20
            },
            "download_settings": {
                "default_max_pages": 5,
                "default_bidding_type": None,
                "auto_save": True
            },
            "query_settings": {
                "show_charts": True,
                "auto_export": False,
                "result_limit": 100
            }
        }
        
        # 从 config.py 加载可用的模型提供商
        self.available_models = self._load_available_models()
        
        self.load_config()
    
    def _get_default_provider(self) -> Dict[str, str]:
        """
        获取默认的模型提供商
        
        Returns:
            包含 key 和 model 的字典
        """
        # 优先级顺序：DEEPSEEK > DOUBAO > SILICONFLOW
        priority_order = ["DEEPSEEK", "DOUBAO", "SILICONFLOW"]
        
        for provider_key in priority_order:
            if provider_key in config.PROVIDERS:
                return {
                    "key": provider_key,
                    "model": config.PROVIDERS[provider_key]["MODEL"]
                }
        
        # 如果没有找到优先级中的提供商，使用第一个可用的
        if config.PROVIDERS:
            first_key = next(iter(config.PROVIDERS))
            return {
                "key": first_key,
                "model": config.PROVIDERS[first_key]["MODEL"]
            }
        
        # 兜底默认值
        return {"key": "DEEPSEEK", "model": "deepseek-chat"}
    
    def _load_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        从 config.py 加载可用的模型提供商配置
        
        Returns:
            模型提供商配置字典
        """
        # 模型提供商的友好名称映射
        provider_names = {
            "DEEPSEEK": "DeepSeek",
            "DOUBAO": "豆包 (字节跳动)",
            "SILICONFLOW": "硅基流动"
        }
        
        # 模型的友好名称映射
        model_display_names = {
            "deepseek-chat": "DeepSeek Chat",
            "deepseek-coder": "DeepSeek Coder",
            "doubao-1.5-pro-32k-250115": "豆包 1.5 Pro 32K",
            "doubao-lite-4k": "豆包 Lite 4K",
            "deepseek-ai/DeepSeek-V3": "DeepSeek V3",
            "Qwen/Qwen2.5-72B-Instruct": "Qwen 2.5 72B",
            "meta-llama/Meta-Llama-3.1-70B-Instruct": "Llama 3.1 70B"
        }
        
        available_models = {}
        
        # 从 config.PROVIDERS 加载配置
        for provider_key, provider_config in config.PROVIDERS.items():
            # 获取提供商友好名称
            provider_name = provider_names.get(provider_key, provider_key)
            
            # 获取模型配置
            model_key = provider_config["MODEL"]
            model_display_name = model_display_names.get(model_key, model_key)
            
            available_models[provider_key] = {
                "name": provider_name,
                "models": {
                    model_key: model_display_name
                },
                "api_key_env": provider_config["API_KEY_ENV"],
                "base_url": provider_config["BASE_URL"]
            }
        
        # 为某些提供商添加额外的模型选项
        if "DEEPSEEK" in available_models:
            available_models["DEEPSEEK"]["models"]["deepseek-coder"] = "DeepSeek Coder"
        
        if "DOUBAO" in available_models:
            available_models["DOUBAO"]["models"]["doubao-lite-4k"] = "豆包 Lite 4K"
        
        if "SILICONFLOW" in available_models:
            available_models["SILICONFLOW"]["models"].update({
                "Qwen/Qwen2.5-72B-Instruct": "Qwen 2.5 72B",
                "meta-llama/Meta-Llama-3.1-70B-Instruct": "Llama 3.1 70B"
            })
        
        return available_models
    
    def test_model_connection(self, provider: str = None) -> Dict[str, Any]:
        """
        测试模型连接
        
        Args:
            provider: 要测试的提供商，如果为None则测试当前选择的模型
            
        Returns:
            测试结果字典
        """
        if provider is None:
            current_model = self.get_current_model_info()
            provider = current_model["provider"]
        
        logger.info(f"开始测试模型连接: {provider}")
        
        # 检查提供商是否存在
        if provider not in config.PROVIDERS:
            logger.error(f"未知的模型提供商: {provider}")
            return {
                "success": False,
                "provider": provider,
                "message": f"未知的模型提供商: {provider}",
                "details": "请检查配置文件中的提供商设置"
            }
        
        provider_config = config.PROVIDERS[provider]
        provider_name = self.available_models.get(provider, {}).get("name", provider)
        
        # 检查API密钥
        if not provider_config["API_KEY"]:
            logger.warning(f"模型 {provider} API密钥未配置")
            return {
                "success": False,
                "provider": provider,
                "provider_name": provider_name,
                "message": f"API密钥未配置",
                "details": f"请设置环境变量: {provider_config['API_KEY_ENV']}"
            }
        
        # 根据不同提供商调用相应的测试方法
        try:
            logger.info(f"开始调用 {provider} 模型API")
            if provider == "DEEPSEEK":
                result = self._test_deepseek_connection(provider_config, provider_name)
            elif provider == "DOUBAO":
                result = self._test_doubao_connection(provider_config, provider_name)
            elif provider == "SILICONFLOW":
                result = self._test_siliconflow_connection(provider_config, provider_name)
            else:
                result = self._test_generic_openai_connection(provider_config, provider_name, provider)
                
            if result["success"]:
                logger.info(f"模型 {provider} 连接测试成功，响应时间: {result.get('response_time', 'N/A')}ms")
            else:
                logger.error(f"模型 {provider} 连接测试失败: {result['message']}")
                
            return result
                
        except Exception as e:
            logger.error(f"模型 {provider} 连接测试异常: {str(e)}")
            return {
                "success": False,
                "provider": provider,
                "provider_name": provider_name,
                "message": f"连接测试异常",
                "details": str(e)
            }
    
    def _test_generic_openai_connection(self, provider_config: Dict[str, Any], provider_name: str, provider: str) -> Dict[str, Any]:
        """
        通用的OpenAI兼容API连接测试
        """
        try:
            from openai import OpenAI
            import time
            
            client = OpenAI(
                api_key=provider_config["API_KEY"],
                base_url=provider_config["BASE_URL"]
            )
            
            start_time = time.time()
            
            response = client.chat.completions.create(
                model=provider_config["MODEL"],
                messages=[
                    {"role": "system", "content": "你是一个AI助手"},
                    {"role": "user", "content": "请回复'连接测试成功'"}
                ],
                max_tokens=50,
                temperature=0.1,
                timeout=30
            )
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            if response.choices and response.choices[0].message.content:
                return {
                    "success": True,
                    "provider": provider,
                    "provider_name": provider_name,
                    "message": "连接测试成功",
                    "details": f"响应时间: {response_time}ms",
                    "response_content": response.choices[0].message.content.strip(),
                    "response_time": response_time
                }
            else:
                return {
                    "success": False,
                    "provider": provider,
                    "provider_name": provider_name,
                    "message": "API响应异常",
                    "details": "未收到有效的响应内容"
                }
                
        except Exception as e:
            return {
                "success": False,
                "provider": provider,
                "provider_name": provider_name,
                "message": "连接失败",
                "details": str(e)
            }
    
    def _test_deepseek_connection(self, provider_config: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """测试DeepSeek连接"""
        return self._test_generic_openai_connection(provider_config, provider_name, "DEEPSEEK")
    
    def _test_doubao_connection(self, provider_config: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """测试豆包连接"""
        return self._test_generic_openai_connection(provider_config, provider_name, "DOUBAO")
    
    def _test_siliconflow_connection(self, provider_config: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """测试硅基流动连接"""
        return self._test_generic_openai_connection(provider_config, provider_name, "SILICONFLOW")
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                        self.config_data = yaml.safe_load(f) or {}
                    else:
                        self.config_data = json.load(f)
                
                # 合并默认配置
                self.config_data = self._merge_config(self.default_config, self.config_data)
            else:
                # 首次使用，创建默认配置
                self.config_data = self.default_config.copy()
                self.save_config()
                
        except Exception as e:
            st.error(f"❌ 加载配置文件失败: {str(e)}")
            self.config_data = self.default_config.copy()
        
        return self.config_data
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否保存成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config_data, f, allow_unicode=True, indent=2)
                else:
                    json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.error(f"❌ 保存配置文件失败: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键如 "default_model.provider"
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, auto_save: bool = True) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            auto_save: 是否自动保存
            
        Returns:
            是否设置成功
        """
        keys = key.split('.')
        config = self.config_data
        
        # 创建嵌套字典结构
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        
        if auto_save:
            return self.save_config()
        
        return True
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的模型列表"""
        return self.available_models
    
    def get_model_display_name(self, provider: str, model: str) -> str:
        """
        获取模型的显示名称
        
        Args:
            provider: 提供商名称
            model: 模型名称
            
        Returns:
            显示名称
        """
        if provider in self.available_models:
            provider_info = self.available_models[provider]
            model_name = provider_info["models"].get(model, model)
            return f"{provider_info['name']} - {model_name}"
        return f"{provider} - {model}"
    
    def check_model_availability(self, provider: str) -> bool:
        """
        检查模型提供商是否可用（检查API密钥）
        
        Args:
            provider: 提供商名称
            
        Returns:
            是否可用
        """
        if provider not in self.available_models:
            return False
        
        api_key_env = self.available_models[provider]["api_key_env"]
        return bool(os.getenv(api_key_env))
    
    def get_current_model_info(self) -> Dict[str, str]:
        """
        获取当前选择的模型信息
        
        Returns:
            包含 provider, model, display_name 的字典
        """
        default_provider = self._get_default_provider()
        provider = self.get("default_model.provider", default_provider["key"])
        model = self.get("default_model.name", default_provider["model"])
        display_name = self.get_model_display_name(provider, model)
        
        return {
            "provider": provider,
            "model": model,
            "display_name": display_name,
            "available": self.check_model_availability(provider)
        }
    
    def get_current_model_config(self) -> Dict[str, Any]:
        """
        获取当前模型的完整配置信息（用于实际调用API）
        
        Returns:
            包含 base_url, api_key, model 等的配置字典
        """
        current_model = self.get_current_model_info()
        provider = current_model["provider"]
        
        if provider in config.PROVIDERS:
            provider_config = config.PROVIDERS[provider]
            return {
                "base_url": provider_config["BASE_URL"],
                "api_key": provider_config["API_KEY"],
                "model": current_model["model"],
                "provider": provider,
                "available": current_model["available"]
            }
        
        # 兜底返回
        return {
            "base_url": None,
            "api_key": None,
            "model": current_model["model"],
            "provider": provider,
            "available": False
        }
    
    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认配置和用户配置
        
        Args:
            default: 默认配置
            user: 用户配置
            
        Returns:
            合并后的配置
        """
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def reset_to_default(self) -> bool:
        """
        重置为默认配置
        
        Returns:
            是否重置成功
        """
        self.config_data = self.default_config.copy()
        return self.save_config()
    
    def export_config(self) -> str:
        """
        导出配置为 JSON 字符串
        
        Returns:
            JSON 格式的配置字符串
        """
        return json.dumps(self.config_data, ensure_ascii=False, indent=2)
    
    def import_config(self, config_str: str) -> bool:
        """
        从 JSON 字符串导入配置
        
        Args:
            config_str: JSON 格式的配置字符串
            
        Returns:
            是否导入成功
        """
        try:
            imported_config = json.loads(config_str)
            self.config_data = self._merge_config(self.default_config, imported_config)
            return self.save_config()
        except Exception as e:
            st.error(f"❌ 导入配置失败: {str(e)}")
            return False


# 全局配置管理器实例
@st.cache_resource
def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    return ConfigManager()


def show_model_selector(config_manager: ConfigManager) -> None:
    """
    显示模型选择器组件
    
    Args:
        config_manager: 配置管理器实例
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 默认模型配置")
    
    # 获取当前模型信息
    current_model = config_manager.get_current_model_info()
    available_models = config_manager.get_available_models()
    
    # 创建选项列表
    model_options = []
    model_mapping = {}
    
    for provider, provider_info in available_models.items():
        for model_key, model_name in provider_info["models"].items():
            display_name = f"{provider_info['name']} - {model_name}"
            availability = "✅" if config_manager.check_model_availability(provider) else "❌"
            option_text = f"{availability} {display_name}"
            
            model_options.append(option_text)
            model_mapping[option_text] = (provider, model_key)
    
    # 找到当前选择的索引
    current_display = config_manager.get_model_display_name(
        current_model["provider"], 
        current_model["model"]
    )
    current_option = f"{'✅' if current_model['available'] else '❌'} {current_display}"
    
    try:
        current_index = model_options.index(current_option)
    except ValueError:
        current_index = 0
    
    # 模型选择器
    selected_option = st.sidebar.selectbox(
        "选择默认模型",
        options=model_options,
        index=current_index,
        help="选择系统默认使用的大语言模型"
    )
    
    # 检查是否有变化
    if selected_option in model_mapping:
        new_provider, new_model = model_mapping[selected_option]
        
        if (new_provider != current_model["provider"] or 
            new_model != current_model["model"]):
            
            # 更新配置
            config_manager.set("default_model.provider", new_provider)
            config_manager.set("default_model.name", new_model)
            
            # 显示更新提示
            if config_manager.check_model_availability(new_provider):
                st.sidebar.success(f"✅ 已切换到: {config_manager.get_model_display_name(new_provider, new_model)}")
            else:
                st.sidebar.warning(f"⚠️ 模型已选择但API密钥未配置: {new_provider}")
    
    # 显示当前模型状态
    with st.sidebar.expander("📊 模型状态"):
        for provider, provider_info in available_models.items():
            api_key_env = provider_info["api_key_env"]
            is_available = config_manager.check_model_availability(provider)
            status_icon = "✅" if is_available else "❌"
            
            st.write(f"{status_icon} **{provider_info['name']}**")
            if not is_available:
                st.caption(f"需要设置环境变量: {api_key_env}")
    
    # 连接测试按钮
    if st.sidebar.button("🔌 连接测试", help="测试当前选择的模型连通性", use_container_width=True):
        with st.sidebar:
            with st.spinner("正在测试连接..."):
                test_result = config_manager.test_model_connection()
                
                if test_result["success"]:
                    st.success(f"✅ {test_result['message']}")
                    st.info(f"🤖 **{test_result['provider_name']}**\n\n"
                           f"📊 {test_result['details']}\n\n"
                           f"💬 模型回复: {test_result.get('response_content', 'N/A')}")
                else:
                    st.error(f"❌ {test_result['message']}")
                    st.warning(f"🔧 **{test_result.get('provider_name', test_result['provider'])}**\n\n"
                              f"📋 详情: {test_result['details']}")
    
    # 配置管理按钮
    with st.sidebar.expander("⚙️ 配置管理"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("重置配置", help="重置为默认配置"):
                if config_manager.reset_to_default():
                    st.success("✅ 配置已重置")
                    st.rerun()
        
        with col2:
            if st.button("刷新状态", help="重新检查模型可用性"):
                st.rerun()
        
        # 配置文件位置信息
        st.caption(f"配置文件: `{config_manager.config_file}`")


def show_advanced_settings(config_manager: ConfigManager) -> None:
    """
    显示高级设置
    
    Args:
        config_manager: 配置管理器实例
    """
    with st.sidebar.expander("🔧 高级设置"):
        
        # 下载设置
        st.write("**下载设置**")
        
        default_max_pages = st.number_input(
            "默认最大页数",
            min_value=1,
            max_value=100,
            value=config_manager.get("download_settings.default_max_pages", 5),
            help="数据下载时的默认最大页数"
        )
        
        auto_save = st.checkbox(
            "自动保存数据",
            value=config_manager.get("download_settings.auto_save", True),
            help="是否自动保存下载的数据"
        )
        
        # 查询设置
        st.write("**查询设置**")
        
        show_charts = st.checkbox(
            "显示图表",
            value=config_manager.get("query_settings.show_charts", True),
            help="查询结果是否显示图表分析"
        )
        
        result_limit = st.number_input(
            "结果限制",
            min_value=10,
            max_value=1000,
            value=config_manager.get("query_settings.result_limit", 100),
            help="查询结果的最大显示数量"
        )
        
        # 保存设置
        if st.button("保存设置"):
            config_manager.set("download_settings.default_max_pages", default_max_pages)
            config_manager.set("download_settings.auto_save", auto_save)
            config_manager.set("query_settings.show_charts", show_charts)
            config_manager.set("query_settings.result_limit", result_limit)
            
            st.success("✅ 设置已保存") 