from openai import OpenAI
from biddingcsg.utils.logger import logger
from biddingcsg.llm.prompts import SYS_BIDDING_SUMMARY_PROMPT, SYS_PRICE_EXTRACTION_PROMPT
from biddingcsg.utils.realtimelog import add_realtime_log
import biddingcsg.config.global_config as config

class UnifiedLLMClient:
    """统一的LLM调用客户端，支持多种模型提供商"""
    
    def __init__(self, provider=None, model=None, api_key=None, base_url=None):
        """
        初始化统一LLM客户端
        
        Args:
            provider: 模型提供商 (DEEPSEEK, DOUBAO, SILICONFLOW)
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
        """
        self.provider = provider or self._get_default_provider()
        self.provider_config = config.PROVIDERS.get(self.provider, {})
        
        # 使用传入参数或配置文件中的默认值
        self.model = model or self.provider_config.get("MODEL", "deepseek-chat")
        self.api_key = api_key or self.provider_config.get("API_KEY")
        self.base_url = base_url or self.provider_config.get("BASE_URL", "")

        logger.info(f"初始化LLM客户端: {self.provider} - {self.model} - {self.api_key} - {self.base_url}")
        
        if not self.api_key:
            logger.warning(f"模型 {self.provider} 的API密钥未配置，请设置环境变量 {self.provider_config.get('API_KEY_ENV', '')}")
            
        # 初始化OpenAI客户端
        self.client = None
        if self.api_key and self.base_url:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                logger.error(f"初始化OpenAI客户端失败: {e}")
    
    def _get_default_provider(self):
        """获取默认的模型提供商，优先级：DEEPSEEK > DOUBAO > SILICONFLOW"""
        priority_order = ["DEEPSEEK", "DOUBAO", "SILICONFLOW"]
        
        for provider_key in priority_order:
            if provider_key in config.PROVIDERS and config.PROVIDERS[provider_key].get("API_KEY"):
                return provider_key
        
        # 如果没有配置API密钥的提供商，返回第一个可用的
        if config.PROVIDERS:
            return next(iter(config.PROVIDERS))
        
        return "DEEPSEEK"  # 兜底默认值
    
    def chat(self, user_prompt, system_prompt="你是人工智能助手", temperature=0.3, max_tokens=2000, timeout=30, status_callback=None):
        """
        统一的聊天接口
        
        Args:
            user_prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 生成温度
            max_tokens: 最大生成长度
            timeout: 超时时间
            status_callback: 状态更新回调函数，用于实时显示streaming内容
            
        Returns:
            str: 模型回复内容
        """
        if not self.client:
            logger.error(f"模型 {self.provider} 客户端未初始化，请检查配置")
            if status_callback:
                status_callback(f"❌ 模型 {self.provider} 客户端未初始化")
            return None
        
        try:
            logger.info(f"调用 {self.provider} 模型: {self.model}")
            if status_callback:
                status_callback(f"🚀 开始调用 {self.provider} 模型...")
            
            full_content = ""
            chunk_count = 0
            
            for chunk in self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                stream=True
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    chunk_count += 1
                    
                    # 实时更新状态显示
                    if status_callback:
                        # 显示最新的内容片段，限制长度避免界面混乱
                        display_content = content.strip()
                        if len(display_content) > 50:
                            display_content = display_content[:47] + "..."
                        
                        # 显示累计内容长度和当前片段
                        # status_callback(f"💭 {self.provider} 推理中...\n块{chunk_count}: `{display_content}`\n总长度: {len(full_content)}字符")
                        status_callback(f"💭 {full_content}")
                    add_realtime_log(f"{content}")
            if full_content:
                content = full_content.strip()
                logger.info(f"模型 {self.provider} 调用成功，返回内容长度: {len(content)}")
                if status_callback:
                    status_callback(f"✅ {self.provider} 推理完成\n总长度: {len(content)}字符，共{chunk_count}个块")
                return content
            else:
                logger.warning(f"模型 {self.provider} 返回空内容")
                if status_callback:
                    status_callback(f"⚠️ {self.provider} 返回空内容")
                return None
                
        except Exception as e:
            logger.error(f"调用模型 {self.provider} 失败: {e}")
            if status_callback:
                status_callback(f"❌ {self.provider} 调用失败: {str(e)}")
            return None
    
    def is_available(self):
        """检查当前模型是否可用"""
        return self.client is not None and self.api_key is not None

class LLMHelper:
    """LLM助手类，提供统一的模型调用接口"""
    
    _llm_client = None
    _global_status_callback = None
    
    @classmethod
    def get_llm_client(cls):
        """获取或创建LLM客户端实例"""
        if cls._llm_client is None:
            cls._llm_client = UnifiedLLMClient()
        return cls._llm_client
    
    @classmethod
    def set_llm_client(cls, provider=None, model=None, api_key=None, base_url=None):
        """设置LLM客户端配置"""
        cls._llm_client = UnifiedLLMClient(provider, model, api_key, base_url)
    
    @classmethod
    def set_global_status_callback(cls, callback):
        """设置全局状态回调函数"""
        cls._global_status_callback = callback
        logger.info("已设置全局LLM状态回调")
    
    @classmethod
    def clear_global_status_callback(cls):
        """清除全局状态回调函数"""
        cls._global_status_callback = None
        logger.info("已清除全局LLM状态回调")
    
    @staticmethod
    def llm_basic_info_extract(user_prompt, status_callback=None):
        """
        调用模型提取基本信息
        
        Args:
            user_prompt: 用户输入的提示词
            status_callback: 状态更新回调函数
            
        Returns:
            str: 提取的基本信息
        """
        try:
            # 确保LLM客户端已初始化
            LLMHelper.ensure_initialized()
            
            # 使用传入的回调或全局回调
            callback = status_callback or LLMHelper._global_status_callback
            
            if callback:
                callback("🔍 准备提取基本信息...")
            
            # 优先尝试使用配置的统一模型
            llm_client = LLMHelper.get_llm_client()
            if llm_client.is_available():
                result = llm_client.chat(
                    user_prompt=str(user_prompt),
                    system_prompt=SYS_BIDDING_SUMMARY_PROMPT,
                    temperature=0.1,
                    status_callback=callback
                )
                if result:
                    return result
            
            # 备选方案：如果统一模型不可用，返回None
            logger.warning("统一模型不可用，无法提取基本信息")
            if callback:
                callback("⚠️ 统一模型不可用，无法提取基本信息")
            return None
            
        except Exception as ex:
            logger.error(f"llm_basic_info_extract 调用模型出错, 错误信息: {ex}")
            if callback:
                callback(f"❌ 基本信息提取失败: {str(ex)}")
            return None

    @staticmethod
    def llm_summary(user_prompt, status_callback=None):
        """
        调用模型总结内容
        
        Args:
            user_prompt: 用户输入的提示词
            status_callback: 状态更新回调函数
            
        Returns:
            str: 总结内容
        """
        try:
            # 确保LLM客户端已初始化
            LLMHelper.ensure_initialized()
            
            # 使用传入的回调或全局回调
            callback = status_callback or LLMHelper._global_status_callback
            
            if callback:
                callback("📝 准备内容总结...")
            
            llm_client = LLMHelper.get_llm_client()
            if llm_client.is_available():
                return llm_client.chat(
                    user_prompt=str(user_prompt),
                    system_prompt=SYS_BIDDING_SUMMARY_PROMPT,
                    temperature=0.1,
                    status_callback=callback
                )
            else:
                logger.warning("统一模型不可用，无法执行内容总结")
                if callback:
                    callback("⚠️ 统一模型不可用，无法执行内容总结")
                return None
                
        except Exception as ex:
            logger.warning(f"llm_summary 调用模型出错, 错误信息: {ex}")
            if callback:
                callback(f"❌ 内容总结失败: {str(ex)}")
            return None

    @staticmethod
    def llm_price_extract(user_prompt, status_callback=None):
        """
        调用模型提取价格信息
        
        Args:
            user_prompt: 用户输入的提示词
            status_callback: 状态更新回调函数
            
        Returns:
            str: 提取的价格信息
        """
        try:
            # 确保LLM客户端已初始化
            LLMHelper.ensure_initialized()
            
            # 使用传入的回调或全局回调
            callback = status_callback or LLMHelper._global_status_callback
            
            if callback:
                callback("💰 准备价格信息提取...")
            
            llm_client = LLMHelper.get_llm_client()
            if llm_client.is_available():
                return llm_client.chat(
                    user_prompt=str(user_prompt),
                    system_prompt=SYS_PRICE_EXTRACTION_PROMPT,
                    temperature=0.1,
                    status_callback=callback
                )
            else:
                logger.warning("统一模型不可用，无法执行价格提取")
                if callback:
                    callback("⚠️ 统一模型不可用，无法执行价格提取")
                return None
                
        except Exception as ex:
            logger.warning(f"llm_price_extract 调用模型出错, 错误信息: {ex}")
            if callback:
                callback(f"❌ 价格提取失败: {str(ex)}")
            return None
    
    @staticmethod
    def switch_provider(provider):
        """
        切换模型提供商
        
        Args:
            provider: 新的模型提供商 (DEEPSEEK, DOUBAO, SILICONFLOW)
        """
        try:
            if provider in config.PROVIDERS:
                LLMHelper.set_llm_client(provider=provider)
                logger.info(f"已切换到模型提供商: {provider}")
            else:
                logger.error(f"未知的模型提供商: {provider}")
        except Exception as e:
            logger.error(f"切换模型提供商失败: {e}")
    
    @staticmethod
    def initialize_from_config_manager():
        """
        从配置管理器初始化LLM客户端
        
        该方法会尝试导入 BiddingCSG 配置管理器并使用配置的模型
        """
        try:
            # 尝试导入 BiddingCSG 配置管理器
            from biddingcsg.config.config_manager import get_biddingcsg_config_manager
            
            config_manager = get_biddingcsg_config_manager()
            current_model = config_manager.get_current_model_info()
            
            # 使用配置管理器中选择的模型
            LLMHelper.set_llm_client(provider=current_model["provider"])
            logger.info(f"已从BiddingCSG配置初始化模型: {current_model['provider']} - {current_model['model']}")
            
        except ImportError:
            # 如果配置管理器不可用，使用默认配置
            logger.info("BiddingCSG配置管理器不可用，使用默认模型配置")
            LLMHelper._llm_client = UnifiedLLMClient()
        except Exception as e:
            logger.warning(f"从BiddingCSG配置初始化失败: {e}，使用默认配置")
            LLMHelper._llm_client = UnifiedLLMClient()
    
    @staticmethod 
    def ensure_initialized():
        """
        确保LLM客户端已初始化
        
        该方法会检查客户端是否已初始化，如果没有则尝试从配置管理器初始化
        """
        if LLMHelper._llm_client is None:
            LLMHelper.initialize_from_config_manager()