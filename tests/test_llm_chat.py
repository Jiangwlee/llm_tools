"""
单元测试：测试 biddingcsg.llm.chat 模块
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.biddingcsg.llm.chat import UnifiedLLMClient, LLMHelper


class TestUnifiedLLMClient(unittest.TestCase):
    """测试 UnifiedLLMClient 类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # Mock 配置
        self.mock_config = {
            'PROVIDERS': {
                'DEEPSEEK': {
                    'MODEL': 'deepseek-chat',
                    'API_KEY': 'test-deepseek-key',
                    'BASE_URL': 'https://api.deepseek.com/v1',
                    'API_KEY_ENV': 'DEEPSEEK_API_KEY'
                },
                'DOUBAO': {
                    'MODEL': 'doubao-lite-4k',
                    'API_KEY': 'test-doubao-key',
                    'BASE_URL': 'https://ark.cn-beijing.volces.com/api/v3',
                    'API_KEY_ENV': 'DOUBAO_API_KEY'
                },
                'SILICONFLOW': {
                    'MODEL': 'deepseek-ai/deepseek-chat',
                    'API_KEY': 'test-sf-key',
                    'BASE_URL': 'https://api.siliconflow.cn/v1',
                    'API_KEY_ENV': 'SILICONFLOW_API_KEY'
                }
            }
        }
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_init_with_default_provider(self, mock_logger, mock_config):
        """测试使用默认提供商初始化"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        with patch('src.biddingcsg.llm.chat.OpenAI') as mock_openai:
            client = UnifiedLLMClient()
            
            self.assertEqual(client.provider, 'DEEPSEEK')
            self.assertEqual(client.model, 'deepseek-chat')
            self.assertEqual(client.api_key, 'test-deepseek-key')
            self.assertEqual(client.base_url, 'https://api.deepseek.com/v1')
            mock_openai.assert_called_once()
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_init_with_specific_provider(self, mock_logger, mock_config):
        """测试使用特定提供商初始化"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        with patch('src.biddingcsg.llm.chat.OpenAI') as mock_openai:
            client = UnifiedLLMClient(provider='DOUBAO')
            
            self.assertEqual(client.provider, 'DOUBAO')
            self.assertEqual(client.model, 'doubao-lite-4k')
            self.assertEqual(client.api_key, 'test-doubao-key')
            self.assertEqual(client.base_url, 'https://ark.cn-beijing.volces.com/api/v3')
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_init_with_missing_api_key(self, mock_logger, mock_config):
        """测试缺少API密钥时的初始化"""
        mock_config_without_key = {
            'PROVIDERS': {
                'DEEPSEEK': {
                    'MODEL': 'deepseek-chat',
                    'API_KEY': None,
                    'BASE_URL': 'https://api.deepseek.com/v1',
                    'API_KEY_ENV': 'DEEPSEEK_API_KEY'
                }
            }
        }
        mock_config.PROVIDERS = mock_config_without_key['PROVIDERS']
        
        client = UnifiedLLMClient()
        
        self.assertIsNone(client.client)
        mock_logger.warning.assert_called()
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_get_default_provider_priority(self, mock_logger, mock_config):
        """测试默认提供商的优先级选择"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        client = UnifiedLLMClient()
        result = client._get_default_provider()
        
        # 应该选择第一个有API密钥的提供商（DEEPSEEK）
        self.assertEqual(result, 'DEEPSEEK')
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_chat_success(self, mock_logger, mock_config):
        """测试成功的聊天调用"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        # Mock OpenAI 客户端和响应
        mock_client = Mock()
        mock_response_chunks = [
            Mock(choices=[Mock(delta=Mock(content="Hello "))]),
            Mock(choices=[Mock(delta=Mock(content="world!"))]),
            Mock(choices=[Mock(delta=Mock(content=None))])  # 结束块
        ]
        mock_client.chat.completions.create.return_value = iter(mock_response_chunks)
        
        with patch('src.biddingcsg.llm.chat.OpenAI', return_value=mock_client):
            client = UnifiedLLMClient()
            
            # Mock 状态回调
            status_callback = Mock()
            
            result = client.chat(
                user_prompt="Hello",
                system_prompt="You are a helpful assistant",
                status_callback=status_callback
            )
            
            self.assertEqual(result, "Hello world!")
            self.assertTrue(status_callback.called)
            mock_client.chat.completions.create.assert_called_once()
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_chat_no_client(self, mock_logger, mock_config):
        """测试客户端未初始化时的聊天调用"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        client = UnifiedLLMClient()
        client.client = None  # 模拟客户端未初始化
        
        status_callback = Mock()
        result = client.chat(
            user_prompt="Hello",
            status_callback=status_callback
        )
        
        self.assertIsNone(result)
        status_callback.assert_called_with("❌ 模型 DEEPSEEK 客户端未初始化")
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_chat_api_error(self, mock_logger, mock_config):
        """测试API调用异常时的处理"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        # Mock OpenAI 客户端抛出异常
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        with patch('src.biddingcsg.llm.chat.OpenAI', return_value=mock_client):
            client = UnifiedLLMClient()
            
            status_callback = Mock()
            result = client.chat(
                user_prompt="Hello",
                status_callback=status_callback
            )
            
            self.assertIsNone(result)
            mock_logger.error.assert_called()
            status_callback.assert_called()
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_is_available(self, mock_logger, mock_config):
        """测试客户端可用性检查"""
        mock_config.PROVIDERS = self.mock_config['PROVIDERS']
        
        with patch('src.biddingcsg.llm.chat.OpenAI') as mock_openai:
            client = UnifiedLLMClient()
            self.assertTrue(client.is_available())
            
            # 测试客户端不可用的情况
            client.client = None
            self.assertFalse(client.is_available())
            
            # 测试API密钥不可用的情况
            client.api_key = None
            self.assertFalse(client.is_available())


class TestLLMHelper(unittest.TestCase):
    """测试 LLMHelper 类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 重置类变量
        LLMHelper._llm_client = None
        LLMHelper._global_status_callback = None
    
    def tearDown(self):
        """测试后的清理工作"""
        # 重置类变量
        LLMHelper._llm_client = None
        LLMHelper._global_status_callback = None
    
    @patch('src.biddingcsg.llm.chat.UnifiedLLMClient')
    def test_get_llm_client_singleton(self, mock_client_class):
        """测试LLM客户端的单例模式"""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        # 第一次调用应该创建新实例
        client1 = LLMHelper.get_llm_client()
        self.assertEqual(client1, mock_instance)
        
        # 第二次调用应该返回同一实例
        client2 = LLMHelper.get_llm_client()
        self.assertEqual(client1, client2)
        
        # 应该只调用一次构造函数
        mock_client_class.assert_called_once()
    
    @patch('src.biddingcsg.llm.chat.UnifiedLLMClient')
    def test_set_llm_client(self, mock_client_class):
        """测试设置LLM客户端"""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        LLMHelper.set_llm_client(provider='DOUBAO', model='test-model')
        
        mock_client_class.assert_called_with('DOUBAO', 'test-model', None, None)
        self.assertEqual(LLMHelper._llm_client, mock_instance)
    
    def test_set_global_status_callback(self):
        """测试设置全局状态回调"""
        callback = Mock()
        
        with patch('src.biddingcsg.llm.chat.logger') as mock_logger:
            LLMHelper.set_global_status_callback(callback)
            
            self.assertEqual(LLMHelper._global_status_callback, callback)
            mock_logger.info.assert_called_with("已设置全局LLM状态回调")
    
    def test_clear_global_status_callback(self):
        """测试清除全局状态回调"""
        # 先设置一个回调
        LLMHelper._global_status_callback = Mock()
        
        with patch('src.biddingcsg.llm.chat.logger') as mock_logger:
            LLMHelper.clear_global_status_callback()
            
            self.assertIsNone(LLMHelper._global_status_callback)
            mock_logger.info.assert_called_with("已清除全局LLM状态回调")
    
    def test_llm_basic_info_extract_success(self):
        """测试基本信息提取成功"""
        # Mock LLM客户端
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.chat.return_value = "提取的基本信息"
        
        with patch.object(LLMHelper, 'get_llm_client', return_value=mock_client), \
             patch.object(LLMHelper, 'ensure_initialized'):
            
            status_callback = Mock()
            result = LLMHelper.llm_basic_info_extract("测试输入", status_callback)
            
            self.assertEqual(result, "提取的基本信息")
            mock_client.chat.assert_called_once()
            status_callback.assert_called()
    
    @patch('src.biddingcsg.llm.chat.logger')
    def test_llm_basic_info_extract_fallback(self, mock_logger):
        """测试基本信息提取降级处理"""
        # Mock LLM客户端不可用
        mock_client = Mock()
        mock_client.is_available.return_value = False
        
        with patch.object(LLMHelper, 'get_llm_client', return_value=mock_client), \
             patch.object(LLMHelper, 'ensure_initialized'):
            
            status_callback = Mock()
            result = LLMHelper.llm_basic_info_extract("测试输入", status_callback)
            
            # 由于客户端不可用，应该返回 None
            self.assertIsNone(result)
            mock_logger.warning.assert_called()
    
    @patch('src.biddingcsg.llm.chat.SYS_BIDDING_SUMMARY_PROMPT', 'test-summary-prompt')
    def test_llm_summary_success(self):
        """测试内容总结成功"""
        # Mock LLM客户端
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.chat.return_value = "总结内容"
        
        with patch.object(LLMHelper, 'get_llm_client', return_value=mock_client), \
             patch.object(LLMHelper, 'ensure_initialized'):
            
            status_callback = Mock()
            result = LLMHelper.llm_summary("测试输入", status_callback)
            
            self.assertEqual(result, "总结内容")
            mock_client.chat.assert_called_once()
    
    @patch('src.biddingcsg.llm.chat.SYS_PRICE_EXTRACTION_PROMPT', 'test-price-prompt')
    def test_llm_price_extract_success(self):
        """测试价格提取成功"""
        # Mock LLM客户端
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.chat.return_value = "价格: 1000元"
        
        with patch.object(LLMHelper, 'get_llm_client', return_value=mock_client), \
             patch.object(LLMHelper, 'ensure_initialized'):
            
            status_callback = Mock()
            result = LLMHelper.llm_price_extract("测试输入", status_callback)
            
            self.assertEqual(result, "价格: 1000元")
            mock_client.chat.assert_called_once()
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_switch_provider_success(self, mock_logger, mock_config):
        """测试切换模型提供商成功"""
        mock_config.PROVIDERS = {'DOUBAO': {}}
        
        with patch.object(LLMHelper, 'set_llm_client') as mock_set_client:
            LLMHelper.switch_provider('DOUBAO')
            
            mock_set_client.assert_called_with(provider='DOUBAO')
            mock_logger.info.assert_called_with("已切换到模型提供商: DOUBAO")
    
    @patch('src.biddingcsg.llm.chat.config')
    @patch('src.biddingcsg.llm.chat.logger')
    def test_switch_provider_unknown(self, mock_logger, mock_config):
        """测试切换到未知的模型提供商"""
        mock_config.PROVIDERS = {}
        
        LLMHelper.switch_provider('UNKNOWN')
        
        mock_logger.error.assert_called_with("未知的模型提供商: UNKNOWN")
    
    @patch('src.biddingcsg.llm.chat.logger')
    def test_initialize_from_config_manager_success(self, mock_logger):
        """测试从配置管理器初始化成功"""
        # Mock 配置管理器
        mock_config_manager = Mock()
        mock_config_manager.get_current_model_info.return_value = {
            'provider': 'DEEPSEEK',
            'model': 'deepseek-chat'
        }
        
        # Mock 模块导入和函数调用
        mock_module = Mock()
        mock_module.get_biddingcsg_config_manager = Mock(return_value=mock_config_manager)
        
        with patch.dict('sys.modules', {'biddingcsg.config.config_manager': mock_module}), \
             patch.object(LLMHelper, 'set_llm_client') as mock_set_client:
            
            LLMHelper.initialize_from_config_manager()
            
            mock_set_client.assert_called_with(provider='DEEPSEEK')
            mock_logger.info.assert_called()
    
    @patch('src.biddingcsg.llm.chat.logger')
    @patch('src.biddingcsg.llm.chat.UnifiedLLMClient')
    def test_initialize_from_config_manager_fallback(self, mock_client_class, mock_logger):
        """测试配置管理器不可用时的降级处理"""
        # Mock 导入错误 - 使 sys.modules 中不存在该模块
        original_modules = sys.modules.copy()
        if 'biddingcsg.config.config_manager' in sys.modules:
            del sys.modules['biddingcsg.config.config_manager']
        
        try:
            LLMHelper.initialize_from_config_manager()
            
            mock_client_class.assert_called_once()
            mock_logger.info.assert_called_with("BiddingCSG配置管理器不可用，使用默认模型配置")
        finally:
            # 恢复原始模块状态
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def test_ensure_initialized(self):
        """测试确保客户端已初始化"""
        # 客户端为空时应该调用初始化
        LLMHelper._llm_client = None
        
        with patch.object(LLMHelper, 'initialize_from_config_manager') as mock_init:
            LLMHelper.ensure_initialized()
            mock_init.assert_called_once()
        
        # 客户端已存在时不应该重复初始化
        LLMHelper._llm_client = Mock()
        
        with patch.object(LLMHelper, 'initialize_from_config_manager') as mock_init:
            LLMHelper.ensure_initialized()
            mock_init.assert_not_called()


if __name__ == '__main__':
    unittest.main() 