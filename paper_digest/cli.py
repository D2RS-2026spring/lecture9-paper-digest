"""CLI 入口 - 命令行接口"""

import click
import questionary
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .processor import PaperProcessor
from .render import Renderer

console = Console()


def do_render():
    """执行渲染"""
    renderer = Renderer()
    renderer.render_all()
    console.print("[green]✓[/green] 页面渲染完成")
    return True


def do_serve(port: int = 8080, host: str = 'localhost', no_open: bool = False):
    """启动服务器"""
    import http.server
    import socketserver
    import os
    import webbrowser
    import threading
    import time

    public_dir = Path('public')
    if not public_dir.exists():
        console.print("[red]错误: public/ 目录不存在[/red]")
        raise click.Abort()

    original_dir = os.getcwd()
    os.chdir(public_dir)

    url = f"http://{host}:{port}/"

    def open_browser():
        time.sleep(0.5)
        webbrowser.open(url)

    if not no_open:
        threading.Thread(target=open_browser, daemon=True).start()

    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            httpd = socketserver.TCPServer((host, port), http.server.SimpleHTTPRequestHandler)
            break
        except OSError as e:
            if e.errno == 48 and attempt < max_attempts - 1:
                port += 1
                url = f"http://{host}:{port}/"
            else:
                os.chdir(original_dir)
                raise
    else:
        os.chdir(original_dir)
        console.print(f"[red]错误: 无法找到可用端口[/red]")
        raise click.Abort()

    with httpd:
        console.print(f"[green]✓[/green] 服务器启动: {url}")
        if not no_open:
            console.print("[green]✓[/green] 正在打开浏览器...")
        console.print("[dim]按 Ctrl+C 停止[/dim]")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]服务器已停止[/yellow]")
        finally:
            os.chdir(original_dir)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Paper Digest - 基于 Zotero + AI 的科研文献知识库系统"""
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

        if interactive:
            selected_keys = processor.select_collections_interactive()
            if not selected_keys:
                console.print("[yellow]未选择任何集合，取消同步[/yellow]")
                return
            total_count = 0
            for key in selected_keys:
                count = processor.sync(limit=limit, collection_key=key, tag=tag)
                total_count += count
            console.print(f"[green]成功同步 {total_count} 篇文献[/green]")
            return

        if collection and len(collection) == 8 and collection.isalnum():
            count = processor.sync(limit=limit, collection_key=collection, tag=tag)
        elif collection:
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
@click.option('--batch', '-b', is_flag=True, help='使用 Batch API 模式（省50%费用）')
@click.option('--check', is_flag=True, help='检查 Batch 任务状态')
@click.option('--wait', '-w', is_flag=True, help='等待 Batch 任务完成')
@click.option('--interval', '-i', default=60, help='轮询间隔（秒）')
def build(limit: int, force: bool, prompt: str, batch: bool, check: bool, wait: bool, interval: int):
    """解析文献（默认实时模式，--batch 切换批量模式）"""
    try:
        processor = PaperProcessor()

        # 读取自定义 prompt
        custom_prompt = None
        if prompt:
            with open(prompt, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()

        # Batch 检查模式
        if check or (wait and not batch):
            count = processor.check_batch_results(wait=wait, poll_interval=interval)
            console.print(f"[green]✓[/green] 处理了 {count} 篇文献")
            return

        # Batch 提交模式
        if batch:
            batch_id = processor.build_batch(limit=limit, custom_prompt=custom_prompt)
            if batch_id:
                console.print(f"\n[green]✓[/green] Batch 任务已提交: {batch_id[:40]}...")
                console.print("[dim]使用 --check --wait 参数检查结果[/dim]")
            else:
                console.print("[yellow]没有提交新任务[/yellow]")
            return

        # 实时解析模式
        count = processor.build(force=force, limit=limit, custom_prompt=custom_prompt)
        console.print(f"[green]成功解析 {count} 篇文献[/green]")

    except Exception as e:
        console.print(f"[red]解析失败: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option('--port', '-p', default=8080, help='端口号')
@click.option('--host', '-h', default='localhost', help='主机地址')
@click.option('--no-open', is_flag=True, help='不自动打开浏览器')
@click.option('--no-render', is_flag=True, help='跳过渲染步骤')
def serve(port: int, host: str, no_open: bool, no_render: bool):
    """启动本地服务器（默认先自动渲染）"""
    try:
        if not no_render:
            do_render()
        do_serve(port=port, host=host, no_open=no_open)
    except Exception as e:
        console.print(f"[red]启动失败: {e}[/red]")
        raise click.Abort()


@main.command()
@click.option('--port', '-p', default=8080, help='端口号')
@click.option('--host', '-h', default='localhost', help='主机地址')
@click.option('--no-open', is_flag=True, help='不自动打开浏览器')
def dev(port: int, host: str, no_open: bool):
    """开发模式：强制重新渲染并启动服务器"""
    try:
        do_render()
        do_serve(port=port, host=host, no_open=no_open)
    except Exception as e:
        console.print(f"[red]启动失败: {e}[/red]")
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
    from .cache import CacheManager
    from .db import sqlite3

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

    if row['cache_key']:
        result = cache.get(row['cache_key'])
        if result:
            one_sentence = result.get('one_sentence_summary')
            if one_sentence:
                table.add_row("一句话总结", one_sentence[:80])
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
def run():
    """交互式工作流：选文献 → 同步 → 解析 → 启动服务"""
    import time

    processor = PaperProcessor()

    # Step 1: 选择集合
    console.print("\n[bold blue]步骤 1/4: 选择文献集合[/bold blue]")
    selected_keys = processor.select_collections_interactive()
    if not selected_keys:
        console.print("[yellow]未选择任何集合，取消运行[/yellow]")
        return

    # Step 2: 设置数量
    console.print("\n[bold blue]步骤 2/4: 设置同步数量[/bold blue]")
    limit_str = questionary.text(
        "最多同步多少篇文献？",
        default="10",
        validate=lambda x: x.isdigit() and int(x) > 0 or "请输入正整数"
    ).ask()
    limit = int(limit_str) if limit_str else 10

    # Step 3: 同步
    console.print("\n[bold blue]步骤 3/4: 同步文献[/bold blue]")
    total_count = 0
    for key in selected_keys:
        count = processor.sync(limit=limit, collection_key=key)
        total_count += count
    console.print(f"[green]✓[/green] 共同步 {total_count} 篇文献")

    if total_count == 0:
        console.print("[yellow]没有同步到文献，工作流结束[/yellow]")
        return

    # Step 4: 选择解析模式并执行
    console.print("\n[bold blue]步骤 4/4: 选择解析模式[/bold blue]")
    mode = questionary.select(
        "请选择解析方式：",
        choices=[
            questionary.Choice(title="🚀 实时解析 (立即返回)", value="realtime"),
            questionary.Choice(title="⏰ Batch模式 (省50%费用)", value="batch"),
        ],
        default="realtime"
    ).ask()

    if mode == "realtime":
        console.print("\n[bold blue]开始实时解析...[/bold blue]")
        processor.build(limit=limit)
    else:
        console.print("\n[bold blue]提交 Batch 任务...[/bold blue]")
        batch_id = processor.build_batch(limit=limit)
        if batch_id:
            console.print(f"[green]✓[/green] Batch 任务已提交")
            should_wait = questionary.confirm("是否等待任务完成？", default=True).ask()
            if should_wait:
                processor.check_batch_results(wait=True, poll_interval=60)
            else:
                console.print("[yellow]跳过等待，稍后使用 --check --wait 检查[/yellow]")

    # 渲染并启动服务
    console.print("\n[bold blue]启动服务...[/bold blue]")
    do_render()
    time.sleep(0.5)
    do_serve()


if __name__ == '__main__':
    main()
