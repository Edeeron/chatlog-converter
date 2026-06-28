# ChatLog Converter - 中文版

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

**按 Agent 名称分组的 AI 聊天日志处理工具 · 本地处理 · 隐私安全**

[🚀 快速开始](#-快速开始) · [📖 使用教程](#-使用教程) · [💡 示例](#-示例) · [🤝 贡献](#-贡献)

</div>

---

## 🌟 项目简介

ChatLog Converter 是一款专为处理 AI 聊天数据设计的轻量级工具。它可以自动检测对话结构，按 Agent 名称分组消息，并将其转换为适合分析、备份或模型微调的各种格式。

### ✨ 核心特性

- 🔒 **隐私优先**：所有处理在本地完成，数据永远不会离开你的设备
- 🎯 **智能检测**：自动识别 Agent 名称、角色、内容和时间戳字段
- 📊 **多种模式**：提取特定 Agent、分类所有 Agent 或转换为 JSON 格式
- 🎨 **现代界面**：简洁的 Web 界面，深色主题，直观的工作流程
- 💻 **命令行支持**：提供命令行接口，便于自动化和批量处理
- 🌍 **双语支持**：完整支持中文和英文界面
- 📦 **零配置**：开箱即用，自动检测分隔符
- ⚡ **批量处理**：一次处理多个文件，自动分块处理大文件

### 🎯 适用场景

- **AI 开发者**：整理多 Agent 对话数据用于模型微调
- **数据分析师**：清洗和分类聊天日志进行分析
- **普通用户**：备份和管理个人 AI 对话记录
- **研究人员**：高效处理大规模对话数据集

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Edeeron/chatlog-converter.git
cd chatlog-converter

# 安装依赖
pip install -r requirements.txt
```

**注意**：在 Linux/macOS 上，可能需要使用 `pip3` 和 `python3` 而不是 `pip` 和 `python`。

### 启动 Web 界面（推荐）

```bash
# Windows
python main.py

# Linux/macOS
python3 main.py
```

然后在浏览器中打开：**http://127.0.0.1:8010**

### 命令行模式

```bash
# 启动 CLI 模式
# Windows
python main.py --cli

# Linux/macOS
python3 main.py --cli

# 或直接使用 CLI
# Windows
python cli.py convert chat.csv --mode finetune

# Linux/macOS
python3 cli.py convert chat.csv --mode finetune
```

---

## 📖 使用教程

### 四种处理模式

| 模式 | 说明 | 输出格式 |
|------|------|----------|
| 📄 **提取指定 Agent** | 输入 Agent 名称，提取与该 Agent 的全部对话 | CSV |
| 📑 **全部 Agent 分类** | 按 Agent 名称分组，每个 Agent 保存一个文件 | 多个 CSV |
| 🔧 **JSON - 储存格式** | 包含 message_id、turn_id、token_count 等完整信息 | JSON（适合储存与检索） |
| 🔗 **JSON - 上下文格式** | 简洁的 role + content + 时间戳结构 | JSON（适合上下文接入与模型微调） |
| 🤖 **OpenAI 微调格式** | 纯消息格式的 JSONL，用于 OpenAI/Azure 微调 | JSONL |

### Web 界面工作流程

1. **选择模式**：选择你需要的处理模式
2. **上传文件**：拖拽或点击上传 CSV/TXT 文件
3. **确认映射**：验证自动检测的字段映射是否正确
4. **处理并保存**：点击处理按钮并下载结果

### CLI 使用示例

```bash
# 自动检测并转换为 JSON
python cli.py convert chat.csv --mode finetune

# 提取特定 Agent
python cli.py extract chat.csv --agent "GPT-4" --output ./extracted

# 分类所有 Agent
python cli.py classify chat.csv --output ./classified

# 预览文件结构（前 10 行）
python cli.py preview chat.csv --rows 10

# 设置语言为英文
python cli.py lang en

# 强制启用流式模式处理大文件
python cli.py convert large_file.csv --mode context --streaming
```

---

## 💡 使用示例

### 示例 1：提取特定 Agent 的对话

假设你有一个包含多个 AI 助手的聊天记录，只想提取"客服助手"的对话：

1. 选择"📄 提取指定 Agent"模式
2. 上传 `聊天记录.csv`
3. 在"目标 Agent"输入框中输入：`客服助手`
4. 点击"预览匹配"确认结果
5. 点击"开始处理"并保存

输出文件：`聊天记录_提取_客服助手.csv`

### 示例 2：转换为 JSON 储存格式

将聊天记录转换为包含完整元数据的 JSON 格式：

1. 选择"🔧 JSON - 储存格式"模式
2. 上传文件并确认字段映射
3. 勾选"反转消息序列"（如果需要从旧到新排序）
4. 保存为 JSON 文件

输出示例：
```json
[
  {
    "conversation_id": "conv_客服助手_001",
    "user_id": "",
    "agent_name": "客服助手",
    "created_at": "2024-05-09 11:20:45",
    "messages": [
      {
        "message_id": "msg_001",
        "turn_id": "turn_001",
        "role": "user",
        "content": "你好，我想咨询一下产品问题",
        "timestamp": "2024-05-09 11:20:45",
        "token_count": 15
      },
      {
        "message_id": "msg_002",
        "turn_id": "turn_001",
        "role": "assistant",
        "content": "您好！很高兴为您服务，请问有什么问题？",
        "timestamp": "2024-05-09 11:20:46",
        "token_count": 18
      }
    ]
  }
]
```

### 示例 3：分类所有 Agent

将一个混合了多个 Agent 的聊天记录按 Agent 分开：

1. 选择"📑 全部 Agent 分类"模式
2. 上传 `混合对话.csv`
3. 确认 Agent 列检测正确
4. 点击"开始处理"

输出文件：
- `混合对话_GPT4.csv`
- `混合对话_Claude.csv`
- `混合对话_客服助手.csv`

### 示例 4：转换为 OpenAI 微调格式

将聊天记录直接转换为 JSONL 格式，用于 OpenAI/Azure 微调：

1. 选择“🤖 **OpenAI 微调格式**”模式
2. 上传你的 CSV 文件
3. 确认字段映射（Agent、Role、Content 列）
4. 点击“开始处理”

输出示例（`chat_history_openai.jsonl`）：
```jsonl
{"messages": [{"role": "user", "content": "你好，最近怎么样？"}, {"role": "assistant", "content": "我很好！今天有什么可以帮你的吗？"}]}
{"messages": [{"role": "user", "content": "天气如何？"}, {"role": "assistant", "content": "今天阳光明媚，温度适宜。"}]}
```

此格式**完全兼容** OpenAI 的微调 API - 无需额外转换！

---

## 🛠️ 技术细节

### 支持的格式

- **输入**：CSV（逗号/制表符分隔）、TXT（表格格式）
- **输出**：CSV、JSON（储存/上下文格式）
- **编码**：UTF-8-SIG（兼容 Excel）

### 自动检测算法

工具使用智能评分系统，结合以下策略：
1. **关键词匹配**：识别多语言（中文和英文）的常见列名
2. **启发式分析**：评估数据特征，如值多样性、文本长度和格式模式
3. **样本验证**：通过分析前 50 行确认检测准确性

### Token 计数

使用 OpenAI 官方的 `tiktoken` 库（cl100k_base 编码）进行准确的 GPT-4 Token 计数，确保与 OpenAI API 保持一致。如果库不可用，则回退到字符计数。

### 性能优化

- **自动检测分隔符**：智能识别 CSV/TXT 多种格式（逗号/制表符）
- **流式处理模式**：大于 100MB 的文件自动启用，内存占用恒定约 50-100MB
- **批量处理**：一次处理多个文件，自动复用首次检测结果，提升效率
- **适用范围**：流式模式目前仅适用于 JSON 转换模式（`finetune`、`context` 和 `openai`）

---

## 📁 项目结构

```
chatlog-converter/
├── main.py              # 统一入口点（Web/CLI 选择器）
├── api.py               # FastAPI 后端服务
├── cli.py               # 命令行界面
├── core.py              # 核心处理逻辑
├── static/
│   └── index.html       # Web 前端（单页应用）
├── locales/
│   ├── zh.json          # 中文翻译
│   └── en.json          # 英文翻译
├── requirements.txt     # Python 依赖
├── LICENSE              # MIT 许可证
└── README.md            # 英文文档
```

---

## ❓ 常见问题

### Q: 我的 CSV 文件无法识别怎么办？

A: 确保文件使用 UTF-8 编码、第一行是列标题、数据格式一致。可使用 `python cli.py preview your_file.csv` 检查结构。

### Q: 如何修改自动检测的结果？

A: 在 Web 界面上传文件后，在"字段映射"部分手动调整即可。

### Q: 支持哪些列名自动检测？

A: 支持中英文：
- Agent：`agent名称`、`agent_name`、`智能体`、`bot`
- Role：`role`、`角色`、`speaker`、`说话人`
- Content：`content`、`内容`、`message`、`消息`
- Time：`time`、`时间`、`timestamp`、`日期`

---

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 基于 [FastAPI](https://fastapi.tiangolo.com/) 和 [Uvicorn](https://www.uvicorn.org/) 构建
- Token 计数由 [tiktoken](https://github.com/openai/tiktoken) 提供支持
- 灵感来源于对隐私安全的 AI 聊天日志管理需求

---

<div align="center">

**由 [Edeeron](https://github.com/Edeeron) 用 ❤️ 制作**

⭐ 如果觉得有帮助，请给个 Star！

</div>
