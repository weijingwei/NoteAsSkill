# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NoteAsSkill（笔技）** — A desktop app that converts notes into Claude Code Skills. Each note is a directory containing
`note.md` + `SKILL.md`, organized in a three-column layout (sidebar, editor, AI chat).

**Tech stack**: PySide6 + QWebEngine + EasyMDE + OpenAI/Anthropic/Ollama SDKs

## Essential Commands

### Setup & Run

```bash
conda activate noteasskill    # Python 3.12 conda environment
python main.py                # Launch the app
```

### Run Tests

项目使用 **pytest** 作为测试框架，采用分层测试结构。

```bash
# 运行全部测试（294+ 用例）
python -m pytest tests/ -v

# 运行指定模块
python -m pytest tests/test_core/ -v        # 核心业务逻辑
python -m pytest tests/test_ai/ -v          # AI 客户端
python -m pytest tests/test_mcp/ -v         # MCP 模块
python -m pytest tests/test_widgets/ -v     # GUI 组件（pytest-qt）
python -m pytest tests/test_integration/ -v # 集成测试

# 运行指定文件
python -m pytest tests/test_core/test_singleton.py -v

# 运行单个测试
python -m pytest tests/test_core/test_singleton.py::TestSingletonMeta::test_same_instance -v

# 带覆盖率报告
python -m pytest tests/ -v --cov=app --cov-report=html

# 只运行非 GUI 测试（快速）
python -m pytest tests/ -v -m "not slow"
```

**测试分层**:

| 层级          | 目录                         | 内容                                                                                                                              |
|-------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| Unit        | `tests/test_core/`         | singleton, config, event_bus, commands, note_manager, note_naming, skill_generator, attachment_handler, folder_skill_strategies |
| Unit        | `tests/test_ai/`           | factory, client_base, openai, anthropic, ollama                                                                                 |
| Unit        | `tests/test_mcp/`          | mcp_client, mcp_manager                                                                                                         |
| Component   | `tests/test_widgets/`      | notification_bar, sidebar, editor, chat_panel, settings_dialog                                                                  |
| Integration | `tests/test_integration/`  | full_note_flow, ai_integration                                                                                                  |
| E2E         | `tests/test_automation.py` | GUI 自动化（pyautogui，需要桌面环境）                                                                                                       |

**全局 Fixtures** (`tests/conftest.py`):

- `clean_singletons` — autouse，自动清理单例状态
- `temp_notebook` — 隔离的 notebook 目录
- `config_with_temp` — 指向临时目录的 Config
- `ai_client_mock` — mock AI 客户端
- `mock_ai_chat_response` — 固定 AI 响应

### Build Executable (Windows)

```bash
build.bat
# or: pyinstaller NoteAsSkill.spec --noconfirm
```

## Key Architecture

### Note Storage Format

Each note is a directory: `notebook/skills/{note-name}/` containing:

- `note.md` — Markdown content
- `SKILL.md` — AI-generated skill description (YAML frontmatter + body)
- `attachments/` — Auto-archived images/files

Index file `notebook/.index.json` tracks notes, folders, and tags.

### Module Structure

```
app/
├── ai/              — AI client layer (Abstract Factory pattern)
│   ├── client.py    — Abstract AIClient base (chat/chat_stream)
│   ├── factory.py   — AIClientFactory with dynamic provider registration
│   ├── openai_client.py / anthropic_client.py / ollama_client.py
├── core/            — Business logic (Singleton pattern throughout)
│   ├── config.py    — Config singleton (reads config.yaml + user config)
│   ├── note_manager.py — Note CRUD singleton
│   ├── event_bus.py — Qt Signal-based pub/sub for cross-thread events
│   ├── commands.py  — Command pattern (deferred folder skill updates)
│   ├── singleton.py — SingletonMeta metaclass (with clear_instance for testing)
│   ├── git_sync.py  — Git sync on QThread
│   ├── folder_skill_strategies.py — Strategy pattern (simple/ai/hybrid)
│   └── folder_skill_updater.py — Debounced folder skill generation
├── mcp/             — MCP server management (subprocess + JSON-RPC)
└── widgets/         — PySide6 GUI components
    ├── main_window.py    — Three-column layout, app orchestration
    ├── sidebar.py        — Note list, folder tree, tags
    ├── editor.py         — Markdown editor (QWebEngine + EasyMDE)
    ├── chat_panel.py     — AI chat panel (3 modes: skill gen, Q&A, general)
    └── settings_dialog.py — Preferences dialog
```

### Design Patterns

| Pattern          | Where                                                                 |
|------------------|-----------------------------------------------------------------------|
| Singleton        | `Config`, `NoteManager`, `EventBus`, `MCPManager` via `SingletonMeta` |
| Abstract Factory | `AIClientFactory` — dynamic provider registration                     |
| Strategy         | `FolderSkillStrategyFactory` — simple/ai/hybrid strategies            |
| Observer         | `EventBus` — Qt Signal pub/sub                                        |
| Command          | `CommandQueue` with `UpdateFolderSkillCommand`                        |
| Template Method  | `AIClient` abstract base with `chat()`/`chat_stream()`                |

### Data Flow

1. User edits note → auto-save triggers (30s interval from `config.yaml`)
2. Save event fires `EventBus` signal → async SKILL.md generation on background thread
3. Folder SKILL updates debounced via `FolderSkillUpdater` (30s delay)
4. Git sync runs on separate QThread

### Configuration

- `config.yaml` — app-level defaults (version, colors, timeouts, API endpoints)
- `notebook/.config.yaml` — user-specific settings (API keys, model selection)
- Current version tracked in `config.yaml` (bump last digit on each code change)

## Important Conventions

- **Version**: Bump the last digit in `config.yaml` version after each code change
- **Singletons**: Use `clear_instance()` for testing, never re-instantiate directly
- **Events**: Use `EventBus` for cross-module communication, not direct references
- **Threading**: Long-running operations (AI, Git, MCP) must use QThread/background workers
- **Note naming**: Follow conventions in `core/note_naming.py`
- **TDD**: 新功能开发遵循 Red → Green → Refactor，详见 `.github/TDD.md`
