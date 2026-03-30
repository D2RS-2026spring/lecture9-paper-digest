"""Zotero 集成模块 - 处理本地 Zotero 连接和文献获取"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from pyzotero import zotero
from dotenv import load_dotenv


@dataclass
class Paper:
    """文献数据类"""
    zotero_key: str
    title: str
    item_type: str
    date: str
    authors: List[str]
    pdf_path: Optional[str]
    pdf_filename: Optional[str]
    zotero_link: str


class ZoteroClient:
    """Zotero 客户端 - 本地模式"""

    def __init__(self):
        # 加载环境变量
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        self.library_id = os.getenv("ZOTERO_USER_ID", "")
        self.root_dir = os.getenv("ZOTERO_ROOT_DIR", "")
        self.data_dir = os.getenv("ZOTERO_DATA_DIR", "")

        if not self.library_id:
            raise ValueError("ZOTERO_USER_ID 未设置，请检查 .env 文件")

        self.zot = zotero.Zotero(self.library_id, "user", local=True)

    def resolve_attachment_path(self, path: str) -> Optional[str]:
        """将 Zotero 附件路径转换为完整文件系统路径"""
        if not path or path == 'N/A':
            return None

        # 已经是绝对路径
        if os.path.isabs(path) and os.path.exists(path):
            return path

        # attachments: 开头（链接附件）
        if path.startswith('attachments:'):
            relative_path = path[12:]
            if self.root_dir:
                full_path = os.path.join(self.root_dir, relative_path)
                if os.path.exists(full_path):
                    return full_path
            return None

        # storage: 开头
        if path.startswith('storage:'):
            storage_path = path[8:]
            if self.data_dir:
                full_path = os.path.join(self.data_dir, storage_path)
                if os.path.exists(full_path):
                    return full_path
            return None

        return None

    def get_pdf_attachment(self, item_key: str) -> Optional[Dict[str, Any]]:
        """获取文献的 PDF 附件信息"""
        try:
            children = self.zot.children(item_key)
            for child in children:
                data = child.get('data', {})
                if (data.get('itemType') == 'attachment' and
                    data.get('contentType') == 'application/pdf'):
                    return {
                        'key': child.get('key'),
                        'filename': data.get('filename', ''),
                        'path': data.get('path', ''),
                    }
            return None
        except Exception as e:
            print(f"获取附件失败: {e}")
            return None

    def get_papers_with_pdf(self, limit: int = 10, collection_key: Optional[str] = None) -> List[Paper]:
        """获取带 PDF 的文献列表"""
        papers = []

        # 获取文献
        if collection_key:
            items = self.zot.collection_items(collection_key, limit=limit * 2)
        else:
            items = self.zot.top(limit=limit * 2)

        for item in items:
            data = item.get('data', {})
            item_key = item.get('key')

            # 跳过附件和笔记
            if data.get('itemType') in ['attachment', 'note']:
                continue

            # 获取 PDF
            pdf = self.get_pdf_attachment(item_key)
            if pdf:
                full_path = self.resolve_attachment_path(pdf.get('path', ''))
                if full_path and os.path.exists(full_path):
                    # 提取作者
                    creators = data.get('creators', [])
                    authors = []
                    for creator in creators:
                        if creator.get('creatorType') in ['author', 'editor']:
                            first = creator.get('firstName', '')
                            last = creator.get('lastName', '')
                            if first and last:
                                authors.append(f"{first} {last}")
                            elif last:
                                authors.append(last)

                    paper = Paper(
                        zotero_key=item_key,
                        title=data.get('title', 'Unknown Title'),
                        item_type=data.get('itemType', 'unknown'),
                        date=data.get('date', ''),
                        authors=authors,
                        pdf_path=full_path,
                        pdf_filename=pdf.get('filename'),
                        zotero_link=f"zotero://select/items/{item_key}"
                    )
                    papers.append(paper)

                    if len(papers) >= limit:
                        break

        return papers

    def get_all_collections(self) -> List[Dict[str, str]]:
        """获取所有集合（目录）"""
        collections = self.zot.collections()
        return [
            {
                'key': c.get('key'),
                'name': c.get('data', {}).get('name', 'Unnamed'),
                'parent': c.get('data', {}).get('parentCollection', '')
            }
            for c in collections
        ]

    def count_items(self) -> int:
        """获取文献总数"""
        return self.zot.count_items()
