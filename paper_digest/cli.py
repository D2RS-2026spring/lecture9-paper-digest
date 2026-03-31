"""CLI 入口 - 命令行接口"""

import click
import questionary
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .processor import PaperProcessor
from .render import Renderer

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Paper Digest - 基于 Zotero + AI 的科研文献知识编译系统"""
    pass


@main.command()
@click.option('--limit', '-l', default=100, help='最多同步多少篇文献')
@click.option('--collection', '-c', default=None, help='只同步指定集合的文献（支持 key 或名称，支持模糊匹配）')  # noqa: E501
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
    """生成文献展示网站"""
    try:
        renderer = Renderer()
        renderer.render_all()
        console.print("\n[green]✓[/green] 渲染完成！")
        console.print("\n文件位于: public/")
        console.print("  - index.html: 主页面")
        console.print("  - papers.json: 文献数据")
        console.print("\n本地预览:")
        console.print("  paper-digest serve")
    except Exception as e:
        console.print(f"[red]渲染失败: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise click.Abort()


@main.command()
@click.option('--port', '-p', default=8080, help='端口号')
@click.option('--host', '-h', default='localhost', help='主机地址')
@click.option('--no-open', is_flag=True, help='不自动打开浏览器')
def serve(port: int, host: str, no_open: bool):
    """启动本地服务器预览"""
    import http.server
    import socketserver
    import os
    import webbrowser
    import threading

    public_dir = Path('public')
    if not public_dir.exists():
        console.print("[red]错误: public/ 目录不存在，请先运行 paper-digest render[/red]")
        raise click.Abort()

    os.chdir(public_dir)

    url = f"http://{host}:{port}/"

    # 延迟打开浏览器，确保服务器已启动
    def open_browser():
        import time
        time.sleep(0.5)
        webbrowser.open(url)

    if not no_open:
        threading.Thread(target=open_browser, daemon=True).start()

    # 尝试绑定端口，如果被占用则尝试下一个
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            httpd = socketserver.TCPServer((host, port), http.server.SimpleHTTPRequestHandler)
            break
        except OSError as e:
            if e.errno == 48 and attempt < max_attempts - 1:  # Address already in use
                port += 1
                url = f"http://{host}:{port}/"
            else:
                raise
    else:
        console.print(f"[red]错误: 无法找到可用端口 (尝试了 {port-8080+1} 个端口)[/red]")
        raise click.Abort()

    with httpd:
        console.print(f"[green]✓[/green] 服务器启动: {url}")
        if not no_open:
            console.print("[green]✓[/green] 正在打开浏览器...")
        console.print("按 Ctrl+C 停止")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]服务器已停止[/yellow]")


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
            console.print("  paper-digest check-batch")
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


@main.command()
def run():
    """交互式工作流：选文献 → 同步 → 解析 → 生成页面 → 启动服务"""
    import time
    import http.server
    import socketserver
    import os
    import webbrowser
    import threading

    processor = PaperProcessor()

    # Step 1: 交互式选择集合
    console.print("\n[bold blue]步骤 1/5: 选择文献集合[/bold blue]")
    selected_keys = processor.select_collections_interactive()
    if not selected_keys:
        console.print("[yellow]未选择任何集合，取消运行[/yellow]")
        return

    # Step 2: 输入数量限制
    console.print("\n[bold blue]步骤 2/5: 设置同步数量[/bold blue]")
    limit_str = questionary.text(
        "最多同步多少篇文献？",
        default="10",
        validate=lambda x: x.isdigit() and int(x) > 0 or "请输入正整数"
    ).ask()
    limit = int(limit_str) if limit_str else 10

    # Step 3: 同步文献
    console.print("\n[bold blue]步骤 3/5: 同步文献[/bold blue]")
    total_count = 0
    for key in selected_keys:
        count = processor.sync(limit=limit, collection_key=key)
        total_count += count
    console.print(f"[green]✓[/green] 共同步 {total_count} 篇文献")

    if total_count == 0:
        console.print("[yellow]没有同步到文献，工作流结束[/yellow]")
        return

    # Step 4: 选择解析模式
    console.print("\n[bold blue]步骤 4/5: 选择解析模式[/bold blue]")
    mode = questionary.select(
        "请选择解析方式：",
        choices=[
            questionary.Choice(
                title="🚀 实时解析 (立即返回，费用正常)",
                value="realtime"
            ),
            questionary.Choice(
                title="⏰ Batch模式 (节省50%费用，24小时内完成)",
                value="batch"
            ),
        ],
        default="realtime"
    ).ask()

    if mode == "realtime":
        # 实时解析
        console.print("\n[bold blue]开始实时解析...[/bold blue]")
        count = processor.build(limit=limit)
        if count == 0:
            console.print("[yellow]没有需要解析的新文献[/yellow]")
    else:
        # Batch 模式
        console.print("\n[bold blue]提交 Batch 任务...[/bold blue]")
        batch_id = processor.build_batch(limit=limit)

        if batch_id:
            console.print(f"\n[green]✓[/green] Batch 任务已提交: {batch_id[:40]}...")
            console.print("[dim]Batch API 通常需要 10 分钟到数小时完成[/dim]")

            # 询问是否等待
            should_wait = questionary.confirm(
                "是否等待任务完成？（会定期轮询检查状态）",
                default=True
            ).ask()

            if should_wait:
                interval = 60
                interval_str = questionary.text(
                    "轮询间隔（秒）：",
                    default="60",
                    validate=lambda x: x.isdigit() and int(x) >= 10 or "间隔至少10秒"
                ).ask()
                interval = int(interval_str) if interval_str else 60

                console.print(f"\n[bold blue]等待 Batch 任务完成...[/bold blue]")
                console.print(f"[dim]每 {interval} 秒检查一次状态，按 Ctrl+C 取消等待[/dim]\n")

                try:
                    count = processor.check_batch_results(
                        wait=True,
                        poll_interval=interval
                    )
                    console.print(f"\n[green]✓[/green] Batch 处理完成，共 {count} 篇")
                except KeyboardInterrupt:
                    console.print("\n[yellow]已取消等待[/yellow]")
                    console.print("提示：稍后可以使用 `paper-digest check-batch --wait` 继续等待")
                    return
            else:
                console.print("\n[yellow]跳过等待[/yellow]")
                console.print("提示：稍后使用 `paper-digest check-batch --wait` 获取结果")
                # 询问是否继续生成页面
                continue_anyway = questionary.confirm(
                    "是否继续生成页面？（未完成的文献将不显示解读内容）",
                    default=False
                ).ask()
                if not continue_anyway:
                    return

    # Step 5: 生成页面并启动服务
    console.print("\n[bold blue]步骤 5/5: 生成展示页面[/bold blue]")

    try:
        renderer = Renderer()
        renderer.render_all()
        console.print("[green]✓[/green] 页面生成完成！")
    except Exception as e:
        console.print(f"[red]页面生成失败: {e}[/red]")
        raise click.Abort()

    # 启动服务器
    console.print("\n[bold blue]启动本地服务器...[/bold blue]")

    public_dir = Path('public')
    if not public_dir.exists():
        console.print("[red]错误: public/ 目录不存在[/red]")
        raise click.Abort()

    os.chdir(public_dir)

    port = 8080
    host = 'localhost'
    url = f"http://{host}:{port}/"

    # 延迟打开浏览器
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    # 尝试绑定端口
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            httpd = socketserver.TCPServer(
                (host, port),
                http.server.SimpleHTTPRequestHandler
            )
            break
        except OSError as e:
            if e.errno == 48 and attempt < max_attempts - 1:
                port += 1
                url = f"http://{host}:{port}/"
            else:
                raise
    else:
        console.print(f"[red]错误: 无法找到可用端口[/red]")
        raise click.Abort()

    console.print(f"\n[green]✓[/green] 服务器启动: {url}")
    console.print(f"[green]✓[/green] 正在打开浏览器...")
    console.print("[dim]按 Ctrl+C 停止服务器[/dim]\n")

    with httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]服务器已停止[/yellow]")


if __name__ == '__main__':
    main()
