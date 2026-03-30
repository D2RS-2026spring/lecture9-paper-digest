# 📚 Paper Digest — 基于 Zotero + Qwen 的科研文献知识编译系统

## ✨ 项目简介

**Paper Digest** 是一个面向科研工作流的本地知识系统，用于批量解析 Zotero 文献库中的 PDF 原文，通过大语言模型（Qwen）进行结构化解读，并自动生成 Quarto Book，帮助用户快速掌握一批文献的核心内容。

本项目强调：

* 📖 **结构化知识提取**（而非简单摘要）
* ⚡ **增量更新 + 缓存机制**
* 🧠 **长期可演化的个人知识库**
* 📚 **科研友好的 Quarto 输出**

---

## 环境管理

* 使用 `uv venv` 创建虚拟环境，使用 `uv pip install` 安装包，使用 `uv pip freeze` 保存 Python 环境。
* 使用 `.env` 文件保存 API KEY。

---

## 🧠 系统架构

```text
Zotero API (pyzotero)
        ↓
文献元数据 + PDF
        ↓
LLM解析（Qwen-long）
        ↓
结构化 JSON（缓存）
        ↓
SQLite（状态管理）
        ↓
Markdown / Quarto
        ↓
📘 Book 输出
```

---

## 🚀 核心特性

### 1️⃣ Zotero 原生集成

* 通过 pyzotero 获取本地文献库的下列信息（通过 `http://127.0.0.1:23119/api` 提供）：

  * 文献元数据（标题、作者、年份）
  * collections（目录结构）
  * PDF 附件路径
* 支持按 collection / tag 选择文献

文档：[pyzotero](./docs/pyzotero/pyzotero-tutorial.md)

---

### 2️⃣ 智能缓存（核心能力）

系统会自动判断是否需要重新解析文献：

* ✅ PDF 未变化
* ✅ Prompt 未变化
* ✅ 模型未变化

👉 则直接读取缓存，避免重复调用 LLM

缓存 key 计算方式：

```text
hash(PDF内容 + prompt + model)
```

---

### 3️⃣ SQLite 状态管理

使用 SQLite 作为 manifest 管理系统：

* 文献信息
* 分析状态（pending / done / error）
* cache_key
* prompt版本
* 模型版本

支持：

* 增量更新
* 失败重试
* 查询未处理文献

---

### 4️⃣ LLM 驱动的结构化解析

使用 Qwen-long 对 PDF 进行分析，输出标准化 JSON：

```json
{
  "title": "",
  "research_question": "",
  "methodology": "",
  "key_findings": [],
  "limitations": [],
  "novelty": "",
  "confidence": 0.0
}
```

Qwen 模型使用文档：

- [Qwen-long 模型解读长文](docs/qwen/qwen-long.md)
- [Qwen-batch 异步批量化处理](docs/qwen/qwen-batch-mode.md)
- [Qwen 结构化输出功能](docs/qwen/qwen-structured-output.md)
- [Qwen 深度研究功能](docs/qwen/qwen-deep-research.md)

---

### 5️⃣ Quarto Book 自动生成

自动生成：

* 每篇论文一个 `.qmd`
* 按 Zotero collection 构建目录
* 支持 citation

最终输出：

```bash
quarto render
```

生成完整文献解读书籍 📘

请通过 `/skills` 访问 `quarto-authoring` 技能查看文档。

---

## 📦 项目结构

```text
paper-digest/
├── paper_digest/          # 核心逻辑
│   ├── zotero.py          # Zotero API
│   ├── processor.py       # 主处理流程
│   ├── llm.py             # Qwen 调用
│   ├── cache.py           # 缓存管理
│   ├── db.py              # SQLite
│   └── render.py          # Quarto生成
│
├── prompts/
│   └── v1.txt             # Prompt版本
│
├── quarto/                # Quarto工程
│   ├── index.qmd
│   └── papers/
│
├── .cache/                # 缓存数据
├── paper.db               # SQLite数据库
├── pyproject.toml
└── cli.py                 # CLI入口
```

---

## ⚙️ 安装

```bash
# 克隆仓库
git clone <repo>
cd paper-digest

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -e .

# 或使用 pip
pip install -e .
```

安装完成后，`paper-digest` 命令即可使用。

---

## 🔧 配置

创建 `.env` 文件：

```bash
# Zotero 配置
ZOTERO_USER_ID=your_user_id
ZOTERO_ROOT_DIR=/path/to/your/attachments
ZOTERO_DATA_DIR=/path/to/zotero/storage

# DashScope API Key
DASHSCOPE_API_KEY=your_api_key
```

### 1. Zotero 配置

1. 确保 Zotero 桌面客户端正在运行
2. 在 Zotero 中启用本地 HTTP 服务：编辑 → 首选项 → 高级 → 本地 HTTP 服务
3. 获取 User ID：登录 zotero.org，查看 Library URL 中的数字

### 2. Prompt 配置

编辑 `prompts/v1.txt` 自定义分析 prompt。

---

## 🧪 使用方式

### 完整工作流

```bash
# 1. 从 Zotero 同步文献
paper-digest sync --limit 10

# 2. 解析文献（调用 Qwen-long）
paper-digest build --limit 5

# 3. 生成 Quarto Book
paper-digest render

# 4. 渲染成 HTML/PDF
cd quarto && quarto render
```

### 查看统计

```bash
paper-digest stats
```

### 列出 Zotero 集合

```bash
paper-digest collections
```

### 查看单篇文献详情

```bash
paper-digest show 1
```

### 强制重新解析

```bash
paper-digest rebuild
```

### 使用自定义 Prompt

```bash
paper-digest build --prompt prompts/v1.txt
```

---

## 🔄 工作流程

```text
sync → build → render
```

---

## 📈 设计理念

本项目并非简单“文献摘要工具”，而是**一个将论文编译为结构化知识的系统（Knowledge Compiler）**。

核心思想：

* 文献 = 输入数据
* LLM = 编译器
* JSON = 中间表示（IR）
* Quarto = 输出层

---

## 🛠️ 未来规划

* [ ] 异步批处理
* [ ] 多文献自动综述生成
* [ ] 文献知识图谱
* [ ] RAG 检索接口
* [ ] Web UI
* [ ] 并发任务调度

---

## ⚠️ 注意事项

* 长文解析成本较高，建议合理控制批量规模
* PDF质量会影响解析结果
* 建议使用高质量 prompt 并进行版本管理

---

## 📄 License

MIT License

---

## 🙌 致谢

* Zotero 生态（文献管理）
* Quarto（科研写作）
* Qwen（大模型能力）

---

## 💡 一句话总结

> 用 AI 把你的 Zotero 文献库，编译成一本可以阅读的“知识书”。
