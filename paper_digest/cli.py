"""CLI 入口 - 命令行接口"""

import click
from rich.console import Console
from rich.table import Table

from .processor import PaperProcessor
from .render import QuartoRenderer

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Paper Digest - 基于 Zotero + Qwen 的科研文献知识编译系统"""
    pass


@main.command()
@click.option('--limit', '-l', default=100, help='最多同步多少篇文献')
@click.option('--collection', '-c', default=None, help='只同步指定集合的文献')
def sync(limit: int, collection: str):
    """从 Zotero 同步文献"""
    try:
        processor = PaperProcessor()
        count = processor.sync(limit=limit, collection_key=collection)
        console.print(f"[green]成功同步 {count} 篇文献[/green]")
    except Exception as e:
        console.print(f"[red]同步失败: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option('--limit', '-l', default=None, type=int, help='最多解析多少篇')
@click.option('--force', '-f', is_flag=True, help='强制重新解析')
@click.option('--prompt', '-p', default=None, help='自定义 prompt 文件路径')
def build(limit: int, force: bool, prompt: str):
    """构建/解析文献"""
    try:
        processor = PaperProcessor()

        # 读取自定义 prompt
        custom_prompt = None
        if prompt:
            with open(prompt, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()

        count = processor.build(force=force, limit=limit, custom_prompt=custom_prompt)
        console.print(f"[green]成功解析 {count} 篇文献[/green]")
    except Exception as e:
        console.print(f"[red]解析失败: {e}[/red]")
        raise click.Abort()


@main.command()
def rebuild():
    """强制重建所有文献"""
    try:
        processor = PaperProcessor()
        count = processor.build(force=True)
        console.print(f"[green]成功重建 {count} 篇文献[/green]")
    except Exception as e:
        console.print(f"[red]重建失败: {e}[/red]")
        raise click.Abort()


@main.command()
def render():
    """渲染 Quarto Book"""
    try:
        renderer = QuartoRenderer()
        renderer.render_all()
        renderer.generate_index()
        renderer.generate_quarto_yaml()
        console.print("[green]✓[/green] 渲染完成！")
        console.print("\n运行以下命令生成书籍：")
        console.print("  cd quarto && quarto render")
    except Exception as e:
        console.print(f"[red]渲染失败: {e}[/red]")
        raise click.Abort()


@main.command()
def stats():
    """显示统计信息"""
    try:
        processor = PaperProcessor()
        processor.stats()
    except Exception as e:
        console.print(f"[red]获取统计失败: {e}[/red]")
        raise click.Abort()


@main.command()
def collections():
    """列出 Zotero 集合"""
    try:
        processor = PaperProcessor()
        processor.list_collections()
    except Exception as e:
        console.print(f"[red]获取集合失败: {e}[/red]")
        raise click.Abort()


@main.command()
@click.argument('paper_id', type=int)
def show(paper_id: int):
    """显示单篇文献详情"""
    from .db import Database, sqlite3

    db = Database()

    conn = sqlite3.connect("paper.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, a.research_question, a.method, a.key_findings,
               a.status, a.completed_at, a.error_message
        FROM papers p
        LEFT JOIN analyses a ON p.id = a.paper_id
        WHERE p.id = ?
        ORDER BY a.id DESC
        LIMIT 1
    """, (paper_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        console.print(f"[red]未找到文献 ID: {paper_id}[/red]")
        return

    import json

    table = Table(title=f"文献详情 - {row['title'][:50]}")
    table.add_column("字段", style="cyan")
    table.add_column("值", style="green")

    table.add_row("ID", str(row['id']))
    table.add_row("Zotero Key", row['zotero_key'])
    table.add_row("标题", row['title'][:80])
    table.add_row("类型", row['item_type'])
    table.add_row("日期", row['date'] or 'N/A')

    authors = json.loads(row['authors']) if row['authors'] else []
    table.add_row("作者", ', '.join(authors[:5]) if authors else 'N/A')

    table.add_row("PDF 路径", row['pdf_path'][:60] + '...' if row['pdf_path'] else 'N/A')
    table.add_row("状态", row['status'] or 'never_analyzed')

    if row['research_question']:
        table.add_row("研究问题", row['research_question'][:80])
        table.add_row("方法", row['method'][:80] if row['method'] else 'N/A')

        findings = json.loads(row['key_findings']) if row['key_findings'] else []
        if findings:
            table.add_row("主要发现", findings[0][:80] + '...')

    if row['error_message']:
        table.add_row("错误", row['error_message'][:80])

    console.print(table)


if __name__ == '__main__':
    main()
