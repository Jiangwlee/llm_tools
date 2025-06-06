"""
信息提取服务

从本地HTML文件中提取各种信息（价格、中标方、基本信息等）。
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from bs4 import BeautifulSoup

from biddingcsg.llm.chat import LLMHelper
from biddingcsg.utils.logger import get_logger

logger = get_logger(__name__)


class InfoExtractor:
    """统一信息提取服务"""
    
    def __init__(self, html_directory: str):
        """
        初始化信息提取器
        
        Args:
            html_directory: HTML文件目录路径
        """
        self.html_directory = Path(html_directory)
        self.results = []
        self.stop_requested = False
        
    def extract_info_batch(self, 
                          keyword: str, 
                          extract_type: str = "price",
                          progress_callback: Optional[Callable] = None,
                          log_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        批量提取信息
        
        Args:
            keyword: 搜索关键词
            extract_type: 提取类型 (price, bidder, rate, basic)
            progress_callback: 进度回调函数 (current, total, message)
            log_callback: 日志回调函数 (message)
            
        Returns:
            提取结果列表
        """
        self.stop_requested = False
        self.results = []
        
        try:
            # 阶段1：扫描文件
            if log_callback:
                log_callback("🔍 开始扫描HTML文件...")
            
            files = self._scan_files(keyword)
            
            if log_callback:
                log_callback(f"📁 找到 {len(files)} 个匹配的公示公告文件")
            
            if not files:
                if log_callback:
                    log_callback("⚠️ 未找到匹配文件")
                return []
            
            # 阶段2：批量处理文件
            if log_callback:
                log_callback("🔄 开始批量处理文件...")
            
            self.results = self._process_file_loop(files, extract_type, progress_callback, log_callback)
            
            # 阶段3：完成
            success_count = len([r for r in self.results if r.get('success', False)])
            if log_callback:
                log_callback(f"🎉 批量处理完成！成功提取 {success_count}/{len(files)} 个文件")
            
            return self.results
            
        except Exception as e:
            logger.error(f"批量提取失败: {e}")
            if log_callback:
                log_callback(f"❌ 批量提取失败: {str(e)}")
            return []
    
    def save_results(self, results: List[Dict[str, Any]], output_path: str) -> bool:
        """
        保存提取结果到JSON文件
        
        Args:
            results: 提取结果列表
            output_path: 输出文件路径
            
        Returns:
            是否保存成功
        """
        try:
            # 构建输出数据
            output_data = {
                "extraction_time": datetime.now().isoformat(),
                "total_files": len(results),
                "successful_extractions": len([r for r in results if r.get('success', False)]),
                "results": results
            }
            
            # 确保输出目录存在
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"提取结果已保存到: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            return False
    
    def stop_extraction(self):
        """停止提取过程"""
        self.stop_requested = True
        logger.info("收到停止提取请求")
    
    def _scan_files(self, keyword: str) -> List[Path]:
        """
        扫描匹配的HTML文件
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的文件路径列表
        """
        matching_files = []
        
        if not self.html_directory.exists():
            logger.warning(f"HTML目录不存在: {self.html_directory}")
            return matching_files
        
        # 递归查找所有HTML文件
        for html_file in self.html_directory.rglob("*.html"):
            # 检查文件名是否以"公示公告"开头
            if html_file.name.startswith("公示公告"):
                # 检查文件内容是否包含关键词
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if keyword.lower() in content.lower():
                            matching_files.append(html_file)
                            logger.debug(f"找到匹配文件: {html_file}")
                except Exception as e:
                    logger.error(f"读取文件失败 {html_file}: {e}")
        
        return matching_files
    
    def _process_file_loop(self, 
                          files: List[Path], 
                          extract_type: str,
                          progress_callback: Optional[Callable],
                          log_callback: Optional[Callable]) -> List[Dict[str, Any]]:
        """
        循环处理文件列表
        
        Args:
            files: 文件路径列表
            extract_type: 提取类型
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            
        Returns:
            处理结果列表
        """
        results = []
        total_files = len(files)
        
        for i, file_path in enumerate(files, 1):
            # 检查停止请求
            if self.stop_requested:
                if log_callback:
                    log_callback("🛑 用户请求停止，提取已中断")
                break
            
            # 更新进度
            if progress_callback:
                progress_callback(i, total_files, f"处理 {file_path.name}")
            
            if log_callback:
                log_callback(f"📄 [{i}/{total_files}] 处理文件: {file_path.name}")
            
            try:
                # 处理单个文件
                result = self._process_single_file(file_path, extract_type)
                results.append(result)
                
                if result.get('success', False):
                    if log_callback:
                        log_callback(f"✅ 成功提取: {file_path.name}")
                else:
                    if log_callback:
                        log_callback(f"⚠️ 未找到相关信息: {file_path.name}")
                
            except Exception as e:
                logger.error(f"处理文件失败 {file_path}: {e}")
                if log_callback:
                    log_callback(f"❌ 处理失败: {file_path.name} - {str(e)}")
                
                # 添加失败记录
                results.append({
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "success": False,
                    "error": str(e),
                    "processed_at": datetime.now().isoformat()
                })
            
            # 短暂等待，避免过快处理
            time.sleep(0.1)
        
        return results
    
    def _process_single_file(self, file_path: Path, extract_type: str) -> Dict[str, Any]:
        """
        处理单个HTML文件
        
        Args:
            file_path: HTML文件路径
            extract_type: 提取类型
            
        Returns:
            处理结果字典
        """
        # 读取HTML文件
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取基本信息
        title = self._extract_title(soup)
        date = self._extract_date(soup)
        
        # 查找内容区域
        content_div = soup.find('div', class_='Content')
        if not content_div:
            # 如果没找到特定的div，使用整个body
            content_div = soup.find('body') or soup
        
        # 检查是否包含目标信息
        has_target_info = self._check_target_info(content_div, extract_type)
        
        # 构建基础结果
        result = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "title": title,
            "date": date,
            "extract_type": extract_type,
            "has_target_info": has_target_info,
            "processed_at": datetime.now().isoformat(),
            "success": False,
            "extracted_info": None
        }
        
        # 如果包含目标信息，进行LLM提取
        if has_target_info:
            try:
                extracted_info = self._call_llm_by_type(str(content_div), extract_type)
                if extracted_info:
                    result["extracted_info"] = extracted_info
                    result["success"] = True
                    logger.info(f"成功提取信息: {file_path.name}")
                else:
                    logger.warning(f"LLM返回空结果: {file_path.name}")
            except Exception as e:
                logger.error(f"LLM调用失败 {file_path}: {e}")
                result["error"] = str(e)
        
        return result
    
    def _call_llm_by_type(self, content: str, extract_type: str) -> Optional[str]:
        """
        根据提取类型调用对应的LLM方法
        
        Args:
            content: HTML内容
            extract_type: 提取类型
            
        Returns:
            LLM提取结果
        """
        try:
            if extract_type == "price":
                return LLMHelper.llm_summary(content)
            elif extract_type == "bidder":
                return LLMHelper.llm_basic_info_extract(content)
            elif extract_type == "rate":
                return LLMHelper.llm_price_extract(content)
            elif extract_type == "basic":
                return LLMHelper.llm_basic_info_extract(content)
            else:
                logger.warning(f"未知的提取类型: {extract_type}")
                return None
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return None
    
    def _check_target_info(self, content_div, extract_type: str) -> bool:
        """
        检查内容是否包含目标信息
        
        Args:
            content_div: 内容区域BeautifulSoup对象
            extract_type: 提取类型
            
        Returns:
            是否包含目标信息
        """
        try:
            if extract_type == "price":
                # 检查是否包含投标报价
                return bool(content_div.find_all(lambda tag: '>投标报价<' in str(tag)))
            elif extract_type == "rate":
                # 检查是否包含投标费率
                return bool(content_div.find_all(lambda tag: '>投标费率<' in str(tag)))
            elif extract_type in ["bidder", "basic"]:
                # 对于中标方和基本信息，假设都有内容
                return bool(content_div.get_text(strip=True))
            else:
                return True
        except Exception as e:
            logger.error(f"检查目标信息失败: {e}")
            return False
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """从HTML中提取标题"""
        title_selectors = [
            'h1.s-title',
            'h1',
            'title',
            '.title',
            '.article-title'
        ]
        
        for selector in title_selectors:
            title_tag = soup.select_one(selector)
            if title_tag and title_tag.get_text(strip=True):
                return title_tag.get_text(strip=True)
        
        return "未找到标题"
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """从HTML中提取日期"""
        date_selectors = [
            'div.s-date',
            '.date',
            '.publish-date',
            '.article-date'
        ]
        
        for selector in date_selectors:
            date_tag = soup.select_one(selector)
            if date_tag and date_tag.get_text(strip=True):
                return date_tag.get_text(strip=True)
        
        # 尝试从文本中提取日期
        import re
        date_pattern = r'\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?'
        text_content = soup.get_text()
        date_match = re.search(date_pattern, text_content)
        if date_match:
            return date_match.group()
        
        return "未找到日期"


def create_info_extractor(html_directory: str) -> InfoExtractor:
    """
    创建信息提取器实例
    
    Args:
        html_directory: HTML文件目录
        
    Returns:
        信息提取器实例
    """
    return InfoExtractor(html_directory) 