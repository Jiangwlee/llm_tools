"""
数据库管理器

负责数据库的创建、连接管理和基本的CRUD操作
支持连接池、事务管理和数据迁移
"""

import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import contextmanager
from datetime import datetime
import logging

from ..models.database import (
    DATABASE_SCHEMA, CrawlItem, LLMAnalysis, LLMSummary, 
    LLMSession, AnalysisError, CrawlStatus, AnalysisStatus
)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: Union[str, Path] = "data/crawler.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # 日志设置
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据库
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row  # 支持字典式访问
            conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
            conn.execute("PRAGMA journal_mode = WAL")  # 启用WAL模式
            self._local.connection = conn
        
        return self._local.connection
    
    @contextmanager
    def get_cursor(self, transaction: bool = False):
        """
        获取数据库游标的上下文管理器
        
        Args:
            transaction: 是否启用事务
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if transaction:
                cursor.execute("BEGIN")
            
            yield cursor
            
            if transaction:
                conn.commit()
                
        except Exception as e:
            if transaction:
                conn.rollback()
            self.logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_cursor(transaction=True) as cursor:
                # 创建所有表
                for table_name, schema in DATABASE_SCHEMA.items():
                    self.logger.info(f"创建表: {table_name}")
                    cursor.execute(schema)
                
                self.logger.info("数据库初始化完成")
                
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
    
    # ==================== CrawlItem 相关操作 ====================
    
    def insert_crawl_item(self, item: CrawlItem) -> int:
        """
        插入爬虫数据项
        
        Args:
            item: 爬虫数据项
            
        Returns:
            插入的记录ID
        """
        # 计算内容MD5
        item.calculate_content_md5()
        
        sql = """
        INSERT INTO crawl_items (
            url, title, content_html, content_md5, metadata, 
            page_type, crawl_timestamp, status, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, (
                item.url,
                item.title,
                item.content_html,
                item.content_md5,
                item.metadata,
                item.page_type,
                item.crawl_timestamp or datetime.now(),
                item.status.value,
                item.error_message
            ))
            return cursor.lastrowid
    
    def update_crawl_item(self, item: CrawlItem) -> bool:
        """
        更新爬虫数据项
        
        Args:
            item: 爬虫数据项（必须包含ID）
            
        Returns:
            是否更新成功
        """
        if not item.id:
            raise ValueError("更新操作需要指定item.id")
        
        # 重新计算内容MD5
        item.calculate_content_md5()
        
        sql = """
        UPDATE crawl_items SET
            title = ?, content_html = ?, content_md5 = ?, metadata = ?,
            page_type = ?, status = ?, error_message = ?
        WHERE id = ?
        """
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, (
                item.title,
                item.content_html,
                item.content_md5,
                item.metadata,
                item.page_type,
                item.status.value,
                item.error_message,
                item.id
            ))
            return cursor.rowcount > 0
    
    def get_crawl_item_by_id(self, item_id: int) -> Optional[CrawlItem]:
        """根据ID获取爬虫数据项"""
        sql = "SELECT * FROM crawl_items WHERE id = ?"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, (item_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_crawl_item(row)
            return None
    
    def get_crawl_item_by_url(self, url: str) -> Optional[CrawlItem]:
        """根据URL获取爬虫数据项"""
        sql = "SELECT * FROM crawl_items WHERE url = ?"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, (url,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_crawl_item(row)
            return None
    
    def get_crawl_items_by_status(self, status: CrawlStatus, limit: int = 100) -> List[CrawlItem]:
        """根据状态获取爬虫数据项列表"""
        sql = "SELECT * FROM crawl_items WHERE status = ? ORDER BY crawl_timestamp DESC LIMIT ?"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, (status.value, limit))
            rows = cursor.fetchall()
            
            return [self._row_to_crawl_item(row) for row in rows]
    
    def get_crawl_items_paginated(self, page: int = 1, page_size: int = 50) -> Tuple[List[CrawlItem], int]:
        """
        分页获取爬虫数据项
        
        Returns:
            (数据项列表, 总数量)
        """
        offset = (page - 1) * page_size
        
        # 获取总数
        count_sql = "SELECT COUNT(*) FROM crawl_items"
        data_sql = """
        SELECT * FROM crawl_items 
        ORDER BY crawl_timestamp DESC 
        LIMIT ? OFFSET ?
        """
        
        with self.get_cursor() as cursor:
            cursor.execute(count_sql)
            total_count = cursor.fetchone()[0]
            
            cursor.execute(data_sql, (page_size, offset))
            rows = cursor.fetchall()
            
            items = [self._row_to_crawl_item(row) for row in rows]
            return items, total_count
    
    def _row_to_crawl_item(self, row: sqlite3.Row) -> CrawlItem:
        """将数据库行转换为CrawlItem对象"""
        return CrawlItem(
            id=row['id'],
            url=row['url'],
            title=row['title'],
            content_html=row['content_html'],
            content_md5=row['content_md5'],
            metadata=row['metadata'],
            page_type=row['page_type'],
            crawl_timestamp=datetime.fromisoformat(row['crawl_timestamp']) if row['crawl_timestamp'] else None,
            status=CrawlStatus(row['status']),
            error_message=row['error_message']
        )
    
    # ==================== LLMAnalysis 相关操作 ====================
    
    def insert_llm_analysis(self, analysis: LLMAnalysis) -> int:
        """插入LLM分析结果"""
        sql = """
        INSERT INTO llm_analysis (
            crawl_item_id, project_name, project_code, tender_agency, budget_amount,
            announcement_date, registration_deadline, bid_deadline, opening_date,
            contact_person, contact_phone, contact_email,
            technical_requirements, qualification_requirements,
            document_fees, guarantee_amount, additional_info,
            analysis_timestamp, llm_model, confidence_score, status, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, (
                analysis.crawl_item_id,
                analysis.project_name,
                analysis.project_code,
                analysis.tender_agency,
                analysis.budget_amount,
                analysis.announcement_date,
                analysis.registration_deadline,
                analysis.bid_deadline,
                analysis.opening_date,
                analysis.contact_person,
                analysis.contact_phone,
                analysis.contact_email,
                analysis.technical_requirements,
                analysis.qualification_requirements,
                analysis.document_fees,
                analysis.guarantee_amount,
                analysis.additional_info,
                analysis.analysis_timestamp or datetime.now(),
                analysis.llm_model,
                analysis.confidence_score,
                analysis.status.value,
                analysis.error_message
            ))
            return cursor.lastrowid
    
    def get_llm_analysis_by_crawl_item_id(self, crawl_item_id: int) -> Optional[LLMAnalysis]:
        """根据爬虫项目ID获取LLM分析结果"""
        sql = "SELECT * FROM llm_analysis WHERE crawl_item_id = ?"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, (crawl_item_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_llm_analysis(row)
            return None
    
    def _row_to_llm_analysis(self, row: sqlite3.Row) -> LLMAnalysis:
        """将数据库行转换为LLMAnalysis对象"""
        return LLMAnalysis(
            id=row['id'],
            crawl_item_id=row['crawl_item_id'],
            project_name=row['project_name'],
            project_code=row['project_code'],
            tender_agency=row['tender_agency'],
            budget_amount=row['budget_amount'],
            announcement_date=row['announcement_date'],
            registration_deadline=row['registration_deadline'],
            bid_deadline=row['bid_deadline'],
            opening_date=row['opening_date'],
            contact_person=row['contact_person'],
            contact_phone=row['contact_phone'],
            contact_email=row['contact_email'],
            technical_requirements=row['technical_requirements'],
            qualification_requirements=row['qualification_requirements'],
            document_fees=row['document_fees'],
            guarantee_amount=row['guarantee_amount'],
            additional_info=row['additional_info'],
            analysis_timestamp=datetime.fromisoformat(row['analysis_timestamp']) if row['analysis_timestamp'] else None,
            llm_model=row['llm_model'],
            confidence_score=row['confidence_score'],
            status=AnalysisStatus(row['status']),
            error_message=row['error_message']
        )
    
    # ==================== LLMSummary 相关操作 ====================
    
    def insert_llm_summary(self, summary: LLMSummary) -> int:
        """插入LLM摘要"""
        sql = """
        INSERT INTO llm_summaries (
            crawl_item_id, summary_text, key_points, risk_assessment,
            recommendation, summary_timestamp, llm_model, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, (
                summary.crawl_item_id,
                summary.summary_text,
                summary.key_points,
                summary.risk_assessment,
                summary.recommendation,
                summary.summary_timestamp or datetime.now(),
                summary.llm_model,
                summary.status.value
            ))
            return cursor.lastrowid
    
    def get_llm_summary_by_crawl_item_id(self, crawl_item_id: int) -> Optional[LLMSummary]:
        """根据爬虫项目ID获取LLM摘要"""
        sql = "SELECT * FROM llm_summaries WHERE crawl_item_id = ?"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, (crawl_item_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_llm_summary(row)
            return None
    
    def _row_to_llm_summary(self, row: sqlite3.Row) -> LLMSummary:
        """将数据库行转换为LLMSummary对象"""
        return LLMSummary(
            id=row['id'],
            crawl_item_id=row['crawl_item_id'],
            summary_text=row['summary_text'],
            key_points=row['key_points'],
            risk_assessment=row['risk_assessment'],
            recommendation=row['recommendation'],
            summary_timestamp=datetime.fromisoformat(row['summary_timestamp']) if row['summary_timestamp'] else None,
            llm_model=row['llm_model'],
            status=AnalysisStatus(row['status'])
        )
    
    # ==================== LLMSession 相关操作 ====================
    
    def create_llm_session(self, session_name: str, description: str = "", 
                          llm_model: str = "", config_snapshot: str = "{}") -> int:
        """创建LLM处理会话"""
        sql = """
        INSERT INTO llm_sessions (
            session_name, description, start_time, llm_model, config_snapshot, status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, (
                session_name,
                description,
                datetime.now(),
                llm_model,
                config_snapshot,
                AnalysisStatus.PENDING.value
            ))
            return cursor.lastrowid
    
    def update_session_progress(self, session_id: int, total_items: int = None,
                               processed_items: int = None, success_items: int = None,
                               failed_items: int = None, status: AnalysisStatus = None):
        """更新会话进度"""
        updates = []
        params = []
        
        if total_items is not None:
            updates.append("total_items = ?")
            params.append(total_items)
        
        if processed_items is not None:
            updates.append("processed_items = ?")
            params.append(processed_items)
        
        if success_items is not None:
            updates.append("success_items = ?")
            params.append(success_items)
        
        if failed_items is not None:
            updates.append("failed_items = ?")
            params.append(failed_items)
        
        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
            
            if status in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]:
                updates.append("end_time = ?")
                params.append(datetime.now())
        
        if not updates:
            return
        
        params.append(session_id)
        sql = f"UPDATE llm_sessions SET {', '.join(updates)} WHERE id = ?"
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, params)
    
    def get_llm_session_by_id(self, session_id: int) -> Optional[LLMSession]:
        """根据ID获取LLM会话"""
        sql = "SELECT * FROM llm_sessions WHERE id = ?"
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, (session_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_llm_session(row)
            return None
    
    def _row_to_llm_session(self, row: sqlite3.Row) -> LLMSession:
        """将数据库行转换为LLMSession对象"""
        return LLMSession(
            id=row['id'],
            session_name=row['session_name'],
            description=row['description'],
            start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
            end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
            total_items=row['total_items'],
            processed_items=row['processed_items'],
            success_items=row['success_items'],
            failed_items=row['failed_items'],
            llm_model=row['llm_model'],
            config_snapshot=row['config_snapshot'],
            status=AnalysisStatus(row['status'])
        )
    
    # ==================== AnalysisError 相关操作 ====================
    
    def log_analysis_error(self, error: AnalysisError) -> int:
        """记录分析错误"""
        sql = """
        INSERT INTO analysis_errors (
            crawl_item_id, session_id, error_type, error_message,
            error_details, timestamp, retry_count, resolved
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.get_cursor(transaction=True) as cursor:
            cursor.execute(sql, (
                error.crawl_item_id,
                error.session_id,
                error.error_type,
                error.error_message,
                error.error_details,
                error.timestamp or datetime.now(),
                error.retry_count,
                error.resolved
            ))
            return cursor.lastrowid
    
    # ==================== 统计和查询操作 ====================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}
        
        with self.get_cursor() as cursor:
            # 爬虫数据统计
            cursor.execute("SELECT COUNT(*) FROM crawl_items")
            stats['total_crawl_items'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT status, COUNT(*) FROM crawl_items GROUP BY status")
            stats['crawl_items_by_status'] = dict(cursor.fetchall())
            
            # LLM分析统计
            cursor.execute("SELECT COUNT(*) FROM llm_analysis")
            stats['total_llm_analysis'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT status, COUNT(*) FROM llm_analysis GROUP BY status")
            stats['llm_analysis_by_status'] = dict(cursor.fetchall())
            
            # 摘要统计
            cursor.execute("SELECT COUNT(*) FROM llm_summaries")
            stats['total_llm_summaries'] = cursor.fetchone()[0]
            
            # 会话统计
            cursor.execute("SELECT COUNT(*) FROM llm_sessions")
            stats['total_llm_sessions'] = cursor.fetchone()[0]
            
            # 错误统计
            cursor.execute("SELECT COUNT(*) FROM analysis_errors WHERE resolved = FALSE")
            stats['unresolved_errors'] = cursor.fetchone()[0]
        
        return stats
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        with self.get_cursor(transaction=True) as cursor:
            # 只清理失败和已处理的数据
            cursor.execute("""
                DELETE FROM crawl_items 
                WHERE crawl_timestamp < ? 
                AND status IN ('failed', 'completed')
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            self.logger.info(f"清理了 {deleted_count} 条旧数据")
            
            return deleted_count 