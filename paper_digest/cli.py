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
@click.option('--collection', '-c', default=None, help='只同步指定集合的文献（支持 key 或名称，支持模糊匹配）')
@click.option('--tag', '-t', default=None, help='只同步指定标签的文献')
@click.option('--interactive', '-i', is_flag=True, help='使用交互式界面选择集合')
def sync(limit: int, collection: str, tag: str, interactive: bool):
    """从 Zotero 同步文献"""
    try:
        processor = PaperProcessor()

        # 交互式模式
        if interactive:
            selected_keys = processor.select_collections_interactive()
            if not selected_keys:
                console.print("[yellow]未选择任何集合，取消同步[/yellow]")
                return
            # 同步选中的集合
            total_count = 0
            for key in selected_keys:
                count = processor.sync(limit=limit, collection_key=key, tag=tag)
                total_count += count
            console.print(f"[green]成功同步 {total_count} 篇文献[/green]")
            return

        # 判断 collection 是 key 还是 name
        # key 通常是 8 位字母数字混合，如 "ABCD1234"
        if collection and len(collection) == 8 and collection.isalnum():
            # 可能是 key，直接使用
            count = processor.sync(limit=limit, collection_key=collection, tag=tag)
        elif collection:
            # 按名称查找
            count = processor.sync(limit=limit, collection_name=collection, tag=tag)
        else:
            count = processor.sync(limit=limit, tag=tag)

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
def tags():
    """列出 Zotero 标签"""
    try:
        processor = PaperProcessor()
        processor.list_tags()
    except Exception as e:
        console.print(f"[red]获取标签失败: {e}[/red]")
        raise click.Abort()


@main.command()
@click.argument('paper_id', type=int)
def show(paper_id: int):
    """显示单篇文献详情"""
    from .db import Database, sqlite3
    from .cache import CacheManager

    db = Database()
    cache = CacheManager()

    conn = sqlite3.connect("paper.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, a.status, a.completed_at, a.error_message,
               a.batch_id, a.batch_status, a.cache_key
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

    if row['batch_id']:
        table.add_row("Batch ID", row['batch_id'][:30] + '...')
        table.add_row("Batch 状态", row['batch_status'] or 'N/A')

    # 从缓存读取分析结果
    if row['cache_key']:
        result = cache.get(row['cache_key'])
        if result:
            # 尝试提取关键信息
            one_sentence = result.get('one_sentence_summary')
            if one_sentence:
                table.add_row("一句话总结", one_sentence[:80])
            # 显示更多字段
            for key, label in [
                ('research_background', '研究背景'),
                ('research_conclusion', '研究结论'),
                ('innovation_points', '创新点'),
            ]:
                value = result.get(key)
                if value:
                    table.add_row(label, value[:80] + '...')

    if row['error_message']:
        table.add_row("错误", row['error_message'][:80])

    console.print(table)


@main.command()
@click.option('--limit', '-l', default=None, type=int, help='最多提交多少篇')
@click.option('--prompt', '-p', default=None, help='自定义 prompt 文件路径')
def submit_batch(limit: int, prompt: str):
    """使用 Batch API 提交文献分析任务（节省 50% 费用）"""
    try:
        processor = PaperProcessor()

        # 读取自定义 prompt
        custom_prompt = None
        if prompt:
            with open(prompt, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()

        batch_id = processor.build_batch(limit=limit, custom_prompt=custom_prompt)

        if batch_id:
            console.print(f"\n[green]✓[/green] Batch 任务已提交: {batch_id}")
            console.print("\n使用以下命令检查结果：")
            console.print(f"  paper-digest check-batch")
        else:
            console.print("[yellow]没有提交新任务[/yellow]")

    except Exception as e:
        console.print(f"[red]提交失败: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option('--wait', '-w', is_flag=True, help='等待任务完成')
@click.option('--interval', '-i', default=60, help='轮询间隔（秒）')
def check_batch(wait: bool, interval: int):
    """检查 Batch 任务状态并获取结果"""
    try:
        processor = PaperProcessor()
        count = processor.check_batch_results(
            wait=wait,
            poll_interval=interval
        )
        console.print(f"[green]✓[/green] 获取了 {count} 篇文献的结果")
    except Exception as e:
        console.print(f"[red]检查失败: {e}[/red]")
        raise click.Abort()


if __name__ == '__main__':
    main()
