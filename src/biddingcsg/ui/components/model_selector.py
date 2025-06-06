"""
模型选择器组件

提供模型选择、状态显示和连接测试功能。
"""

import streamlit as st
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from biddingcsg.config import get_biddingcsg_config_manager
from biddingcsg.llm.chat import LLMHelper
from biddingcsg.utils.logger import get_logger

logger = get_logger(__name__)


class ModelSelector:
    """模型选择器组件"""
    
    def __init__(self):
        """初始化模型选择器"""
        self.config_manager = get_biddingcsg_config_manager()
    
    def render_sidebar_selector(self) -> None:
        """在侧边栏渲染模型选择器"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🤖 模型配置")
        
        # 获取当前模型信息
        current_model = self.config_manager.get_current_model_info()
        
        # 显示当前模型状态
        with st.sidebar:
            if current_model["available"]:
                st.success(f"✅ 当前模型: {current_model['display_name']}")
            else:
                st.warning(f"⚠️ 当前模型: {current_model['display_name']}")
                st.caption("API密钥未配置")
        
        # 模型选择区域
        self._render_model_selector()
        
        # 连接测试区域
        self._render_connection_test()
        
        # 配置管理区域
        self._render_config_management()
    
    def _render_model_selector(self) -> None:
        """渲染模型选择器"""
        # 获取可用的模型提供商
        from biddingcsg.config import global_config
        
        if not global_config.PROVIDERS:
            st.sidebar.error("❌ 未找到可用的模型提供商配置")
            return
        
        # 创建模型选项
        model_options = []
        model_mapping = {}
        
        current_model = self.config_manager.get_current_model_info()
        current_index = 0
        
        for i, (provider_key, provider_config) in enumerate(global_config.PROVIDERS.items()):
            # 检查是否有API密钥
            has_api_key = bool(provider_config.get("API_KEY"))
            status_icon = "✅" if has_api_key else "❌"
            
            # 创建显示名称
            model_name = provider_config.get("MODEL", "unknown")
            display_name = f"{status_icon} {provider_key} - {model_name}"
            
            model_options.append(display_name)
            model_mapping[display_name] = {
                "provider": provider_key,
                "model": model_name,
                "available": has_api_key
            }
            
            # 找到当前选择的索引
            if provider_key == current_model["provider"]:
                current_index = i
        
        # 模型选择下拉框
        selected_option = st.sidebar.selectbox(
            "选择模型",
            options=model_options,
            index=current_index,
            help="选择要使用的大语言模型"
        )
        
        # 处理模型切换
        if selected_option in model_mapping:
            selected_info = model_mapping[selected_option]
            
            # 检查是否需要切换
            if selected_info["provider"] != current_model["provider"]:
                self._switch_model(selected_info["provider"], selected_info["model"])
    
    def _render_connection_test(self) -> None:
        """渲染连接测试区域"""
        st.sidebar.markdown("#### 🔌 连接测试")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("测试连接", help="测试当前模型的连通性", use_container_width=True):
                self._test_current_model()
        
        with col2:
            if st.button("刷新状态", help="刷新模型状态", use_container_width=True):
                st.rerun()
    
    def _render_config_management(self) -> None:
        """渲染配置管理区域"""
        with st.sidebar.expander("⚙️ 配置管理"):
            col1, col2 = st.sidebar.columns(2)
            
            with col1:
                if st.button("重置配置", help="重置为默认配置"):
                    if self.config_manager.reset_to_default():
                        st.success("✅ 配置已重置")
                        st.rerun()
            
            with col2:
                if st.button("查看配置", help="查看当前配置"):
                    self._show_config_details()
            
            # 显示配置文件位置
            st.caption(f"配置文件: `{self.config_manager.config_file}`")
    
    def _switch_model(self, provider: str, model: str) -> None:
        """切换模型"""
        try:
            # 更新配置
            self.config_manager.config_data["default_model"] = {
                "provider": provider,
                "name": model
            }
            
            # 保存配置
            if self.config_manager.save_config():
                # 重新初始化LLM客户端
                LLMHelper.set_llm_client(provider=provider, model=model)
                
                st.sidebar.success(f"✅ 已切换到: {provider} - {model}")
                logger.info(f"模型已切换: {provider} - {model}")
                
                # 刷新页面以更新状态
                st.rerun()
            else:
                st.sidebar.error("❌ 保存配置失败")
                
        except Exception as e:
            st.sidebar.error(f"❌ 切换模型失败: {str(e)}")
            logger.error(f"切换模型失败: {e}")
    
    def _test_current_model(self) -> None:
        """测试当前模型连接"""
        current_model = self.config_manager.get_current_model_info()
        
        if not current_model["available"]:
            st.sidebar.error("❌ 当前模型API密钥未配置")
            return
        
        with st.sidebar:
            with st.spinner("正在测试连接..."):
                try:
                    # 确保LLM客户端已初始化
                    LLMHelper.ensure_initialized()
                    
                    # 获取LLM客户端
                    llm_client = LLMHelper.get_llm_client()
                    
                    if not llm_client.is_available():
                        st.error("❌ LLM客户端不可用")
                        return
                    
                    # 进行简单的测试调用
                    response = llm_client.chat(
                        user_prompt="你好，请简单回复确认连接正常",
                        system_prompt="你是一个AI助手，请简洁回复",
                        max_tokens=50,
                        timeout=10
                    )
                    
                    if response:
                        st.success("✅ 连接测试成功！")
                        st.info(f"🤖 **{current_model['display_name']}**\n\n"
                               f"💬 测试回复: {response[:100]}{'...' if len(response) > 100 else ''}")
                        logger.info(f"模型连接测试成功: {current_model['provider']}")
                    else:
                        st.error("❌ 模型无响应")
                        
                except Exception as e:
                    st.error(f"❌ 连接测试失败: {str(e)}")
                    logger.error(f"模型连接测试失败: {e}")
    
    def _show_config_details(self) -> None:
        """显示配置详情"""
        st.sidebar.markdown("**当前配置:**")
        config_data = self.config_manager.config_data
        
        # 显示默认模型配置
        default_model = config_data.get("default_model", {})
        st.sidebar.code(f"""
提供商: {default_model.get("provider", "未设置")}
模型: {default_model.get("name", "未设置")}
        """)
    
    def get_current_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息（供外部使用）"""
        return self.config_manager.get_current_model_info()


# 全局模型选择器实例
_model_selector = None


def get_model_selector() -> ModelSelector:
    """获取全局模型选择器实例（单例模式）"""
    global _model_selector
    if _model_selector is None:
        _model_selector = ModelSelector()
    return _model_selector 