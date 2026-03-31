# Paper Digest

基于 Zotero + AI 的科研文献知识库系统。

## 功能说明

- **Zotero 集成**：自动同步本地文献库，提取 PDF 和元数据
- **AI 解析**：使用 Qwen-long 提取研究背景、结论、创新点、实验设计、讨论、产业可行性
- **Batch API**：批量处理节省 50% 费用
- **智能缓存**：相同 PDF + Prompt 不重复调用
- **单页面应用**：现代化的文献展示界面，支持卡片/列表双布局
- **完整解读**：默认展示 AI 生成的完整文献分析内容

## 快速开始

### 1. 安装

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. 配置

创建 `.env` 文件：

```bash
ZOTERO_USER_ID=62236
ZOTERO_ROOT_DIR=/path/to/attachments
ZOTERO_DATA_DIR=/path/to/zotero/storage
DASHSCOPE_API_KEY=your_key
```

确保 Zotero 桌面客户端正在运行（编辑 → 首选项 → 高级 → 启用本地 HTTP 服务）。

### 3. 运行

**推荐：Batch 模式（省 50% 费用）**

```bash
# 同步文献
paper-digest sync --limit 10

# 提交批量分析任务
paper-digest submit-batch

# 等待完成（60秒轮询）
paper-digest check-batch --wait --interval 60

# 生成展示页面
paper-digest render
```

**快速：实时模式（立即返回）**

```bash
paper-digest sync --limit 5
paper-digest build --limit 5
paper-digest render
```

### 4. 查看结果

```bash
# 本地预览
cd public && python3 -m http.server 8080
# 浏览器访问 http://localhost:8080
```

或直接打开 `public/index.html`。

---

## 常用命令

### 文献管理

| 命令 | 说明 |
|------|------|
| `paper-digest stats` | 查看统计 |
| `paper-digest show 1` | 查看文献详情 |

### 筛选同步

```bash
# 交互式选择集合
paper-digest sync -i --limit 10

# 按集合名称同步
paper-digest sync -c "Seed Microbiome" --limit 10

# 按标签同步
paper-digest sync -t "#重要研究" --limit 10
```

### 批量处理

```bash
# 提交批量任务
paper-digest submit-batch --limit 20

# 检查并获取结果
paper-digest check-batch --wait --interval 60
```

### 生成展示页面

```bash
# 生成文献展示网站
paper-digest render

# 文件输出到 public/ 目录
```

---

## 界面功能

### 双布局模式

| 布局 | 特点 | 适用场景 |
|------|------|----------|
| **卡片布局** | 紧凑网格，一句话摘要，点击展开详情 | 快速浏览、筛选文献 |
| **列表布局** | 完整信息，默认显示全部解读内容 | 仔细阅读、逐篇研读 |

### 解读内容展示

AI 生成的完整文献分析包含：
- **一句话解读**：核心结论快速概览
- **研究背景**：领域问题和研究动机
- **研究结论**：主要发现和成果
- **核心创新点**： novelty 和技术突破
- **实验设计**：研究方法和数据
- **讨论**：意义、局限、未来方向
- **产业转化可行性**：应用前景评估

### 交互功能

- **实时搜索**：支持标题、作者、解读内容全文检索
- **多维度排序**：生成时间、发表时间、标题
- **分页控制**：10/20/50 篇每页
- **URL 状态同步**：所有操作自动同步到 URL，可分享特定视图
- **Zotero 跳转**：一键在 Zotero 中打开原文

---

## 文件结构

```
.
├── paper.db              # SQLite 数据库（文献元数据）
├── .cache/               # AI 分析结果缓存
│   └── *.json           # 每篇文献的完整解读
└── public/               # 生成的展示页面
    ├── index.html       # 单页面应用
    └── papers.json      # 文献数据（含完整解读）
```

---

## 技术架构

```
Zotero → PDF → Qwen-long → SQLite → public/
                    ↓
                 .cache/   (AI 解读缓存)
```

- **Zotero**：本地 HTTP API 获取文献元数据
- **Qwen-long**：1000万 token 长文本模型，解析 PDF 全文
- **Batch API**：异步处理，费用减半，24h 内完成
- **缓存机制**：hash(PDF内容 + prompt) 作为 key
- **前端**：原生 JavaScript，无框架依赖，单 HTML 文件

---

## 自定义提示词

编辑 `prompts/default.txt` 可自定义 AI 分析的内容结构。修改后自动重新分析（缓存失效）。

---

## 文档

- [Qwen-long 长文本解析](docs/qwen/qwen-long.md)
- [Qwen Batch 批处理](docs/qwen/qwen-batch-mode.md)
- [pyzotero 使用教程](docs/pyzotero/pyzotero-tutorial.md)
