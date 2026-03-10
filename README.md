# NoteAsSkil - 笔技

一个将笔记自动转换为 Claude Code Skill 的桌面应用。

## 核心特性

- **三列布局**：左侧笔记列表、中间 Markdown 编辑器、右侧 AI 对话区
- **AI 辅助**：自动生成 SKILL.md，支持笔记问答和通用对话
- **多 API 支持**：OpenAI / Anthropic / Ollama 三种接口可配置
- **文件夹 + 标签**：灵活组织笔记
- **附件管理**：自动归档、粘贴图片、拖拽上传
- **跨平台**：Windows / Linux / macOS 全平台支持

## 安装

### 1. 创建 conda 环境

```bash
conda create -n noteasskill python=3.12 -y
conda activate noteasskill
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

```bash
python main.py
```

## 配置

首次运行后，在应用中打开 **设置 > 偏好设置** 配置 AI 接口：

### OpenAI

- Base URL: `https://api.openai.com/v1`
- API Key: 你的 OpenAI API Key
- Model: `gpt-4` 或 `gpt-3.5-turbo`

### Anthropic

- Base URL: `https://api.anthropic.com`
- API Key: 你的 Anthropic API Key
- Model: `claude-3-opus-20240229` 或 `claude-3-sonnet-20240229`

### Ollama (本地)

- Base URL: `http://localhost:11434`
- Model: `llama2` 或其他已安装的模型

## 目录结构

```
noteasskill/
├── main.py                 # 应用入口
├── requirements.txt        # 依赖清单
├── app/
│   ├── widgets/           # GUI 组件
│   │   ├── main_window.py # 主窗口
│   │   ├── sidebar.py     # 左侧边栏
│   │   ├── editor.py      # Markdown 编辑器
│   │   ├── chat_panel.py  # AI 对话区
│   │   └── settings_dialog.py # 设置对话框
│   ├── core/              # 核心模块
│   │   ├── config.py      # 配置管理
│   │   ├── note_manager.py # 笔记管理
│   │   ├── skill_generator.py # SKILL 生成
│   │   └── attachment_handler.py # 附件处理
│   └── ai/                # AI 客户端
│       ├── client.py      # 抽象基类
│       ├── openai_client.py
│       ├── anthropic_client.py
│       └── ollama_client.py
└── notebook/
    ├── .config.yaml       # 应用配置
    ├── skills/            # 笔记存储
    └── templates/         # 笔记模板
```

## 使用说明

### 创建笔记

1. 点击左下角「新建笔记」按钮
2. 输入笔记标题
3. 在编辑器中编写 Markdown 内容

### 编辑笔记

- 编辑器支持实时预览
- 支持粘贴图片（自动归档到附件目录）
- 支持拖拽文件上传

### AI 对话

右侧面板提供三种模式：

1. **生成 SKILL**：根据笔记内容自动生成 SKILL.md
2. **笔记问答**：基于当前笔记内容提问
3. **通用对话**：自由对话

### 标签管理

- 在笔记内容中添加 `#标签名` 即可自动识别
- 点击左侧标签列表可筛选笔记

## 开发

### 技术栈

- **GUI**: PySide6 (Qt 官方 Python 绑定)
- **编辑器**: QWebEngine + EasyMDE
- **AI**: OpenAI / Anthropic SDK

### 运行测试

```bash
python -m pytest tests/
```

## 许可证

MIT License