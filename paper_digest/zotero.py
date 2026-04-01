"""Zotero 集成模块 - 处理本地 Zotero 连接和文献获取"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pyzotero import zotero


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

    def resolve_attachment_path(self, path: str, filename: Optional[str] = None,
                                 item_key: Optional[str] = None) -> Optional[str]:
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

        # 纯文件名（filename 存储方式）
        # 文件实际存储在 {data_dir}/storage/{item_key}/{filename}
        if filename and item_key and self.data_dir:
            full_path = os.path.join(self.data_dir, 'storage', item_key, filename)
            if os.path.exists(full_path):
                return full_path

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

    def get_papers_with_pdf(self, limit: int = 10, collection_key: Optional[str] = None,
                           tag: Optional[str] = None) -> List[Paper]:
        """获取带 PDF 的文献列表"""
        papers = []

        # 获取文献
        if tag:
            # 按标签搜索
            items = self.zot.items(tag=tag, limit=limit * 2)
        elif collection_key:
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
                full_path = self.resolve_attachment_path(
                    pdf.get('path', ''),
                    filename=pdf.get('filename'),
                    item_key=pdf.get('key')
                )
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

    def find_collection_by_name(self, name: str) -> Optional[str]:
        """通过名称查找集合的 key（支持模糊匹配）"""
        collections = self.get_all_collections()

        # 完全匹配
        for c in collections:
            if c['name'] == name:
                return c['key']

        # 不区分大小写匹配
        name_lower = name.lower()
        for c in collections:
            if c['name'].lower() == name_lower:
                return c['key']

        # 包含匹配
        matches = [c for c in collections if name_lower in c['name'].lower()]
        if len(matches) == 1:
            return matches[0]['key']
        elif len(matches) > 1:
            # 多个匹配，返回最短的（最精确）
            matches.sort(key=lambda x: len(x['name']))
            return matches[0]['key']

        return None

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签及其使用次数"""
        tags = self.zot.tags()
        result = []
        for tag in tags:
            # API 返回的是字符串
            if isinstance(tag, str):
                result.append({
                    'tag': tag,
                    'type': 0,
                    'items': 0
                })
            else:
                # 某些版本可能返回字典
                data = tag.get('data', {}) if isinstance(tag, dict) else {}
                result.append({
                    'tag': data.get('tag', str(tag)),
                    'type': data.get('type', 0),
                    'items': tag.get('meta', {}).get('numItems', 0) if isinstance(tag, dict) else 0
                })
        return result

    def count_items(self) -> int:
        """获取文献总数"""
        return self.zot.count_items()

    def get_collections_tree(self) -> List[Dict[str, Any]]:
        """
        获取集合的树状结构

        Returns:
            树状结构的集合列表，每个节点包含 key, name, children
        """
        collections = self.get_all_collections()

        # 构建 key -> collection 映射
        key_map = {c['key']: c for c in collections}

        # 构建树
        roots = []
        children_map = {}

        for c in collections:
            parent = c.get('parent', '')
            if parent:
                if parent not in children_map:
                    children_map[parent] = []
                children_map[parent].append(c)
            else:
                roots.append(c)

        def build_tree(node, depth=0):
            """递归构建树节点"""
            result = {
                'key': node['key'],
                'name': node['name'],
                'depth': depth,
                'children': []
            }

            if node['key'] in children_map:
                for child in children_map[node['key']]:
                    result['children'].append(build_tree(child, depth + 1))

            return result

        tree = []
        for root in roots:
            tree.append(build_tree(root))

        return tree

    def flatten_collections_tree(self, tree=None) -> List[Dict[str, Any]]:
        """
        将树状集合展平为列表，包含缩进信息用于显示

        Returns:
            展平的集合列表，每个元素包含 key, name, display_name, depth
        """
        if tree is None:
            tree = self.get_collections_tree()

        result = []

        def traverse(node):
            # 生成树状前缀
            depth = node['depth']
            prefix = "  " * depth
            if depth > 0:
                prefix += "└─ "

            display_name = f"{prefix}{node['name']}"

            result.append({
                'key': node['key'],
                'name': node['name'],
                'display_name': display_name,
                'depth': depth
            })

            for child in node['children']:
                traverse(child)

        for root in tree:
            traverse(root)

        return result
