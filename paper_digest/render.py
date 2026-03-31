"""渲染模块 - 生成单页面应用"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console

console = Console()


class Renderer:
    """渲染器 - 生成单页面文献展示网站"""

    def __init__(self, output_dir: str = "public"):
        self.output_dir = Path(output_dir)
        self.db_path = "paper.db"

    def setup(self):
        """初始化目录"""
        self.output_dir.mkdir(exist_ok=True)

    def export_papers_json(self) -> Path:
        """导出所有文献数据为 JSON"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, a.status, a.cache_key, a.completed_at
            FROM papers p
            LEFT JOIN analyses a ON p.id = a.paper_id
            ORDER BY p.id DESC
        """)

        papers = []
        for row in cursor.fetchall():
            paper = {
                "id": row["id"],
                "title": row["title"],
                "authors": json.loads(row["authors"]) if row["authors"] else [],
                "date": row["date"],
                "year": self._extract_year(row["date"]),
                "item_type": row["item_type"],
                "zotero_key": row["zotero_key"],
                "zotero_link": row["zotero_link"],
                "created_at": row["created_at"],
                "status": row["status"] or "never_analyzed",
                "completed_at": row["completed_at"],
            }

            if row["cache_key"]:
                analysis = self._load_analysis(row["cache_key"])
                if analysis:
                    paper["analysis"] = {
                        "basic_info": analysis.get("basic_info", {}),
                        "research_background": analysis.get("research_background", ""),
                        "research_conclusion": analysis.get("research_conclusion", ""),
                        "innovation_points": analysis.get("innovation_points", ""),
                        "experimental_design": analysis.get("experimental_design", ""),
                        "discussion": analysis.get("discussion", ""),
                        "industrial_feasibility": analysis.get("industrial_feasibility", ""),
                        "one_sentence_summary": analysis.get("one_sentence_summary", ""),
                    }
                    paper["journal"] = analysis.get("basic_info", {}).get("journal", "")
                    paper["year_published"] = analysis.get("basic_info", {}).get("year", "")
                else:
                    paper["analysis"] = None
                    paper["journal"] = ""
                    paper["year_published"] = ""
            else:
                paper["analysis"] = None
                paper["journal"] = ""
                paper["year_published"] = ""

            papers.append(paper)

        conn.close()

        json_path = self.output_dir / "papers.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)

        console.print(f"[green]✓[/green] 导出 {len(papers)} 篇文献: {json_path}")
        return json_path

    def _extract_year(self, date_str: Optional[str]) -> int:
        if not date_str:
            return 0
        import re
        match = re.search(r'\d{4}', date_str)
        return int(match.group()) if match else 0

    def _load_analysis(self, cache_key: str) -> Optional[Dict]:
        cache_path = Path(".cache") / f"{cache_key}.json"
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def generate_html(self) -> Path:
        html_path = self.output_dir / "index.html"
        html_content = self._get_html_template()
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        console.print(f"[green]✓[/green] 生成页面: {html_path}")
        return html_path

    def _get_html_template(self) -> str:
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper Digest - 文献知识库</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; color: #333; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; margin-bottom: 30px; }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .stats-bar { display: flex; justify-content: center; gap: 40px; margin-top: 20px; flex-wrap: wrap; }
        .stat-value { font-size: 2em; font-weight: bold; }
        .controls { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 15px; align-items: center; }
        input, select { padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; }
        .search-box { flex: 1; min-width: 200px; }
        .search-box input { width: 100%; }
        .view-switcher { display: flex; gap: 8px; background: #f0f0f0; padding: 4px; border-radius: 8px; }
        .view-btn { padding: 6px 12px; border: none; background: transparent; border-radius: 6px; cursor: pointer; font-size: 14px; color: #666; }
        .view-btn.active { background: white; color: #667eea; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .papers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .paper-card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #f0f0f0; }
        .paper-summary-view { padding: 20px; cursor: pointer; }
        .paper-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .paper-id { color: #999; font-size: 12px; font-family: monospace; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; background: #e8f5e9; color: #2e7d32; }
        .paper-title { font-size: 1.1em; font-weight: 600; margin-bottom: 10px; line-height: 1.4; }
        .paper-one-sentence { padding: 12px; background: #f8f9fa; border-radius: 8px; border-left: 3px solid #667eea; }
        .paper-card { cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
        .paper-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.12); }
        .btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; border: none; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #f0f0f0; color: #666; }
        .papers-list { display: flex; flex-direction: column; gap: 24px; margin-bottom: 30px; }
        .paper-list-item { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 24px; border: 1px solid #f0f0f0; }
        .paper-list-item .paper-title { font-size: 1.2em; font-weight: 600; margin-bottom: 10px; }
        .paper-list-item .paper-meta-row { color: #666; font-size: 0.9em; margin-bottom: 12px; }
        .paper-list-item .paper-one-sentence { margin-top: 16px; padding: 16px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea; }
        .paper-list-item .full-analysis { margin-top: 20px; padding-top: 20px; border-top: 1px solid #f0f0f0; }
        .paper-list-item .analysis-section { margin-bottom: 16px; }
        .paper-list-item .analysis-section h5 { color: #667eea; font-size: 0.85em; font-weight: 600; margin-bottom: 6px; }
        .paper-list-item .analysis-section p { color: #444; font-size: 0.95em; line-height: 1.7; white-space: pre-wrap; }
        .pagination { display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 30px; }
        .pagination button { padding: 10px 20px; border: 1px solid #e0e0e0; background: white; border-radius: 8px; cursor: pointer; }
        .pagination button:hover:not(:disabled) { background: #667eea; color: white; border-color: #667eea; }
        .pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
        .overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; }
        .overlay.active { display: block; }
        .modal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); z-index: 101; max-width: 800px; width: 90%; max-height: 85vh; overflow: hidden; }
        .modal.active { display: block; }
        .modal-header { padding: 20px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .modal-header h2 { font-size: 1.3em; margin: 0; line-height: 1.4; }
        .modal-header .meta { margin-top: 8px; font-size: 0.9em; opacity: 0.9; }
        .modal-body { padding: 24px; overflow-y: auto; max-height: calc(85vh - 140px); }
        .modal-section { margin-bottom: 20px; }
        .modal-section:last-child { margin-bottom: 0; }
        .modal-section h4 { color: #667eea; font-size: 0.95em; font-weight: 600; margin-bottom: 10px; }
        .modal-section p { color: #444; font-size: 0.95em; line-height: 1.8; white-space: pre-wrap; }
        .modal-footer { padding: 16px 24px; border-top: 1px solid #f0f0f0; display: flex; gap: 10px; justify-content: flex-end; }
        .modal-close { position: absolute; top: 16px; right: 16px; background: rgba(255,255,255,0.2); border: none; color: white; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; }
        .modal-close:hover { background: rgba(255,255,255,0.3); }
        @media (max-width: 768px) { .papers-grid { grid-template-columns: 1fr; } .modal { width: 95%; max-height: 90vh; } .modal-body { max-height: calc(90vh - 140px); } }
    </style>
</head>
<body>
    <div class="overlay" id="overlay"></div>
    <div class="modal" id="modal">
        <button class="modal-close" onclick="closeModal()">×</button>
        <div class="modal-header" id="modal-header">
            <h2 id="modal-title"></h2>
            <div class="meta" id="modal-meta"></div>
        </div>
        <div class="modal-body" id="modal-body"></div>
        <div class="modal-footer">
            <a id="modal-zotero-link" href="#" target="_blank" class="btn btn-primary">📚 在 Zotero 中打开</a>
            <button class="btn btn-secondary" onclick="closeModal()">✕ 关闭</button>
        </div>
    </div>
    <header>
        <h1>Paper Digest</h1>
        <p>基于 Zotero + AI 的科研文献知识库</p>
        <div class="stats-bar">
            <div class="stat-item"><div class="stat-value" id="total-count">-</div><div class="stat-label">总文献</div></div>
            <div class="stat-item"><div class="stat-value" id="completed-count">-</div><div class="stat-label">已解读</div></div>
        </div>
    </header>
    <div class="container">
        <div class="controls">
            <div class="control-group search-box"><input type="text" id="search" placeholder="搜索标题、作者、解读内容..."></div>
            <div class="control-group"><label>排序:</label><select id="sort-by"><option value="created_at_desc">生成时间 (新→旧)</option><option value="created_at_asc">生成时间 (旧→新)</option><option value="date_desc">发表时间 (新→旧)</option><option value="date_asc">发表时间 (旧→新)</option><option value="title">标题</option></select></div>
            <div class="control-group"><label>每页:</label><select id="per-page"><option value="10">10</option><option value="20" selected>20</option><option value="50">50</option></select></div>
            <div class="control-group">
                <div class="view-switcher">
                    <button class="view-btn active" data-view="grid">⊞ 卡片</button>
                    <button class="view-btn" data-view="list">☰ 列表</button>
                </div>
            </div>
        </div>
        <div class="loading" id="loading">加载中...</div>
        <div class="no-results" id="no-results" style="display: none;">没有找到匹配的文献</div>
        <div class="papers-grid" id="papers-grid"></div>
        <div class="papers-list" id="papers-list" style="display: none;"></div>
        <div class="pagination" id="pagination" style="display: none;">
            <button id="prev-page">← 上一页</button>
            <span class="page-info" id="page-info"></span>
            <button id="next-page">下一页 →</button>
        </div>
    </div>
    <script>
        let allPapers = [];
        let filteredPapers = [];
        let currentPage = 1;
        let perPage = 20;
        let expandedPaperId = null;
        let currentView = 'grid';

        async function init() {
            try {
                const response = await fetch('papers.json');
                allPapers = await response.json();
                restoreStateFromURL();
                updateStats();
                applyFilters();
                document.getElementById('loading').style.display = 'none';
            } catch (error) {
                console.error('加载失败:', error);
                document.getElementById('loading').textContent = '加载失败，请使用本地服务器: paper-digest serve';
            }
        }

        function restoreStateFromURL() {
            const params = new URLSearchParams(window.location.search);
            const sortBy = params.get('sort');
            if (sortBy) document.getElementById('sort-by').value = sortBy;
            const perPageParam = params.get('perPage');
            if (perPageParam) { perPage = parseInt(perPageParam); document.getElementById('per-page').value = perPageParam; }
            const page = params.get('page');
            if (page) currentPage = parseInt(page);
            const search = params.get('search');
            if (search) document.getElementById('search').value = search;
            const paperId = params.get('paper');
            if (paperId) expandedPaperId = parseInt(paperId);
            const view = params.get('view');
            if (view && (view === 'grid' || view === 'list')) {
                currentView = view;
                document.querySelectorAll('.view-btn').forEach(btn => { btn.classList.toggle('active', btn.dataset.view === view); });
            }
        }

        function updateURL() {
            const params = new URLSearchParams();
            if (currentPage > 1) params.set('page', currentPage);
            if (perPage !== 20) params.set('perPage', perPage);
            const sortBy = document.getElementById('sort-by').value;
            if (sortBy !== 'created_at_desc') params.set('sort', sortBy);
            const search = document.getElementById('search').value.trim();
            if (search) params.set('search', search);
            if (expandedPaperId) params.set('paper', expandedPaperId);
            if (currentView !== 'grid') params.set('view', currentView);
            const newURL = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;
            window.history.replaceState({}, '', newURL);
        }

        function updateStats() {
            document.getElementById('total-count').textContent = allPapers.length;
            const completed = allPapers.filter(p => p.status === 'completed').length;
            document.getElementById('completed-count').textContent = completed;
        }

        function applyFilters() {
            const searchTerm = document.getElementById('search').value.toLowerCase();
            const sortBy = document.getElementById('sort-by').value;
            filteredPapers = allPapers.filter(paper => {
                if (!searchTerm) return true;
                const analysis = paper.analysis || {};
                const searchable = [paper.title, paper.authors?.join(' '), paper.journal, analysis.one_sentence_summary, analysis.research_background, analysis.research_conclusion].join(' ').toLowerCase();
                return searchable.includes(searchTerm);
            });
            filteredPapers.sort((a, b) => {
                switch (sortBy) {
                    case 'created_at_desc': return (b.created_at || '').localeCompare(a.created_at || '');
                    case 'created_at_asc': return (a.created_at || '').localeCompare(b.created_at || '');
                    case 'date_desc': return (b.year || 0) - (a.year || 0);
                    case 'date_asc': return (a.year || 0) - (b.year || 0);
                    case 'title': return (a.title || '').localeCompare(b.title || '');
                    default: return 0;
                }
            });
            const totalPages = Math.ceil(filteredPapers.length / perPage) || 1;
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;
            const start = (currentPage - 1) * perPage;
            const end = start + perPage;
            renderCurrentView(filteredPapers.slice(start, end));
            renderPagination(totalPages);
            updateURL();
            if (expandedPaperId) {
                openModal(expandedPaperId);
            }
        }

        function renderCurrentView(papers) {
            if (currentView === 'list') {
                document.getElementById('papers-grid').style.display = 'none';
                renderPapersList(papers);
            } else {
                document.getElementById('papers-list').style.display = 'none';
                renderPapersGrid(papers);
            }
        }

        function renderPapersGrid(papers) {
            const grid = document.getElementById('papers-grid');
            if (papers.length === 0) { grid.style.display = 'none'; document.getElementById('no-results').style.display = 'block'; return; }
            grid.style.display = 'grid'; document.getElementById('no-results').style.display = 'none';
            grid.innerHTML = papers.map(paper => renderPaperCard(paper)).join('');
            papers.forEach(paper => {
                const card = document.querySelector(`[data-paper-id="${paper.id}"]`);
                card.addEventListener('click', () => openModal(paper.id));
            });
        }

        function renderPaperCard(paper) {
            const analysis = paper.analysis || {};
            const hasAnalysis = paper.status === 'completed' && analysis.one_sentence_summary;
            return `<div class="paper-card" data-paper-id="${paper.id}"><div class="paper-summary-view"><div class="paper-header"><span class="paper-id">#${String(paper.id).padStart(4, '0')}</span><div class="paper-badges"><span class="badge">${paper.year || ''}</span></div></div><div class="paper-title">${escapeHtml(paper.title)}</div><div class="paper-meta">${escapeHtml(paper.journal || '')} · ${paper.authors?.slice(0, 2).join(', ') || ''}</div>${hasAnalysis ? `<div class="paper-one-sentence">${escapeHtml(analysis.one_sentence_summary)}</div>` : ''}</div></div>`;
        }

        function openModal(paperId) {
            const paper = allPapers.find(p => p.id === paperId);
            if (!paper) return;

            expandedPaperId = paperId;
            document.getElementById('modal-title').textContent = paper.title;
            document.getElementById('modal-meta').textContent = `${paper.authors?.join(', ') || ''} · ${paper.journal || ''} · ${paper.year || ''}`;
            document.getElementById('modal-zotero-link').href = paper.zotero_link;

            const analysis = paper.analysis || {};
            const hasAnalysis = paper.status === 'completed' && analysis.one_sentence_summary;

            if (hasAnalysis) {
                const sections = [
                    {key: 'one_sentence_summary', title: '一句话解读'},
                    {key: 'research_background', title: '研究背景'},
                    {key: 'research_conclusion', title: '研究结论'},
                    {key: 'innovation_points', title: '核心创新点'},
                    {key: 'experimental_design', title: '实验设计'},
                    {key: 'discussion', title: '讨论'},
                    {key: 'industrial_feasibility', title: '产业转化可行性'}
                ];
                document.getElementById('modal-body').innerHTML = sections.map(section => {
                    const content = analysis[section.key];
                    if (!content) return '';
                    return `<div class="modal-section"><h4>${section.title}</h4><p>${escapeHtml(content)}</p></div>`;
                }).join('');
            } else {
                document.getElementById('modal-body').innerHTML = '<p style="color: #666; text-align: center; padding: 40px;">此文献尚未完成 AI 分析</p>';
            }

            document.getElementById('overlay').classList.add('active');
            document.getElementById('modal').classList.add('active');
            document.body.style.overflow = 'hidden';
            updateURL();
        }

        function closeModal() {
            document.getElementById('overlay').classList.remove('active');
            document.getElementById('modal').classList.remove('active');
            document.body.style.overflow = '';
            expandedPaperId = null;
            updateURL();
        }

        function renderPapersList(papers) {
            const list = document.getElementById('papers-list');
            if (papers.length === 0) { list.style.display = 'none'; document.getElementById('no-results').style.display = 'block'; return; }
            list.style.display = 'flex'; document.getElementById('no-results').style.display = 'none';
            list.innerHTML = papers.map(paper => renderPaperListItem(paper)).join('');
        }

        function renderPaperListItem(paper) {
            const analysis = paper.analysis || {};
            const hasAnalysis = paper.status === 'completed' && analysis.one_sentence_summary;
            return `<div class="paper-list-item"><div class="paper-header"><span class="paper-id">#${String(paper.id).padStart(4, '0')}</span><div class="paper-badges"><span class="badge">${paper.year || ''}</span>${paper.journal ? `<span class="badge">${escapeHtml(paper.journal)}</span>` : ''}</div></div><div class="paper-title">${escapeHtml(paper.title)}</div><div class="paper-meta-row">${paper.authors?.join(', ') || ''}</div>${hasAnalysis ? `<div class="paper-one-sentence"><strong>一句话解读：</strong>${escapeHtml(analysis.one_sentence_summary)}</div><div class="full-analysis">${renderAnalysisSections(analysis)}</div>` : '<p>此文献尚未完成 AI 分析</p>'}<div class="detail-actions" style="margin-top: 20px;"><a href="${paper.zotero_link}" target="_blank" class="btn btn-primary">📚 在 Zotero 中打开</a></div></div>`;
        }

        function renderAnalysisSections(analysis) {
            const sections = [{key: 'research_background', title: '研究背景'}, {key: 'research_conclusion', title: '研究结论'}, {key: 'innovation_points', title: '核心创新点'}, {key: 'experimental_design', title: '实验设计'}, {key: 'discussion', title: '讨论'}, {key: 'industrial_feasibility', title: '产业转化可行性'}];
            return sections.map(section => { const content = analysis[section.key]; if (!content) return ''; return `<div class="analysis-section"><h5>${section.title}</h5><p>${escapeHtml(content)}</p></div>`; }).join('');
        }

        function renderPagination(totalPages) {
            const pagination = document.getElementById('pagination');
            if (totalPages <= 1) { pagination.style.display = 'none'; return; }
            pagination.style.display = 'flex';
            document.getElementById('page-info').textContent = `${currentPage} / ${totalPages}`;
            document.getElementById('prev-page').disabled = currentPage === 1;
            document.getElementById('next-page').disabled = currentPage === totalPages;
        }

        function escapeHtml(text) { if (!text) return ''; const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }

        document.getElementById('search').addEventListener('input', () => { currentPage = 1; applyFilters(); });
        document.getElementById('sort-by').addEventListener('change', () => { applyFilters(); });
        document.getElementById('per-page').addEventListener('change', (e) => { perPage = parseInt(e.target.value); currentPage = 1; applyFilters(); });
        document.getElementById('prev-page').addEventListener('click', () => { if (currentPage > 1) { currentPage--; applyFilters(); } });
        document.getElementById('next-page').addEventListener('click', () => { const totalPages = Math.ceil(filteredPapers.length / perPage); if (currentPage < totalPages) { currentPage++; applyFilters(); } });
        document.querySelectorAll('.view-btn').forEach(btn => { btn.addEventListener('click', () => { document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); currentView = btn.dataset.view; const totalPages = Math.ceil(filteredPapers.length / perPage) || 1; const start = (currentPage - 1) * perPage; const end = start + perPage; updateURL(); renderCurrentView(filteredPapers.slice(start, end)); }); });
        document.getElementById('overlay').addEventListener('click', closeModal);
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

        init();
    </script>
</body>
</html>'''

    def render_all(self):
        """执行完整渲染"""
        self.setup()
        self.export_papers_json()
        self.generate_html()
        console.print(f"\n[green]✓[/green] 渲染完成！文件位于: {self.output_dir}/")
        console.print(f"  - index.html: 主页面")
        console.print(f"  - papers.json: 文献数据")
        console.print(f"\n本地预览: paper-digest serve")
