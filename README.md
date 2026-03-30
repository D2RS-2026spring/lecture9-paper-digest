# Paper Digest

将 Zotero 文献库批量编译成结构化知识书。

## 功能说明

- **Zotero 集成**：自动同步本地文献库，提取 PDF 和元数据
- **AI 解析**：使用 Qwen-long 提取研究问题、方法、主要发现
- **Batch API**：批量处理节省 50% 费用
- **智能缓存**：相同 PDF + Prompt 不重复调用
- **Quarto 输出**：生成可阅读的文献解读书籍
- **灵活筛选**：支持按集合、标签筛选文献

## 实操步骤

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

# 提交批量任务
paper-digest submit-batch

# 等待完成（60秒轮询）
paper-digest check-batch --wait --interval 60

# 生成书籍
paper-digest render
cd quarto && quarto render
```

**快速：实时模式（立即返回）**

```bash
paper-digest sync --limit 5
paper-digest build --limit 5
paper-digest render
```

## 常用命令

### 文献管理

| 命令 | 说明 |
|------|------|
| `paper-digest stats` | 查看统计 |
| `paper-digest show 1` | 查看文献详情 |

### 按集合/标签筛选

```bash
# 列出所有集合（目录）
paper-digest collections

# 按集合名称同步（支持模糊匹配）
paper-digest sync -c "Seed Microbiome" --limit 10

# 按集合 key 同步（8位字母数字）
paper-digest sync -c NVIWASQD --limit 10

# 列出所有标签
paper-digest tags

# 按标签同步
paper-digest sync -t "#重要研究" --limit 10

# 组合筛选：集合 + 标签
paper-digest sync -c "SynComs" -t "#VIP" --limit 5
```

### Batch 批量处理

```bash
# 提交批量任务（节省 50% 费用）
paper-digest submit-batch --limit 20

# 检查任务状态
paper-digest check-batch

# 等待完成（自动轮询）
paper-digest check-batch --wait --interval 60
```

## 技术内幕

```
Zotero → PDF → Qwen-long → SQLite → Quarto
```

- **Zotero**：通过本地 HTTP API (pyzotero) 获取文献
- **Qwen-long**：支持 10M 长文本的 PDF 解析模型
- **Batch API**：异步批处理，费用 50%，24h 内完成
- **缓存**：hash(PDF内容 + prompt + model) 作为 key，存储在 `.cache/`
- **存储**：SQLite 记录状态和 cache_key，实际结果存储在 `.cache/` 文件

## 自定义提示词

编辑 `prompts/default.txt` 可以自定义 AI 分析的内容结构。修改提示词后会自动重新分析（缓存失效）。

## 文档

- [Qwen-long 长文本解析](docs/qwen/qwen-long.md)
- [Qwen Batch 批处理](docs/qwen/qwen-batch-mode.md)
- [pyzotero 使用教程](docs/pyzotero/pyzotero-tutorial.md)
