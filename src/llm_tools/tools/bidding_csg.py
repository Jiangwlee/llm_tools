import re
import csv
import random
import json
import time
from openai import OpenAI
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from llm_tools.connector import getConnection
from llm_tools.logger import get_logger
from llm_tools.utils.number_util import is_number
from llm_tools.tools.deepseek import deepseek_chat
from llm_tools.tools.coze import coze_chat
from llm_tools.tools.prompts import SYS_BIDDING_SUMMARY_PROMPT, SYS_PRICE_EXTRACTION_PROMPT
from llm_tools.tools.ollama_chat import extract_bidding_info
from llm_tools import config
from dataclasses import dataclass

logger = get_logger()

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
                    
                    logger.info(f"收到模型 {self.provider} 的响应片段: {content}")
            
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
            
            # 备选方案：使用本地ollama模型
            logger.info("统一模型不可用，尝试使用本地ollama模型")
            if callback:
                callback("🔄 使用本地ollama模型...")
            return extract_bidding_info(str(user_prompt))
            
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
        从Web UI配置管理器初始化LLM客户端
        
        该方法会尝试导入配置管理器并使用用户在Web UI中选择的模型配置
        """
        try:
            # 尝试导入Web UI配置管理器
            from llm_tools.web_ui.config_manager import get_config_manager
            
            config_manager = get_config_manager()
            current_model = config_manager.get_current_model_info()
            
            # 使用Web UI中配置的模型
            LLMHelper.set_llm_client(provider=current_model["provider"])
            logger.info(f"已从Web UI配置初始化模型: {current_model['provider']} - {current_model['model']}")
            
        except ImportError:
            # 如果Web UI配置管理器不可用，使用默认配置
            logger.info("Web UI配置管理器不可用，使用默认模型配置")
            LLMHelper._llm_client = UnifiedLLMClient()
        except Exception as e:
            logger.warning(f"从Web UI配置初始化失败: {e}，使用默认配置")
            LLMHelper._llm_client = UnifiedLLMClient()
    
    @staticmethod 
    def ensure_initialized():
        """
        确保LLM客户端已初始化
        
        该方法会检查客户端是否已初始化，如果没有则尝试从配置管理器初始化
        """
        if LLMHelper._llm_client is None:
            LLMHelper.initialize_from_config_manager()

class BiddingParser:
    def __init__(self, html: str):
        self.html_text = html

    def parse_announcement(self):
        """
        解析HTML文本，提取表格数据。

        该方法用于从HTML文本中提取招标公告中的表格数据。

        参数：
            无

        返回值：
            dict: 包含所有表格数据的字典。
                  字典的结构如下：
                  {
                      "tables": list[list[str]]
                  }
                  其中，"tables" 键对应的值是一个列表，列表中的每个元素又是一个列表，
                  表示一个表格的数据。每个表格数据列表中的元素是字符串，表示表格中的一个单元格的数据。
        """
        soup = BeautifulSoup(self.html_text, 'html.parser')
        tables = soup.findAll('table') # 找到内容部分

        all_table_data = []
        for t in tables:
            rows = t.findAll('tr')
            table_data = []
            # parse <td>
            prev_row = None
            for r in rows:
                columns = r.findAll('td')
                col_text = [c.text for c in columns]
                if prev_row is not None and len(prev_row) > len(col_text):
                    leading = prev_row[:(len(prev_row) - len(col_text))]
                    leading.extend(col_text)
                    col_text = leading
                table_data.append(col_text)
                prev_row = col_text
                print(', '.join(col_text))
            all_table_data.append(table_data)
        return {
            "tables": all_table_data
        }

    def parse_bid_price(self):
        """
        从解析后的公告中提取标的、标包和价格信息。

        该方法用于从解析后的招标公告数据中提取标的、标包和价格信息。

        参数：
            无

        返回值：
            list[dict]: 包含标的、标包和价格信息的列表。
                      列表中的每个元素是一个字典，字典的结构如下：
                      {
                          "subject": str,  # 标的名称
                          "package": str,  # 标包名称
                          "price": str     # 价格
                      }
        """
        announcement = self.parse_announcement()
        result = []
        for table in announcement['tables']:
            subject_index = None
            package_index = None
            price_index = None
            header = table[0]
            for i in range(0, len(header)):
                if self.is_subject(header[i]):
                    subject_index = i
                    continue
                if self.is_package(header[i]):
                    package_index = i
                    continue
                if self.is_max_price(header[i]):
                    price_index = i
            if subject_index is None or package_index is None or price_index is None:
                subject_index = None
                package_index = None
                price_index = None
                continue
            # 找到了中标信息表
            logger.info(table)
            for i in range(1, len(table)):
                print(i)
                row = table[i]
                result.append({
                    "subject": row[subject_index],
                    "package": row[package_index],
                    'price': row[price_index]
                })
        return result
            

    def is_subject(self, text: str):
        return text.startswith('标的')

    def is_package(self, text: str):
        return text.startswith('标包名称')

    def is_max_price(self, text: str):
        return text.startswith('最高限价')

class BiddingCSG:
    """
    不要使用 requests, 目标网站有爬虫检测, 简单爬虫容易被检测到, 导致封 IP.
    """
    def __init__(self, verbose=False):
        """初始化 Playwright 和浏览器实例"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not verbose, args=["--disable-blink-features=AutomationControlled"])  # 设置为 False 以便调试
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.prev_page = None
        self.bidding_list = []
        self.filtered_list = []
        self.end_date = None
        self.stop_crawl = True

    def search(self, keyword, max_page=65535, end_date=None, query_url=None):
        """
        检索公告。

        该方法用于在南方电网的招标网站上搜索招标公告。

        参数：
            keyword (str): 检索关键字。
            max_page (int, 可选): 最大爬取页数，默认为 65535。
            end_date (str, 可选): 要爬取公告的结束日期，格式为 "YYYY-MM-DD"，默认为 None。
            query_url (str, 可选): 检索页面地址，默认为 "https://www.bidding.csg.cn/dbsearch.jspx?q="。

        返回值：
            None
        """
        self.stop_crawl = False
        self.end_date = end_date
        start_url = f"https://www.bidding.csg.cn/dbsearch.jspx?q=" if query_url is None else query_url
        self.page.goto(start_url, wait_until='load')

        # 填入搜索关键字
        self.page.fill("input[id='txtKey']", keyword)
        # 选择公告类型
        self.page.select_option('#types', value='服务')
        
        # 假设点击一个按钮会打开新标签页
        with self.page.expect_popup() as popup_info:
            self.page.click("input[class='seachBtn']")

        self.prev_page = self.page
        self.page = popup_info.value
        self.page.locator('div.List2').wait_for(state='visible')

        # 在新标签页中操作
        logger.info(self.page.title())
        logger.info(self.page.url)
        
        # 过滤页数信息, 正则表达式
        pattern = r"共(\d+)条记录\s+(\d+)/(\d+)页"

        # 匹配内容
        match = re.search(pattern, self.page.content())

        if match:
            total_records = match.group(1)  # 总记录数
            current_page = match.group(2)   # 当前页
            total_pages = match.group(3)    # 总页数
            logger.info(f"总记录数: {total_records}")
            logger.info(f"当前页: {current_page}")
            logger.info(f"总页数: {total_pages}")
        else:
            print("未找到匹配的内容")

        # 解析页面
        self.parse(self.page.content())
        count = 1
        while count < max_page:
            logger.info(f"正在处理第【{count}】页")
            self.next_page()
            next_page_tag = self.page.locator('text=下一页')
            if next_page_tag.get_attribute('disabled') == 'disabled':
                logger.info("已处理完全部页面")
                break
            if self.stop_crawl:
                logger.info("爬取结束")
                break
            count += 1

    def next_page(self):
        """
        打开下一页。

        该方法用于在招标网站上打开下一页搜索结果。

        参数：
            无

        返回值：
            None
        """
        # 打开下一页
        self.page.click('text=下一页')
        self.page.wait_for_load_state('load')
        self.page.locator('div.List2').wait_for(state='visible')
        self.parse(self.page.content())

    def parse(self, content_text):
        """
        解析搜索结果页面的HTML内容，提取招标公告的信息。

        该方法用于解析搜索结果页面的HTML内容，提取招标公告的类型、甲方、项目名称、日期和链接等信息，
        并将信息存储在 self.bidding_list 列表中。

        参数：
            content_text (str): 包含搜索结果的HTML文本。

        返回值：
            str: 如果解析成功，则返回空字符串 ""。如果未找到正文内容或发生异常，则返回空字符串 ""。
        """
        try:
            # 解析网页内容
            soup = BeautifulSoup(content_text, 'html.parser')

            # 查找包含正文内容的 <div> 标签
            content_div = soup.find('div', class_='List2')

            # 提取正文内容
            if content_div:
                for item in content_div.find_all("li"):
                    # print(item)
                    links = item.find_all("a")
                    # print(f"类型：{links[0].text}, 招标方: {links[1].text}, 项目名称: {links[2].text}, 链接：https://www.bidding.csg.cn/{links[2].get('href')}")
                    create_date = item.find('span', class_='Black14 Gray')
                    # print(f"日期: {create_date.text}")
                    if create_date and create_date.text and self.end_date and create_date.text < self.end_date:
                        self.stop_crawl = True
                    else:
                        self.bidding_list.append({
                            "type": links[0].text,
                            "part_a": links[1].text,
                            "project": links[2].text,
                            "date": create_date.text,
                            "url": f"https://www.bidding.csg.cn{links[2].get('href')}"
                        })
            else:
                print(f"未找到正文内容")
                return ""
        except Exception as e:
            print(f"读取内容失败: {e}")
            return ""

    def read_bidding_page(self, url):
        """
        阅读标讯。

        该方法用于读取单个招标公告的详细信息。

        参数：
            url (str): 招标公告的URL。

        返回值：
            dict: 包含招标公告的标题、日期和正文内容的字典。
                  字典的结构如下：
                  {
                      "title": str,    # 招标公告的标题
                      "date": str,     # 招标公告的日期
                      "content": str   # 招标公告的正文内容
                  }
        """
        try:
            self.page.goto(url, wait_until='load')
            self.page.locator('div.s-content').wait_for(state='visible')
            soup = BeautifulSoup(self.page.content(), 'html.parser')

            title_tag = soup.find('h1', class_='s-title')
            date_tag = soup.find('div', class_='s-date')
            content_div = soup.find('div', class_='Content')
            return {
                "title": title_tag.text,
                "date": date_tag.text,
                "content": content_div.text
            }
        except Exception as e:
            logger.error(f"访问链接时发生错误: {url}。 错误信息: {e}")

        self.random_wait()

    def filter(self, keyword, bidding_type=None):
        """
        过滤出包含特定关键字的公告。

        该方法用于从数据库中查找相关的招标公告，并过滤出包含特定关键字（例如 "投标报价"）的公告。

        参数：
            keyword (str): 过滤关键字。
            bidding_type (int, 可选): 公告类型，1=投标报价，2=投标费率。默认为 None。

        返回值：
            None
        """
        bidding_list = self.lookup(keyword)
        update_list = []
        for item in bidding_list:
            try:
                self.page.goto(item['url'], wait_until='load')
                soup = BeautifulSoup(self.page.content(), 'html.parser')
                content_div = soup.find('div', class_='Content')

                title_tag = soup.find('h1', class_='s-title')
                item['project'] = title_tag.text

                basic_info = LLMHelper.llm_basic_info_extract(content_div)
                logger.info(f"Basic information: {basic_info}")

                if bidding_type == 1 or bidding_type is None:
                    found_elements = content_div.find_all(lambda tag: '>投标报价<' in str(tag))
                    if found_elements:
                        logger.info("找到包含 '>投标报价<' 的标签：")
                        logger.info(content_div.text)
                        result = LLMHelper.llm_summary(content_div)
                        logger.info(result)
                        item['summary'] = result
                        update_list.append(item)
                        # break
                if bidding_type == 2 or bidding_type is None:
                    found_elements = content_div.find_all(lambda tag: '>投标费率<' in str(tag))
                    if found_elements:
                        logger.info(f"找到投标费率, 尝试使用大模型提取投标费率. URL: {item['url']}")
                        result = LLMHelper.llm_price_extract(self.page.content())
                        logger.info(f"大模型解读结果: \n{json.dumps(result, indent=2, ensure_ascii=False)}")
                        item['summary'] = result
                        update_list.append(item)
                if (bidding_type == 1 and not content_div.find_all(lambda tag: '>投标报价<' in str(tag))) or (bidding_type == 2 and not content_div.find_all(lambda tag: '>投标费率<' in str(tag))):
                    logger.warning(f"无投标报价和投标费率，跳过此公告.")
            except Exception as e:
                logger.error(f"访问链接时发生错误: {item['url']}")

            self.random_wait()
        self.update(update_list)

    def save_to_db(self):
        """
        将爬取的招标信息保存到数据库中。

        该方法用于将爬取的招标信息保存到数据库中，避免重复爬取相同的信息。

        参数：
            无

        返回值：
            None
        """
        # 插入数据的 SQL 语句
        insert_query = """
        INSERT INTO bidding_csg (type, part_a, project, create_date, url)
        VALUES (%s, %s, %s, %s, %s)
        """

        # 检查 URL 是否存在的 SQL 语句
        check_url_query = """
        SELECT url FROM bidding_csg WHERE url = %s
        """

        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 用于存储唯一的数据
            unique_data_to_insert = []

            for item in self.bidding_list:
                url = item["url"]
                # 检查 URL 是否已存在
                cursor.execute(check_url_query, (url,))
                result = cursor.fetchone()

                if not result:  # 如果 URL 不存在
                    unique_data_to_insert.append((item["type"], item["part_a"], item["project"], item["date"], item["url"]))
                else:
                    logger.info(f"URL 已存在，跳过: {url}")

            # 执行批量插入
            if unique_data_to_insert:
                cursor.executemany(insert_query, unique_data_to_insert)
                connection.commit()
                logger.info(f"成功插入 {cursor.rowcount} 条数据")
            else:
                logger.info("没有新数据需要插入")

        except Exception as e:
            logger.error(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

    def lookup(self, keyword):
        """
        从数据库中查询相关信息.
        """
        # 查询 SQL 语句
        query = """
        SELECT * FROM llm_tools.bidding_csg
        WHERE project LIKE %s
        """

        result = []
        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 执行查询
            cursor.execute(query, (f"%{keyword}%",))  # 使用 % 通配符匹配关键字

            # 获取查询结果
            results = cursor.fetchall()

            # 输出结果
            if results:
                logger.info(f"找到 {len(results)} 条包含关键字 '{keyword}' 的记录：")
                for row in results:
                    result.append({
                        "type": row[2],
                        "part_a": row[1],
                        "project": row[0],
                        "date": row[3],
                        "url": row[4],
                        "summary": row[5],
                        "price": row[6]
                    })
            else:
                logger.info(f"未找到包含关键字 '{keyword}' 的记录。")
            return result
        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

    def update(self, update_list):
        """更新数据库
        """
        # 更新 SQL 语句
        update_query = """
        UPDATE llm_tools.bidding_csg
        SET summary = %s, project = %s, price = %s
        WHERE url = %s
        """

        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            data_to_update = [(item["summary"], item["project"], item["price"], item["url"]) for item in update_list]
            
            # 执行更新
            cursor.executemany(update_query, data_to_update)
            connection.commit()

        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("数据库连接已关闭")

    def dump(self):
        with open('bidding_list.json', 'w', encoding='utf-8') as outfile:
            json.dump(self.bidding_list, outfile, indent=2)
        with open('filtered.json', 'w', encoding='utf-8') as outfile:
            json.dump(self.filtered_list, outfile, indent=2)

    def load(self):
        with open('bidding_list.json', 'r', encoding='utf-8') as infile:
            self.bidding_list = json.load(infile)

        print(f"加载了 {len(self.bidding_list)} 条记录")

    
    def analyze(self, keyword):
        """分析中标价格和招标价格
        """
        # 查询 SQL 语句
        query_final_price = """
        SELECT * FROM llm_tools.bidding_csg
        WHERE summary IS NOT NULL AND project LIKE %s
        """

        results_with_summary = []
        update_list = []
        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 执行查询
            cursor.execute(query_final_price, (f"%{keyword}%",))

            # 获取查询结果
            results = cursor.fetchall()

            # 输出结果
            if results:
                logger.info(f"找到 {len(results)} 条关于 '{keyword}' 的有价格中标记录.")
                for row in results:
                    results_with_summary.append({
                        "type": row[2],
                        "part_a": row[1],
                        "project": row[0],
                        "date": row[3],
                        "url": row[4],
                        "summary": row[5],
                        "price": row[6]
                    })
            else:
                logger.info(f"未找到包含关键字 '{keyword}' 的记录。")
            
            # 过滤出对应的招标公告，并调用大模型来提取招标金额等信息
            for item in results_with_summary:
                project_key = item['project'][:30]
                query = """
                SELECT * FROM llm_tools.bidding_csg
                WHERE project LIKE %s AND type="招标公告"
                """
                logger.info(f"Project key: {project_key}")
                cursor.execute(query, (f"%{project_key}%",))
                result = cursor.fetchall()
                if len(result) > 0:
                    url = result[0][4]
                    logger.info(f"查询招标公告 url: {url}")
                    self.page.goto(url, wait_until='load')
                    soup = BeautifulSoup(self.page.content(), 'html.parser')
                    content_div = soup.find('div', class_='Content') # 找到内容部分
                    bid_parser = BiddingParser(str(content_div))
                    price_info = bid_parser.parse_bid_price()
                    logger.info(f"项目【{item['project']}】的报价信息：{price_info}")
                    # logger.info(f"中标公告: {item['url']}")
                    # logger.info(f"中标金额: {item['summary']}")
                    item['price'] = json.dumps(price_info)
                    update_list.append(item)
                    # self.random_wait()
            self.update(update_list)
            return result
        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

    def random_wait(self):
        # 生成 1 到 3 秒之间的随机等待时间，防止被反爬虫机制检测到
        wait_time = random.uniform(1, 3)
        # 打印等待时间
        logger.info(f"等待时间: {wait_time:.2f} 秒")
        # 等待
        time.sleep(wait_time)

class BiddingCsgAnalyzer:
    def output_as_csv(self, keyword: str, bidding_type: int):
        # 以 csv 格式输出对比结果
        query = """
        SELECT * FROM llm_tools.bidding_csg bc
        WHERE type='公示公告' AND summary is not NULL AND price is not NULL AND project LIKE %s;
        """

        csv_list = []
        try:
            # 连接数据库
            connection = getConnection()
            cursor = connection.cursor()

            # 执行查询
            cursor.execute(query, (f"%{keyword}%",))

            # 获取查询结果
            results = cursor.fetchall()

            # 输出结果
            if results:
                logger.info(f"找到 {len(results)} 条关于 '{keyword}' 的有价格中标记录.")
                if bidding_type == 1:
                    header = ["招标编号", "甲方", "项目名称", "公告日期", "公告链接", "标的名称", "标包名称", "最高限价(万元)", "中标公司", "中标价格(万元)"]
                    csv_list.append(header)
                    for row in results:
                        project = row[0]
                        part_a = row[1]
                        annoce_date = row[3].strftime("%Y-%m-%d")
                        url = row[4]
                        summary = row[5]
                        price = row[6]
                        summary_obj = json.loads(summary)
                        price_obj = json.loads(price)
                        code = summary_obj["招标编号"]
                        for r in summary_obj["评标情况"]:
                            subject = r["标的"]
                            package = r["标包"]
                            company = r["候选人"]
                            price = r["投标报价"]
                            for item in price_obj:
                                if is_number(str(price)) and is_number(item['price']) and item['package'] == package:
                                    data = [code, part_a, project, annoce_date, url, subject, package, item['price'], company, str(price)]
                                    csv_list.append(data)
                    # break
                else:
                    header = ["招标编号", "甲方", "项目名称", "公告日期", "公告链接", "标的名称", "标包名称", "投标费率"]
                    csv_list.append(header)
                    for row in results:
                        project = row[0]
                        part_a = row[1]
                        annoce_date = row[3].strftime("%Y-%m-%d")
                        url = row[4]
                        summary = row[5]
                        price = row[6]
                        summary_obj = json.loads(summary)
                        code = summary_obj["招标编号"]
                        for r in summary_obj["招标情况"]:
                            subject = r["标的"]
                            package = r["标包"]
                            price_rate = r["投标费率"]
                            data = [code, part_a, project, annoce_date, url, subject, package, price_rate]
                            csv_list.append(data)
            else:
                logger.info(f"未找到包含关键字 '{keyword}' 的记录。")
            
            with open('bidding_csg.csv', 'w', encoding='utf-8', newline="") as outfile:
                writer = csv.writer(outfile)
                writer.writerows(csv_list)
            return csv_list
        except Exception as e:
            logger.info(f"数据库错误: {e}")

        finally:
            # 关闭连接
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("数据库连接已关闭")

def get_price_info(keyword: str, bidding_type=None, max_page=65535):
    """
    下载招投标成交信息.
    """
    csg = BiddingCSG(verbose=True)
    csg.search(keyword, max_page=max_page)
    csg.save_to_db()
    csg.filter(keyword, bidding_type)
    if bidding_type == 1:
        csg.analyze(keyword)

def query_price(keyword: str, bidding_type: int):
    """
    查询成交价格.

    参数:
        - keyword: 甲方公司名称
    
    返回值:
        - 无. 查询结果保存于 bidding_csg.csv
    """
    analyzer = BiddingCsgAnalyzer()
    analyzer.output_as_csv(keyword, bidding_type)

import argparse

USAGE = """
# 下载历史中标成交价格


python bidding_csg.py -d -n "汕头供电局" -t 1

# 导出到 csv 文件

python bidding_csg.py -q -n "汕头供电局" -t 1
"""


if __name__ == '__main__':
    print(USAGE)
    parser = argparse.ArgumentParser(description="下载招投标公告并查询成交价格")
    parser.add_argument("-d", action="store_true", help="执行 get_price_info 下载招投标公告")
    parser.add_argument("-q", action="store_true", help="执行 query_price 来查询成交价格")
    parser.add_argument("-n", type=str, help="要查询的甲方单位名称", required=True)
    parser.add_argument("-t", type=int, choices=[1, 2], help="公告类型: 1=投标报价, 2=投标费率")
    parser.add_argument("--max_page", type=int, default=65535, help="最大爬取页数")

    args = parser.parse_args()

    if args.t:
        logger.info(f"公告类型: {args.t}")

    if not args.d and not args.q:
        parser.error("必须提供 -d 或 -q 参数")

    keyword = args.n
    logger.info(f"查询关键字: {keyword}")

    if args.d:
        logger.info("执行 get_price_info")
        get_price_info(keyword, args.t, args.max_page)
    if args.q:
        logger.info("执行 query_price")
        query_price(keyword, args.t)
