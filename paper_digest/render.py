"""Quarto 渲染模块 - 生成 Markdown/Quarto 文件"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .cache import CacheManager
from .db import Database

console = Console()


def normalize_date(date_str: Optional[str]) -> str:
    """
    将 Zotero 日期格式规范化为 Quarto 兼容的日期格式

    支持格式：
    - 2023 -> 2023-01-01
    - 2023-03 -> 2023-03-01
    - 2023-03-15 -> 2023-03-15
    - 2023/03/15 -> 2023-03-15
    - 2024年12月16日 -> 2024-12-16
    - March 2023 -> 2023-03-01
    - 空值 -> 空字符串
    """
    if not date_str or date_str.strip() == '':
        return ''

    date_str = date_str.strip()

    # 已经是完整日期格式 YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # 只有年份 YYYY
    if re.match(r'^\d{4}$', date_str):
        return f"{date_str}-01-01"

    # 年月格式 YYYY-MM 或 YYYY/MM
    if re.match(r'^\d{4}[-/]\d{2}$', date_str):
        return f"{date_str[:4]}-{date_str[5:7]}-01"

    # 斜杠格式 YYYY/MM/DD
    if re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
        return date_str.replace('/', '-')

    # 斜杠格式 YYYY/M/D（补零）
    slash_match = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', date_str)
    if slash_match:
        year, month, day = slash_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # MM/YYYY 格式（如 06/2022 -> 2022-06-01）
    mm_yyyy_match = re.match(r'^(\d{1,2})/(\d{4})$', date_str)
    if mm_yyyy_match:
        month, year = mm_yyyy_match.groups()
        return f"{year}-{int(month):02d}-01"

    # 中文日期格式 2024年12月16日
    chinese_match = re.match(r'^(\d{4})年(\d{1,2})月(\d{1,2})日$', date_str)
    if chinese_match:
        year, month, day = chinese_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # 中文年月格式 2024年12月
    chinese_ym_match = re.match(r'^(\d{4})年(\d{1,2})月$', date_str)
    if chinese_ym_match:
        year, month = chinese_ym_match.groups()
        return f"{year}-{int(month):02d}-01"

    # 英文月份格式如 "March 2023" 或 "Mar 15, 2023" 或 "2021 Oct 21"
    try:
        formats = [
            '%B %Y', '%b %Y',           # March 2023, Mar 2023
            '%B %d, %Y', '%b %d, %Y',   # March 15, 2023, Mar 15, 2023
            '%d %B %Y', '%d %b %Y',     # 15 March 2023, 15 Mar 2023
            '%Y %b %d', '%Y %B %d',     # 2021 Oct 21, 2021 October 21
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if fmt in ['%B %Y', '%b %Y']:
                    return parsed.strftime('%Y-%m-01')
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except Exception:
        pass

    # 无法解析，原样返回（Quarto 会忽略无效日期）
    console.print(f"[yellow]警告：无法解析日期 '{date_str}'，将忽略[/yellow]")
    return ''


class QuartoRenderer:
    """Quarto 渲染器"""

    def __init__(self, output_dir: str = "quarto"):
        self.output_dir = Path(output_dir)
        self.papers_dir = self.output_dir / "papers"
        self.db = Database()
        self.cache = CacheManager()

    def setup(self):
        """初始化目录结构"""
        self.output_dir.mkdir(exist_ok=True)
        self.papers_dir.mkdir(exist_ok=True)

    def render_paper(self, paper_id: int) -> Optional[Path]:
        """
        渲染单篇文献为 Quarto 文件

        Args:
            paper_id: 文献 ID

        Returns:
            生成的文件路径
        """
        import sqlite3
        conn = sqlite3.connect("paper.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取文献和分析数据（包括 cache_key）
        cursor.execute("""
            SELECT p.*, a.status, a.completed_at, a.cache_key
            FROM papers p
            LEFT JOIN analyses a ON p.id = a.paper_id
            WHERE p.id = ?
            ORDER BY a.id DESC
            LIMIT 1
        """, (paper_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # 解析作者
        authors = json.loads(row['authors']) if row['authors'] else []

        # 规范化日期
        normalized_date = normalize_date(row['date'])

        # 从缓存读取分析结果
        analysis_result = None
        if row['cache_key']:
            analysis_result = self.cache.get(row['cache_key'])

        # 构建 YAML 头部
        yaml_lines = ["---", f"title: \"{row['title']}\""]
        if normalized_date:
            yaml_lines.append(f"date: {normalized_date}")
        yaml_lines.extend([
            f"zotero-key: {row['zotero_key']}",
            f"zotero-link: {row['zotero_link']}",
            "---",
            ""
        ])

        # 构建内容
        lines = yaml_lines + [
            "## 文献信息",
            "",
            f"- **标题**: {row['title']}",
            f"- **作者**: {', '.join(authors) if authors else 'N/A'}",
            f"- **日期**: {row['date'] or 'N/A'}",
            f"- **类型**: {row['item_type']}",
            f"- [在 Zotero 中打开]({row['zotero_link']})",
            "",
        ]

        # 添加分析结果
        if analysis_result:
            # 提取基本信息
            basic_info = analysis_result.get('basic_info', {})
            if basic_info:
                lines.extend([
                    "## 基本信息",
                    "",
                    f"- **期刊**: {basic_info.get('journal', 'N/A')}",
                    f"- **年份**: {basic_info.get('year', 'N/A')}",
                    f"- **通讯作者**: {basic_info.get('corresponding_author', 'N/A')}",
                    "",
                ])

            # 添加各个章节
            sections = [
                ("研究背景", analysis_result.get('research_background')),
                ("研究结论", analysis_result.get('research_conclusion')),
                ("核心创新点", analysis_result.get('innovation_points')),
                ("实验设计", analysis_result.get('experimental_design')),
                ("讨论", analysis_result.get('discussion')),
                ("产业转化可行性", analysis_result.get('industrial_feasibility')),
            ]

            for title, content in sections:
                if content:
                    # 如果内容是列表，转换为带序号的字符串
                    if isinstance(content, list):
                        content_str = "\\n".join(f"{i+1}. {item}" for i, item in enumerate(content))
                    else:
                        content_str = str(content)
                    lines.extend([f"## {title}", "", content_str, ""])

            # 一句话总结
            one_sentence = analysis_result.get('one_sentence_summary')
            if one_sentence:
                lines.extend([
                    "## 一句话总结",
                    "",
                    f"> {one_sentence}",
                    "",
                ])
        else:
            status = row['status'] or 'never_analyzed'
            lines.extend([
                "## 分析结果",
                "",
                f"> 状态: {status}",
                "",
                "这篇文献尚未完成分析。",
                "",
            ])

        # 写入文件
        safe_title = "".join(c for c in row['title'][:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '-')
        filename = f"{row['id']:04d}-{safe_title or 'untitled'}.qmd"
        filepath = self.papers_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return filepath

    def render_all(self) -> List[Path]:
        """
        渲染所有已完成的文献

        Returns:
            生成的文件路径列表
        """
        self.setup()

        # 获取所有文献
        papers = self.db.get_all_papers()

        rendered = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("渲染文献...", total=len(papers))

            for paper in papers:
                progress.update(task, description=f"渲染: {paper.title[:30]}...")

                filepath = self.render_paper(paper.id)
                if filepath:
                    rendered.append(filepath)

                progress.advance(task)

        console.print(f"[green]✓[/green] 渲染完成：{len(rendered)} 篇文献")
        return rendered

    def generate_index(self):
        """生成索引文件"""
        # 获取统计
        stats = self.db.get_stats()

        # 获取所有文献
        papers = self.db.get_all_papers()

        lines = [
            "---",
            f"title: \"Paper Digest - 文献知识库\"",
            f"date: {datetime.now().strftime('%Y-%m-%d')}",
            "---",
            "",
            "# Paper Digest",
            "",
            "基于 Zotero + Qwen 的科研文献知识编译系统",
            "",
            "## 统计",
            "",
            f"- 总文献数: {stats['total_papers']}",
            f"- 已完成分析: {stats['completed']}",
            f"- 待分析: {stats['pending'] + stats['never_analyzed']}",
            "",
            "## 文献列表",
            "",
        ]

        import sqlite3
        conn = sqlite3.connect("paper.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for paper in papers:
            cursor.execute("""
                SELECT status FROM analyses
                WHERE paper_id = ?
                ORDER BY id DESC LIMIT 1
            """, (paper.id,))

            row = cursor.fetchone()
            status = row['status'] if row else 'never_analyzed'

            status_icon = {
                'completed': '✅',
                'pending': '⏳',
                'processing': '🔄',
                'failed': '❌',
                'never_analyzed': '⬜'
            }.get(status, '⬜')

            safe_title = "".join(c for c in paper.title[:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '-')
            filename = f"papers/{paper.id:04d}-{safe_title or 'untitled'}.qmd"

            lines.append(f"{status_icon} [{paper.title}]({filename})")

        conn.close()

        # 写入索引
        index_path = self.output_dir / "index.qmd"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        console.print(f"[green]✓[/green] 索引文件: {index_path}")
        return index_path

    def generate_quarto_yaml(self):
        """生成 _quarto.yml 配置文件"""
        config = """project:
  type: book
  output-dir: _book

book:
  title: "Paper Digest"
  author: "Generated by Paper Digest"
  date: today
  chapters:
    - index.qmd
    - part: "文献列表"
      chapters:
"""

        # 获取所有文献文件
        if self.papers_dir.exists():
            qmd_files = sorted(self.papers_dir.glob("*.qmd"))
            for qmd_file in qmd_files:
                config += f"        - papers/{qmd_file.name}\n"

        config += """
format:
  html:
    theme: cosmo
    toc: true
    toc-depth: 3
  pdf:
    documentclass: scrreprt
"""

        config_path = self.output_dir / "_quarto.yml"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config)

        console.print(f"[green]✓[/green] 配置文件: {config_path}")
        return config_path
