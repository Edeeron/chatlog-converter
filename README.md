# ChatLog Converter

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

**A powerful tool for processing AI chat logs - Group by Agent · Local Processing · Privacy Safe**

[🚀 Quick Start](#-quick-start) · [📖 Usage](#-usage) · [💡 Examples](#-examples) · [🤝 Contributing](#-contributing)

</div>

---

## 🌟 Overview

ChatLog Converter is a lightweight, privacy-focused tool designed to process and transform AI chat conversation logs. It automatically detects conversation structure, groups messages by agent name, and converts them into various formats suitable for analysis, backup, or model fine-tuning.

### ✨ Key Features

- 🔒 **Privacy First**: All processing happens locally - your data never leaves your machine
- 🎯 **Smart Detection**: Automatically identifies agent names, roles, content, and timestamps
- 📊 **Multiple Modes**: Extract specific agents, classify all agents, or convert to JSON formats
- 🎨 **Modern UI**: Clean web interface with dark theme and intuitive workflow
- 💻 **CLI Support**: Command-line interface for automation and batch processing
- 🌍 **Bilingual**: Full support for Chinese and English interfaces
- 📦 **Zero Config**: Works out of the box with automatic delimiter detection
- ⚡ **Batch Processing**: Process multiple files at once with automatic chunked processing for large files
- 🤖 **OpenAI Ready**: Direct conversion to JSONL format for OpenAI/Azure fine-tuning

### 🎯 Use Cases

- **AI Developers**: Organize multi-agent conversation data for model fine-tuning
- **Data Analysts**: Clean and categorize chat logs for analysis
- **Regular Users**: Backup and manage personal AI conversation records
- **Researchers**: Process large-scale dialogue datasets efficiently

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Edeeron/chatlog-converter.git
cd chatlog-converter

# Install dependencies
pip install -r requirements.txt
```

**Note**: On Linux/macOS, you may need to use `pip3` and `python3` instead of `pip` and `python`.

### Launch Web Interface (Recommended)

```bash
# Windows
python main.py

# Linux/macOS
python3 main.py
```

Then open your browser to: **http://127.0.0.1:8010**

### Command-Line Mode

```bash
# Launch CLI mode
# Windows
python main.py --cli

# Linux/macOS
python3 main.py --cli

# Or use CLI directly
# Windows
python cli.py convert chat.csv --mode finetune

# Linux/macOS
python3 cli.py convert chat.csv --mode finetune
```

---

## 📖 Usage

### Five Processing Modes

| Mode | Description | Output |
|------|-------------|--------|
| 📄 **Extract Agent** | Extract all conversations for a specific agent | CSV |
| 📑 **Classify Agents** | Split mixed conversations by agent into separate files | Multiple CSVs |
| 🔧 **JSON - Storage Format** | Convert with full metadata (message_id, turn_id, token_count) | JSON |
| 🔗 **JSON - Context Format** | Simplified format (role + content + timestamp) | JSON |
| 🤖 **OpenAI Fine-tuning** | Pure messages format in JSONL for OpenAI/Azure fine-tuning | JSONL |

### Web Interface Workflow

1. **Select Mode**: Choose your processing mode
2. **Upload File**: Drag & drop your CSV/TXT file
3. **Confirm Mapping**: Verify auto-detected column mappings
4. **Process & Save**: Click to process and download results

### CLI Examples

```bash
# Auto-detect and convert to JSON
python cli.py convert chat.csv --mode finetune

# Extract specific agent
python cli.py extract chat.csv --agent "GPT-4" --output ./extracted

# Classify all agents
python cli.py classify chat.csv --output ./classified

# Preview file structure (first 10 rows)
python cli.py preview chat.csv --rows 10

# Set language to English
python cli.py lang en

# Force streaming mode for large files
python cli.py convert large_file.csv --mode context --streaming
```

---

## 💡 Examples

### Example 1: Extract Specific Agent's Conversations

Suppose you have a chat log containing multiple AI assistants and only want to extract conversations with "Customer Service Bot":

1. Select "📄 **Extract Agent**" mode
2. Upload `chat_history.csv`
3. Enter in the "Target Agent" input box: `Customer Service Bot`
4. Click "Preview Match" to confirm results
5. Click "Start Processing" and save

Output file: `chat_history_extracted_Customer_Service_Bot.csv`

### Example 2: Convert to JSON Storage Format

Convert chat logs to JSON format with complete metadata:

1. Select "🔧 **JSON - Storage Format**" mode
2. Upload file and confirm field mappings
3. Check "Reverse message sequence" (if you need chronological order from old to new)
4. Save as JSON file

Output example:
```json
[
  {
    "conversation_id": "conv_Customer_Service_Bot_001",
    "user_id": "",
    "agent_name": "Customer Service Bot",
    "created_at": "2024-05-09 11:20:45",
    "messages": [
      {
        "message_id": "msg_001",
        "turn_id": "turn_001",
        "role": "user",
        "content": "Hello, I'd like to inquire about a product issue",
        "timestamp": "2024-05-09 11:20:45",
        "token_count": 15
      },
      {
        "message_id": "msg_002",
        "turn_id": "turn_001",
        "role": "assistant",
        "content": "Hello! Happy to assist you, what questions do you have?",
        "timestamp": "2024-05-09 11:20:46",
        "token_count": 18
      }
    ]
  }
]
```

### Example 3: Classify All Agents

Split a mixed chat log with multiple agents by agent name:

1. Select "📑 **Classify Agents**" mode
2. Upload `mixed_conversation.csv`
3. Confirm Agent column detection is correct
4. Click "Start Processing"

Output files:
- `mixed_conversation_GPT4.csv`
- `mixed_conversation_Claude.csv`
- `mixed_conversation_Customer_Service_Bot.csv`

### Example 4: Convert to OpenAI Fine-tuning Format

Convert chat logs directly to JSONL format for OpenAI/Azure fine-tuning:

1. Select "🤖 **OpenAI Fine-tuning**" mode
2. Upload your CSV file
3. Confirm field mappings (Agent, Role, Content columns)
4. Click "Start Processing"

Output example (`chat_history_openai.jsonl`):
```jsonl
{"messages": [{"role": "user", "content": "Hello, how are you?"}, {"role": "assistant", "content": "I'm doing well! How can I help you today?"}]}
{"messages": [{"role": "user", "content": "What's the weather like?"}, {"role": "assistant", "content": "It's sunny and warm today."}]}
```

This format is **directly compatible** with OpenAI's fine-tuning API - no conversion needed!

---

## 🛠️ Technical Details

### Supported Formats

- **Input**: CSV (comma/tab delimited), TXT (table format)
- **Output**: CSV, JSON (storage/context format), JSONL (OpenAI fine-tuning)
- **Encoding**: UTF-8-SIG (Excel compatible)

### Auto-Detection Algorithm

The tool uses an intelligent scoring system that combines:
1. **Keyword matching**: Recognizes common column names in multiple languages (Chinese & English)
2. **Heuristic analysis**: Evaluates data characteristics such as value diversity, text length, and format patterns
3. **Sample validation**: Confirms detection accuracy by analyzing the first 50 rows

### Token Counting

Uses OpenAI's official `tiktoken` library (cl100k_base encoding) for accurate GPT-4 token counting, ensuring consistency with OpenAI API. Falls back to character count if the library is unavailable.

### Performance Optimization

- **Auto delimiter detection**: Intelligently recognizes multiple CSV/TXT formats (comma/tab)
- **Streaming mode**: Automatically enabled for files >100MB, constant memory usage ~50-100MB
- **Batch processing**: Process multiple files at once, reusing first detection results for efficiency
- **Scope**: Streaming mode currently applies only to JSON conversion modes (`finetune`, `context`, and `openai`)

---

## ❓ FAQ

### Q: What if my CSV file is not recognized?

A: Ensure the file uses UTF-8 encoding, has column headers in the first row, and consistent data format. Use `python cli.py preview your_file.csv` to check structure.

### Q: How do I modify auto-detected results?

A: In the web interface, manually adjust field mappings in the "Field Mapping" section after uploading.

### Q: Which column names are supported for auto-detection?

A: Supports Chinese and English:
- Agent: `agent名称`, `agent_name`, `智能体`, `bot`
- Role: `role`, `角色`, `speaker`, `说话人`
- Content: `content`, `内容`, `message`, `消息`
- Time: `time`, `时间`, `timestamp`, `日期`

---

## 📁 Project Structure

```
chatlog-converter/
├── main.py              # Unified entry point (Web/CLI selector)
├── api.py               # FastAPI backend service
├── cli.py               # Command-line interface
├── core.py              # Core processing logic
├── static/
│   └── index.html       # Web frontend (single-page app)
├── locales/
│   ├── zh.json          # Chinese translations
│   └── en.json          # English translations
├── requirements.txt     # Python dependencies
├── LICENSE              # MIT License
├── README.md            # This file (English documentation)
└── README-zh.md         # Chinese documentation
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Uvicorn](https://www.uvicorn.org/)
- Token counting powered by [tiktoken](https://github.com/openai/tiktoken)
- Inspired by the need for privacy-safe AI chat log management

---

<div align="center">

**Made with ❤️ by [Edeeron](https://github.com/Edeeron)**

⭐ Star this repo if you find it helpful!

</div>
