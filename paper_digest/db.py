"""SQLite 数据库模块 - 状态管理和缓存"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class PaperRecord:
    """文献记录"""
    id: int
    zotero_key: str
    title: str
    item_type: str
    date: str
    authors: List[str]
    pdf_path: str
    zotero_link: str
    created_at: str


@dataclass
class AnalysisRecord:
    """分析记录"""
    id: int
    paper_id: int
    status: str  # pending, processing, completed, failed
    research_question: Optional[str]
    method: Optional[str]
    key_findings: Optional[List[str]]
    raw_response: Optional[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    cache_key: Optional[str]
    prompt_version: Optional[str]
    model_version: Optional[str]


class Database:
    """SQLite 数据库管理器"""

    def __init__(self, db_path: str = "paper.db"):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """初始化数据库表结构"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 创建 papers 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zotero_key TEXT UNIQUE,
                    title TEXT NOT NULL,
                    item_type TEXT,
                    date TEXT,
                    authors TEXT,  -- JSON 格式
                    pdf_path TEXT,
                    zotero_link TEXT,
                    pdf_hash TEXT,  -- 用于缓存验证
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建 analyses 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    research_question TEXT,
                    method TEXT,
                    key_findings TEXT,  -- JSON 格式
                    raw_response TEXT,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    cache_key TEXT,
                    prompt_version TEXT,
                    model_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_zotero_key ON papers(zotero_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_paper_id ON analyses(paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_cache_key ON analyses(cache_key)")

            conn.commit()

        # 运行迁移
        self._migrate()

    def _migrate(self):
        """数据库迁移"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 检查 analyses 表是否需要添加新列
            cursor.execute("PRAGMA table_info(analyses)")
            columns = {row['name'] for row in cursor.fetchall()}

            # 添加缺少的列
            if 'cache_key' not in columns:
                cursor.execute("ALTER TABLE analyses ADD COLUMN cache_key TEXT")
            if 'prompt_version' not in columns:
                cursor.execute("ALTER TABLE analyses ADD COLUMN prompt_version TEXT")
            if 'model_version' not in columns:
                cursor.execute("ALTER TABLE analyses ADD COLUMN model_version TEXT")

            # 检查 papers 表是否需要添加 pdf_hash 列
            cursor.execute("PRAGMA table_info(papers)")
            columns = {row['name'] for row in cursor.fetchall()}

            if 'pdf_hash' not in columns:
                cursor.execute("ALTER TABLE papers ADD COLUMN pdf_hash TEXT")

            conn.commit()

    def add_paper(self, zotero_key: str, title: str, item_type: str,
                  date: str, authors: List[str], pdf_path: str,
                  zotero_link: str, pdf_hash: Optional[str] = None) -> int:
        """添加文献，如果已存在则更新"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 检查是否已存在
            cursor.execute("SELECT id FROM papers WHERE zotero_key = ?", (zotero_key,))
            row = cursor.fetchone()

            authors_json = json.dumps(authors, ensure_ascii=False)

            if row:
                # 更新
                cursor.execute("""
                    UPDATE papers
                    SET title = ?, item_type = ?, date = ?, authors = ?,
                        pdf_path = ?, zotero_link = ?, pdf_hash = ?, updated_at = ?
                    WHERE zotero_key = ?
                """, (title, item_type, date, authors_json, pdf_path,
                      zotero_link, pdf_hash, datetime.now().isoformat(), zotero_key))
                paper_id = row[0]
            else:
                # 插入
                cursor.execute("""
                    INSERT INTO papers (zotero_key, title, item_type, date, authors,
                                       pdf_path, zotero_link, pdf_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (zotero_key, title, item_type, date, authors_json,
                      pdf_path, zotero_link, pdf_hash))
                paper_id = cursor.lastrowid

            conn.commit()
            return paper_id

    def get_paper_by_zotero_key(self, zotero_key: str) -> Optional[PaperRecord]:
        """通过 Zotero key 获取文献"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE zotero_key = ?", (zotero_key,))
            row = cursor.fetchone()

            if row:
                return PaperRecord(
                    id=row['id'],
                    zotero_key=row['zotero_key'],
                    title=row['title'],
                    item_type=row['item_type'],
                    date=row['date'],
                    authors=json.loads(row['authors']) if row['authors'] else [],
                    pdf_path=row['pdf_path'],
                    zotero_link=row['zotero_link'],
                    created_at=row['created_at']
                )
            return None

    def get_all_papers(self) -> List[PaperRecord]:
        """获取所有文献"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers ORDER BY id")
            rows = cursor.fetchall()

            return [
                PaperRecord(
                    id=row['id'],
                    zotero_key=row['zotero_key'],
                    title=row['title'],
                    item_type=row['item_type'],
                    date=row['date'],
                    authors=json.loads(row['authors']) if row['authors'] else [],
                    pdf_path=row['pdf_path'],
                    zotero_link=row['zotero_link'],
                    created_at=row['created_at']
                )
                for row in rows
            ]

    def create_analysis(self, paper_id: int, cache_key: Optional[str] = None,
                        prompt_version: Optional[str] = None,
                        model_version: Optional[str] = None) -> int:
        """创建分析记录"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analyses (paper_id, status, started_at, cache_key,
                                     prompt_version, model_version)
                VALUES (?, 'pending', ?, ?, ?, ?)
            """, (paper_id, datetime.now().isoformat(), cache_key,
                  prompt_version, model_version))
            conn.commit()
            return cursor.lastrowid

    def update_analysis_status(self, analysis_id: int, status: str,
                               error_message: Optional[str] = None):
        """更新分析状态"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            if status == 'completed':
                cursor.execute("""
                    UPDATE analyses
                    SET status = ?, completed_at = ?, error_message = ?, updated_at = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), error_message,
                      datetime.now().isoformat(), analysis_id))
            else:
                cursor.execute("""
                    UPDATE analyses
                    SET status = ?, error_message = ?, updated_at = ?
                    WHERE id = ?
                """, (status, error_message, datetime.now().isoformat(), analysis_id))

            conn.commit()

    def save_analysis_result(self, analysis_id: int, research_question: str,
                            method: str, key_findings: List[str],
                            raw_response: str):
        """保存分析结果"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE analyses
                SET research_question = ?, method = ?, key_findings = ?,
                    raw_response = ?, status = 'completed',
                    completed_at = ?, updated_at = ?
                WHERE id = ?
            """, (research_question, method, json.dumps(key_findings, ensure_ascii=False),
                  raw_response, datetime.now().isoformat(),
                  datetime.now().isoformat(), analysis_id))
            conn.commit()

    def get_analysis_by_cache_key(self, cache_key: str) -> Optional[AnalysisRecord]:
        """通过缓存 key 获取已完成的分析"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analyses
                WHERE cache_key = ? AND status = 'completed'
                ORDER BY completed_at DESC LIMIT 1
            """, (cache_key,))
            row = cursor.fetchone()

            if row:
                return AnalysisRecord(
                    id=row['id'],
                    paper_id=row['paper_id'],
                    status=row['status'],
                    research_question=row['research_question'],
                    method=row['method'],
                    key_findings=json.loads(row['key_findings']) if row['key_findings'] else None,
                    raw_response=row['raw_response'],
                    error_message=row['error_message'],
                    started_at=row['started_at'],
                    completed_at=row['completed_at'],
                    cache_key=row['cache_key'],
                    prompt_version=row['prompt_version'],
                    model_version=row['model_version']
                )
            return None

    def get_unanalyzed_papers(self) -> List[Dict[str, Any]]:
        """获取未分析或需要重新分析的文献"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, a.status, a.cache_key
                FROM papers p
                LEFT JOIN analyses a ON p.id = a.paper_id
                WHERE a.id IS NULL
                   OR a.status IN ('pending', 'failed')
                ORDER BY p.id
            """)
            rows = cursor.fetchall()

            return [
                {
                    'id': row['id'],
                    'zotero_key': row['zotero_key'],
                    'title': row['title'],
                    'date': row['date'],
                    'pdf_path': row['pdf_path'],
                    'status': row['status'] or 'never_analyzed'
                }
                for row in rows
            ]

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_papers,
                    SUM(CASE WHEN a.id IS NULL THEN 1 ELSE 0 END) as never_analyzed,
                    SUM(CASE WHEN a.status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN a.status = 'processing' THEN 1 ELSE 0 END) as processing,
                    SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN a.status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM papers p
                LEFT JOIN analyses a ON p.id = a.paper_id
            """)
            row = cursor.fetchone()

            return {
                'total_papers': row['total_papers'] or 0,
                'never_analyzed': row['never_analyzed'] or 0,
                'pending': row['pending'] or 0,
                'processing': row['processing'] or 0,
                'completed': row['completed'] or 0,
                'failed': row['failed'] or 0
            }
