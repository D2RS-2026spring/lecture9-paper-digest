"""主处理流程 - 协调 Zotero、LLM、数据库和缓存"""

from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

from .zotero import ZoteroClient, Paper
from .llm import QwenClient
from .db import Database
from .cache import CacheManager, CacheEntry
from .batch import QwenBatchClient, parse_batch_result


console = Console()


class PaperProcessor:
    """文献处理器"""

    def __init__(self):
        self.zotero = ZoteroClient()
        self.llm = QwenClient()
        self.db = Database()
        self.cache = CacheManager()

    def sync(self, limit: int = 100, collection_key: Optional[str] = None) -> int:
        """
        从 Zotero 同步文献到数据库

        Args:
            limit: 最多同步多少篇文献
            collection_key: 只同步指定集合的文献

        Returns:
            同步的文献数量
        """
        console.print("[bold blue]正在从 Zotero 同步文献...[/bold blue]")

        # 获取带 PDF 的文献
        papers = self.zotero.get_papers_with_pdf(limit=limit, collection_key=collection_key)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("同步文献...", total=len(papers))

            for paper in papers:
                # 计算 PDF hash 用于缓存验证
                from .llm import compute_file_hash
                pdf_hash = compute_file_hash(paper.pdf_path)

                # 添加到数据库
                self.db.add_paper(
                    zotero_key=paper.zotero_key,
                    title=paper.title,
                    item_type=paper.item_type,
                    date=paper.date,
                    authors=paper.authors,
                    pdf_path=paper.pdf_path,
                    zotero_link=paper.zotero_link,
                    pdf_hash=pdf_hash
                )
                progress.advance(task)

        console.print(f"[green]✓[/green] 同步完成：{len(papers)} 篇文献")
        return len(papers)

    def build(self, force: bool = False, limit: Optional[int] = None,
              custom_prompt: Optional[str] = None) -> int:
        """
        构建/解析文献

        Args:
            force: 是否强制重新解析
            limit: 最多解析多少篇，None 表示全部
            custom_prompt: 自定义 prompt

        Returns:
            新解析的文献数量
        """
        # 获取未分析的文献
        unanalyzed = self.db.get_unanalyzed_papers()

        if limit:
            unanalyzed = unanalyzed[:limit]

        if not unanalyzed:
            console.print("[yellow]没有需要解析的文献[/yellow]")
            return 0

        console.print(f"[bold blue]开始解析 {len(unanalyzed)} 篇文献...[/bold blue]")

        processed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("解析文献...", total=len(unanalyzed))

            for paper_info in unanalyzed:
                paper_id = paper_info['id']
                title = paper_info['title']
                pdf_path = paper_info['pdf_path']

                progress.update(task, description=f"解析: {title[:30]}...")

                try:
                    # 计算缓存 key
                    prompt = custom_prompt or self.llm.DEFAULT_SYSTEM_PROMPT
                    cache_key = self.llm.compute_cache_key(pdf_path, prompt, self.llm.model)

                    # 检查缓存
                    if not force:
                        cached = self.cache.get(cache_key)
                        if cached:
                            # 使用缓存结果
                            self._save_result(paper_id, cached, cache_key)
                            console.print(f"  [green]✓[/green] {title[:40]}... (缓存)")
                            processed += 1
                            progress.advance(task)
                            continue

                        # 检查数据库中是否有相同缓存 key 的完成记录
                        db_analysis = self.db.get_analysis_by_cache_key(cache_key)
                        if db_analysis:
                            console.print(f"  [green]✓[/green] {title[:40]}... (数据库缓存)")
                            processed += 1
                            progress.advance(task)
                            continue

                    # 创建分析记录
                    analysis_id = self.db.create_analysis(
                        paper_id=paper_id,
                        cache_key=cache_key,
                        prompt_version=hash(prompt) % 10000,
                        model_version=self.llm.model
                    )

                    # 更新状态为处理中
                    self.db.update_analysis_status(analysis_id, 'processing')

                    # 调用 LLM 分析
                    result = self.llm.analyze_pdf(pdf_path, system_prompt=custom_prompt)

                    # 保存结果
                    self._save_result(paper_id, result, cache_key)

                    # 同时保存到文件缓存
                    cache_entry = CacheEntry(
                        cache_key=cache_key,
                        pdf_hash=self.cache.compute_file_hash(pdf_path),
                        prompt_hash=cache_key.split('_')[1],
                        model=self.llm.model,
                        research_question=result.research_question,
                        method=result.method,
                        key_findings=result.key_findings,
                        raw_response=result.raw_response,
                        created_at=datetime.now().isoformat()
                    )
                    self.cache.set(cache_entry)

                    console.print(f"  [green]✓[/green] {title[:40]}...")
                    processed += 1

                except Exception as e:
                    console.print(f"  [red]✗[/red] {title[:40]}...: {str(e)[:50]}")
                    if 'analysis_id' in locals():
                        self.db.update_analysis_status(analysis_id, 'failed', str(e))

                progress.advance(task)

        console.print(f"[green]✓[/green] 解析完成：{processed} 篇文献")
        return processed

    def _save_result(self, paper_id: int, result, cache_key: str):
        """保存分析结果到数据库"""
        # 查找或创建分析记录
        # 这里简化处理，直接更新最新的 pending/completed 记录
        # 实际应该通过 ID 精确查找

        # 暂时使用 create + update 模式
        from .db import Database
        db = Database()

        # 由于 db.py 没有 get_analysis_by_paper_id，我们创建一个
        analysis_id = self._get_or_create_analysis(paper_id, cache_key)

        db.save_analysis_result(
            analysis_id=analysis_id,
            research_question=result.research_question,
            method=result.method,
            key_findings=result.key_findings if isinstance(result.key_findings, list) else [result.key_findings],
            raw_response=result.raw_response
        )

    def _get_or_create_analysis(self, paper_id: int, cache_key: str) -> int:
        """获取或创建分析记录"""
        import sqlite3
        conn = sqlite3.connect("paper.db")
        cursor = conn.cursor()

        # 查找现有的记录
        cursor.execute("""
            SELECT id FROM analyses
            WHERE paper_id = ? AND cache_key = ?
            ORDER BY id DESC LIMIT 1
        """, (paper_id, cache_key))

        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]

        # 创建新记录
        cursor.execute("""
            INSERT INTO analyses (paper_id, status, cache_key)
            VALUES (?, 'pending', ?)
        """, (paper_id, cache_key))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def stats(self):
        """显示统计信息"""
        stats = self.db.get_stats()

        console.print("\n[bold]文献统计[/bold]")
        console.print(f"  总文献数: {stats['total_papers']}")
        console.print(f"  从未分析: {stats['never_analyzed']}")
        console.print(f"  等待中: {stats['pending']}")
        console.print(f"  处理中: {stats['processing']}")
        if stats.get('batch_running', 0) > 0:
            console.print(f"  [yellow]Batch 运行中: {stats['batch_running']}[/yellow]")
        console.print(f"  [green]已完成: {stats['completed']}[/green]")
        console.print(f"  [red]失败: {stats['failed']}[/red]")

    def list_collections(self):
        """列出所有集合"""
        collections = self.zotero.get_all_collections()

        console.print("\n[bold]Zotero 集合[/bold]")
        for c in collections:
            console.print(f"  {c['key']}: {c['name']}")

    def build_batch(self, limit: Optional[int] = None,
                    custom_prompt: Optional[str] = None) -> Optional[str]:
        """
        使用 Batch API 批量提交文献分析任务

        Args:
            limit: 最多提交多少篇，None 表示全部
            custom_prompt: 自定义 prompt

        Returns:
            Batch 任务 ID，失败返回 None
        """
        # 获取未分析的文献
        unanalyzed = self.db.get_unanalyzed_papers()

        if limit:
            unanalyzed = unanalyzed[:limit]

        if not unanalyzed:
            console.print("[yellow]没有需要提交的文献[/yellow]")
            return None

        console.print(f"[bold blue]准备使用 Batch API 提交 {len(unanalyzed)} 篇文献...[/bold blue]")
        console.print("[dim]Batch API 费用为实时调用的 50%，通常 24 小时内完成[/dim]")

        # 创建 Batch 请求
        batch_client = QwenBatchClient()
        requests = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("准备 Batch 请求...", total=len(unanalyzed))

            for paper_info in unanalyzed:
                paper_id = paper_info['id']
                title = paper_info['title']
                pdf_path = paper_info['pdf_path']

                progress.update(task, description=f"准备: {title[:30]}...")

                try:
                    # 计算缓存 key
                    prompt = custom_prompt or batch_client.DEFAULT_SYSTEM_PROMPT
                    from .llm import compute_file_hash
                    pdf_hash = compute_file_hash(pdf_path)
                    import hashlib
                    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
                    cache_key = f"{pdf_hash}_{prompt_hash}_qwen-long"

                    # 检查缓存（跳过已缓存的）
                    cached = self.cache.get(cache_key)
                    if cached:
                        console.print(f"  [dim]跳过已缓存: {title[:40]}...[/dim]")
                        progress.advance(task)
                        continue

                    # 创建 Batch 请求
                    request = batch_client.create_batch_request(
                        paper_id=str(paper_id),
                        pdf_path=pdf_path,
                        custom_prompt=custom_prompt
                    )
                    requests.append((paper_id, request, cache_key))

                except Exception as e:
                    console.print(f"  [red]✗[/red] {title[:40]}...: {str(e)[:50]}")

                progress.advance(task)

        if not requests:
            console.print("[yellow]没有需要提交的新文献（都已缓存）[/yellow]")
            return None

        console.print(f"[green]✓[/green] 准备了 {len(requests)} 个 Batch 请求")

        # 创建 Batch 任务
        try:
            job = batch_client.create_batch_job([r[1] for r in requests])
            console.print(f"[green]✓[/green] Batch 任务创建成功: {job.batch_id}")

            # 记录到数据库
            for paper_id, request, cache_key in requests:
                self.db.create_batch_analysis(
                    paper_id=paper_id,
                    batch_id=job.batch_id,
                    input_file_id=job.input_file_id,
                    cache_key=cache_key,
                    prompt_version=hash(custom_prompt or "") % 10000,
                    model_version="qwen-long"
                )

            return job.batch_id

        except Exception as e:
            console.print(f"[red]创建 Batch 任务失败: {e}[/red]")
            return None

    def check_batch_results(self, wait: bool = False,
                           poll_interval: int = 60) -> int:
        """
        检查 Batch 任务状态并获取结果

        Args:
            wait: 是否等待任务完成
            poll_interval: 轮询间隔（秒）

        Returns:
            获取结果的文献数量
        """
        # 获取需要检查的 Batch 任务
        analyses = self.db.get_batch_analyses_to_check()

        if not analyses:
            console.print("[yellow]没有正在运行的 Batch 任务[/yellow]")
            return 0

        batch_client = QwenBatchClient()
        processed = 0

        # 按 batch_id 分组
        batch_groups = {}
        for analysis in analyses:
            batch_id = analysis['batch_id']
            if batch_id not in batch_groups:
                batch_groups[batch_id] = []
            batch_groups[batch_id].append(analysis)

        console.print(f"[bold blue]检查 {len(batch_groups)} 个 Batch 任务...[/bold blue]")

        for batch_id, group_analyses in batch_groups.items():
            console.print(f"\n检查 Batch: {batch_id[:30]}...")
            console.print(f"  包含 {len(group_analyses)} 篇文献")

            try:
                if wait:
                    # 等待任务完成
                    job = batch_client.wait_for_completion(
                        batch_id=batch_id,
                        poll_interval=poll_interval
                    )
                else:
                    # 只检查一次状态
                    job = batch_client.check_batch_status(batch_id)

                console.print(f"  状态: {job.status}")

                # 更新数据库中的状态
                for analysis in group_analyses:
                    self.db.update_batch_status(
                        analysis_id=analysis['id'],
                        batch_status=job.status,
                        output_file_id=job.output_file_id,
                        error_file_id=job.error_file_id
                    )

                # 如果完成，下载结果
                if job.status == 'completed' and job.output_file_id:
                    results = batch_client.download_results(job.output_file_id)
                    console.print(f"  下载到 {len(results)} 个结果")

                    # 解析并保存结果
                    for result in results:
                        analysis_id = int(result.custom_id)

                        # 查找对应的 analysis 记录
                        for analysis in group_analyses:
                            if analysis['id'] == analysis_id:
                                parsed = parse_batch_result(result)
                                if parsed:
                                    self.db.save_analysis_result(
                                        analysis_id=analysis_id,
                                        research_question=parsed['research_question'],
                                        method=parsed['method'],
                                        key_findings=parsed['key_findings'],
                                        raw_response=parsed['raw_response']
                                    )
                                    processed += 1
                                    console.print(f"    [green]✓[/green] {analysis['title'][:40]}...")
                                else:
                                    console.print(f"    [red]✗[/red] 解析失败: {analysis['title'][:40]}...")
                                break

                elif job.status == 'failed':
                    console.print(f"  [red]Batch 任务失败[/red]")

            except Exception as e:
                console.print(f"  [red]检查失败: {e}[/red]")

        console.print(f"\n[green]✓[/green] 完成：处理了 {processed} 篇文献")
        return processed
