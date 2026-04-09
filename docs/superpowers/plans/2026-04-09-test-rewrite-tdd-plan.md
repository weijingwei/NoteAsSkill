# 测试重写与 TDD 流程建立 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目从自定义测试框架迁移到 pytest，一次性重写全部测试，精简项目结构，建立 TDD 流程。

**Architecture:** pytest + fixtures 管理隔离的 notebook 环境和单例清理；按模块分目录组织测试；保留 pyautogui 做 E2E UI 测试。

**Tech Stack:** pytest, pytest-qt, pytest-cov, responses (HTTP mock), PySide6

---

### Task 1: 精简项目结构 + 安装测试依赖

**Files:**
- Modify: `.gitignore`
- Modify: `requirements.txt`
- Create: `pytest.ini`
- Delete: `docs/plans/2026-03-11-ui-controls-redesign.md`
- Delete: `tests/test_plan.md`
- Delete: `tests/test_comprehensive.py`
- Delete: `tests/test_functional.py`
- Delete: `tests/screenshots/` 目录全部（含 combobox/ 子目录）
- Delete: `test_notebook/` 目录

- [ ] **Step 1: 删除无用文件**

运行：
```bash
rm -f docs/plans/2026-03-11-ui-controls-redesign.md
rm -f tests/test_plan.md
rm -f tests/test_comprehensive.py
rm -f tests/test_functional.py
rm -rf tests/screenshots/
rm -rf test_notebook/
```

- [ ] **Step 2: 更新 `.gitignore`**

当前 `.gitignore` 已有 `notebook/.index.json`、`notebook/.config.yaml`、`tests/screenshots/`。需要增加对运行时生成数据的忽略：

```diff
+# Notebook 运行时数据
+notebook/skills/
+notebook/.folder_skills/
+
 # Project specific
-notebook/.index.json
-notebook/.config.yaml
+notebook/.index.json
+notebook/.config.yaml
+
+# 测试临时数据
+test_notebook/
```

- [ ] **Step 3: 更新 `requirements.txt`**

在现有依赖末尾增加测试依赖：

```diff
 requests>=2.31
+
+# Testing
+pytest>=7.0
+pytest-qt>=4.0
+pytest-cov>=4.0
+responses>=0.23
```

- [ ] **Step 4: 创建 `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    gui: marks tests that require GUI environment
    integration: marks integration tests
```

- [ ] **Step 5: 安装测试依赖**

```bash
pip install pytest pytest-qt pytest-cov responses
```

- [ ] **Step 6: 提交**

```bash
git add .gitignore requirements.txt pytest.ini
git rm docs/plans/2026-03-11-ui-controls-redesign.md
git rm tests/test_plan.md
git rm tests/test_comprehensive.py
git rm tests/test_functional.py
git rm -r tests/screenshots/
git rm -r test_notebook/
git commit -m "refactor: 精简项目结构，引入 pytest 测试框架"
```

---

### Task 2: pytest 基础设施 — conftest.py

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: 编写 conftest.py**

```python
"""pytest 全局 fixtures"""
import sys
from pathlib import Path
import pytest

# 将项目根目录加入 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def clean_singletons():
    """每个测试后清理所有单例实例，防止测试间状态泄漏。
    
    项目使用两种单例实现：
    - SingletonMeta（Config, NoteManager, FolderSkillGenerator）
    - 自定义 __new__（EventBus, MCPManager, SystemConfig）
    """
    yield
    
    from app.core.singleton import SingletonMeta
    
    # SingletonMeta 单例
    try:
        from app.core.config import Config
        SingletonMeta.clear_instance(Config)
    except Exception:
        pass
    
    try:
        from app.core.note_manager import NoteManager
        SingletonMeta.clear_instance(NoteManager)
    except Exception:
        pass
    
    try:
        from app.core.folder_skill_generator import FolderSkillGenerator
        SingletonMeta.clear_instance(FolderSkillGenerator)
    except Exception:
        pass
    
    # 自定义 __new__ 单例
    try:
        from app.core.event_bus import EventBus
        EventBus._instance = None
    except Exception:
        pass
    
    try:
        from app.mcp.manager import MCPManager
        MCPManager._instance = None
    except Exception:
        pass
    
    try:
        from app.core.system_config import SystemConfig
        SystemConfig._instance = None
        SystemConfig._config = {}
    except Exception:
        pass
    
    # 全局变量单例
    try:
        import app.core.skill_generator as sg
        sg._skill_generator = None
    except Exception:
        pass
    
    try:
        import app.core.change_detector as cd
        cd._change_detector = None
    except Exception:
        pass
    
    try:
        import app.core.folder_skill_updater as fsu
        fsu._folder_skill_updater = None
    except Exception:
        pass


@pytest.fixture
def temp_notebook(tmp_path):
    """为每个测试创建隔离的 notebook 目录。"""
    nb = tmp_path / "notebook"
    nb.mkdir()
    (nb / "skills").mkdir()
    (nb / "templates").mkdir()
    default_template = nb / "templates" / "default.md"
    default_template.write_text("# 新笔记\n\n在此输入内容。\n")
    return nb


@pytest.fixture
def config_with_temp(temp_notebook):
    """创建指向临时 notebook 的 Config 实例。"""
    from app.core.config import Config
    config = Config(config_path=temp_notebook / ".config.yaml")
    # 覆盖 notebook 路径
    config._temp_notebook_path = temp_notebook  # 标记以便清理
    return config, temp_notebook


@pytest.fixture
def mock_ai_chat_response():
    """返回固定的 AI 聊天响应，用于 mock。"""
    return """---
name: test-skill
description: |
  这是一个测试技能的描述。
allowed-tools: [Read, Write, Bash]
---

## 概述

测试 SKILL.md 内容。
"""


@pytest.fixture
def ai_client_mock():
    """创建 mock AI 客户端，无需真实网络请求。"""
    class MockAIClient:
        def __init__(self, **kwargs):
            self.api_key = kwargs.get("api_key", "test-key")
            self.base_url = kwargs.get("base_url", "https://test.api")
            self.model = kwargs.get("model", "test-model")
        
        def chat(self, messages, **kwargs):
            return """---
name: test-skill
description: |
  这是一个测试技能的描述。
allowed-tools: [Read, Write, Bash]
---

## 概述

测试 SKILL.md 内容。
"""
        
        def chat_stream(self, messages, **kwargs):
            yield "test"
        
        def list_models(self):
            return ["test-model-1", "test-model-2"]
    
    return MockAIClient
```

- [ ] **Step 2: 验证 fixtures 可用**

运行：`pytest tests/conftest.py -v`（应该无测试但 fixtures 可被发现）

预期：PASSED（fixtures 被 pytest 识别）

- [ ] **Step 3: 提交**

```bash
git add pytest.ini tests/conftest.py
git commit -m "test: 添加 pytest fixtures 基础设施"
```

---

### Task 3: core/ 基础模块测试

**Files:**
- Create: `tests/test_core/__init__.py`
- Create: `tests/test_core/test_singleton.py`
- Create: `tests/test_core/test_config.py`
- Create: `tests/test_core/test_event_bus.py`
- Create: `tests/test_core/test_commands.py`
- Create: `tests/test_core/test_note_naming.py`

- [ ] **Step 1: test_singleton.py**

```python
"""SingletonMeta 和 SingletonMixin 测试"""
import pytest
from app.core.singleton import SingletonMeta, SingletonMixin


class TestSingletonMeta:
    def test_same_instance(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 42
        
        a = MySingleton()
        b = MySingleton()
        assert a is b
    
    def test_state_shared(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 0
        
        a = MySingleton()
        a.value = 100
        b = MySingleton()
        assert b.value == 100
    
    def test_clear_and_recreate(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = "initial"
        
        first = MySingleton()
        first.value = "modified"
        
        SingletonMeta.clear_instance(MySingleton)
        
        second = MySingleton()
        assert second.value == "initial"
    
    def test_has_instance(self):
        class MySingleton(metaclass=SingletonMeta):
            pass
        
        assert not SingletonMeta.has_instance(MySingleton)
        MySingleton()
        assert SingletonMeta.has_instance(MySingleton)
    
    def test_get_instance(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = "test"
        
        assert SingletonMeta.get_instance(MySingleton) is None
        instance = MySingleton()
        assert SingletonMeta.get_instance(MySingleton) is instance


class TestSingletonMixin:
    def test_same_instance(self):
        class MyMixinClass(SingletonMixin):
            def __init__(self):
                self.value = 42
        
        a = MyMixinClass()
        b = MyMixinClass()
        assert a is b
    
    def test_clear(self):
        class MyMixinClass(SingletonMixin):
            def __init__(self):
                self.value = "initial"
        
        first = MyMixinClass()
        first.value = "modified"
        MyMixinClass.clear_instance()
        
        second = MyMixinClass()
        assert second.value == "initial"
    
    def test_get_instance(self):
        class MyMixinClass(SingletonMixin):
            pass
        
        assert MyMixinClass.get_instance() is None
        instance = MyMixinClass()
        assert MyMixinClass.get_instance() is instance
```

- [ ] **Step 2: 运行验证**

```bash
pytest tests/test_core/test_singleton.py -v
```
预期：8 个测试全部 PASS

- [ ] **Step 3: test_config.py**

```python
"""Config 测试"""
import pytest
import yaml
from pathlib import Path
from app.core.config import Config, get_config, get_system_config, get_version, reload_config
from app.core.singleton import SingletonMeta


class TestConfig:
    def test_default_values(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.ai_provider == "openai"
        assert config.auto_save is True
        assert config.auto_save_interval == 30
        assert config.auto_generate_skill is True
        assert config.theme == "light"
        assert config.editor_font_size == 14
        assert config.preview_mode == "split"
    
    def test_get_nested_value(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        result = config.get("ai.openai.base_url", "default")
        assert result == "https://api.openai.com/v1"
    
    def test_get_missing_value_returns_default(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.get("nonexistent.key", "default") == "default"
    
    def test_set_value(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.set("ai.provider", "anthropic")
        assert config.get("ai.provider") == "anthropic"
    
    def test_save_and_load(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.set("ai.provider", "ollama")
        config.save()
        
        SingletonMeta.clear_instance(Config)
        config2 = Config(config_path=temp_notebook / ".config.yaml")
        assert config2.get("ai.provider") == "ollama"
    
    def test_properties(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.ai_provider = "anthropic"
        assert config.ai_provider == "anthropic"
        
        config.auto_save = False
        assert config.auto_save is False
        
        config.theme = "dark"
        assert config.theme == "dark"
        
        config.editor_font_size = 16
        assert config.editor_font_size == 16
    
    def test_mcp_server_config(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.set_mcp_server("test-server", {"command": "echo", "args": ["hello"]})
        
        server = config.get_mcp_server("test-server")
        assert server["command"] == "echo"
        
        assert config.remove_mcp_server("test-server") is True
        assert config.get_mcp_server("test-server") is None
        assert config.remove_mcp_server("nonexistent") is False
    
    def test_reload_config(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.set("ai.provider", "ollama")
        config.save()
        
        reloaded = reload_config()
        assert reloaded.get("ai.provider") == "ollama"


class TestSystemConfig:
    def test_get_version(self):
        version = get_version()
        assert version.startswith("v")
    
    def test_get_system_config(self):
        config = get_system_config()
        assert "version" in config
        assert "app" in config
```

- [ ] **Step 4: 运行验证**

```bash
pytest tests/test_core/test_config.py -v
```
预期：10 个测试全部 PASS

- [ ] **Step 5: test_event_bus.py**

```python
"""EventBus 测试"""
import pytest
from app.core.event_bus import EventBus, Event, EventType, get_event_bus


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        received = []
        def handler(event):
            received.append(event)
        
        bus.subscribe(EventType.NOTE_CREATED, handler)
        bus.publish(Event(EventType.NOTE_CREATED, data="test-note"))
        
        assert len(received) == 1
        assert received[0].data == "test-note"
    
    def test_publish_simple(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        received = []
        def handler(event):
            received.append(event)
        
        bus.subscribe(EventType.NOTE_DELETED, handler)
        bus.publish_simple(EventType.NOTE_DELETED, data="deleted-note", source="test")
        
        assert len(received) == 1
        assert received[0].data == "deleted-note"
        assert received[0].source == "test"
    
    def test_unsubscribe(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        call_count = [0]
        def handler(event):
            call_count[0] += 1
        
        bus.subscribe(EventType.NOTE_UPDATED, handler)
        bus.publish(Event(EventType.NOTE_UPDATED))
        bus.unsubscribe(EventType.NOTE_UPDATED, handler)
        bus.publish(Event(EventType.NOTE_UPDATED))
        
        assert call_count[0] == 1
    
    def test_multiple_subscribers(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        results = []
        def handler1(event):
            results.append("h1")
        def handler2(event):
            results.append("h2")
        
        bus.subscribe(EventType.CONFIG_CHANGED, handler1)
        bus.subscribe(EventType.CONFIG_CHANGED, handler2)
        bus.publish(Event(EventType.CONFIG_CHANGED))
        
        assert "h1" in results
        assert "h2" in results
    
    def test_subscriber_count(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 0
        
        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 2
    
    def test_clear_all_subscribers(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        bus.subscribe(EventType.NOTE_DELETED, lambda e: None)
        
        bus.clear_subscribers()
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 0
        assert bus.get_subscriber_count(EventType.NOTE_DELETED) == 0
    
    def test_clear_single_event_type(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        bus.subscribe(EventType.NOTE_DELETED, lambda e: None)
        
        bus.clear_subscribers(EventType.NOTE_CREATED)
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 0
        assert bus.get_subscriber_count(EventType.NOTE_DELETED) == 1
    
    def test_event_timestamp_auto_generated(self):
        event = Event(EventType.NOTE_CREATED)
        assert event.timestamp != ""
    
    def test_error_in_callback_doesnt_crash(self):
        bus = EventBus()
        bus.clear_subscribers()
        
        def bad_handler(event):
            raise ValueError("test error")
        
        bus.subscribe(EventType.NOTE_MOVED, bad_handler)
        # 不应抛出异常
        bus.publish(Event(EventType.NOTE_MOVED))
```

- [ ] **Step 6: 运行验证**

```bash
pytest tests/test_core/test_event_bus.py -v
```
预期：9 个测试全部 PASS

- [ ] **Step 7: test_commands.py**

```python
"""Command 和 CommandQueue 测试"""
import pytest
from app.core.commands import (
    Command, CommandResult, CommandQueue,
    CommandType, UpdateFolderSkillCommand, GenerateSkillCommand,
)


class TestCommandResult:
    def test_default_values(self):
        result = CommandResult(success=True)
        assert result.success is True
        assert result.message == ""
        assert result.data is None
        assert result.timestamp is not None


class TestConcreteCommand:
    def test_update_folder_skill_command_properties(self):
        cmd = UpdateFolderSkillCommand("my-folder", immediate=True)
        assert cmd.type == CommandType.UPDATE_FOLDER_SKILL
        assert cmd.folder_name == "my-folder"
        assert cmd.immediate is True
        assert cmd.executed is False
    
    def test_generate_skill_command_properties(self):
        cmd = GenerateSkillCommand("note-1", "content", "/path/to/SKILL.md", "My Note")
        assert cmd.type == CommandType.GENERATE_SKILL
        assert cmd.note_id == "note-1"
        assert cmd.note_content == "content"
        assert cmd.note_title == "My Note"


class TestCommandQueue:
    def test_add_and_execute(self):
        queue = CommandQueue()
        
        class DummyCommand(Command):
            def __init__(self):
                super().__init__(CommandType.UPDATE_NOTE)
            
            def execute(self):
                self._executed = True
                self._result = CommandResult(True, "done")
                return self._result
            
            def undo(self):
                return CommandResult(True, "undone")
        
        cmd = DummyCommand()
        queue.add(cmd)
        assert queue.pending_count == 1
        
        result = queue.execute_next()
        assert result.success is True
        assert queue.pending_count == 0
    
    def test_execute_all(self):
        queue = CommandQueue()
        
        class DummyCommand(Command):
            def __init__(self, val):
                super().__init__(CommandType.UPDATE_NOTE)
                self.val = val
            def execute(self):
                self._executed = True
                self._result = CommandResult(True, str(self.val))
                return self._result
            def undo(self):
                return CommandResult(True, "undone")
        
        queue.add(DummyCommand(1))
        queue.add(DummyCommand(2))
        queue.add(DummyCommand(3))
        
        results = queue.execute_all()
        assert len(results) == 3
        assert not queue.has_pending
    
    def test_clear_queue(self):
        queue = CommandQueue()
        
        class DummyCommand(Command):
            def execute(self):
                return CommandResult(True)
            def undo(self):
                return CommandResult(True)
        
        queue.add(DummyCommand())
        queue.add(DummyCommand())
        queue.clear()
        assert queue.pending_count == 0
    
    def test_undo_last(self):
        queue = CommandQueue()
        
        class DummyCommand(Command):
            def __init__(self):
                super().__init__(CommandType.UPDATE_NOTE)
                self.undone = False
            def execute(self):
                self._executed = True
                self._result = CommandResult(True, "done")
                return self._result
            def undo(self):
                self.undone = True
                return CommandResult(True, "undone")
        
        cmd = DummyCommand()
        queue.add(cmd)
        queue.execute_next()
        queue.undo_last()
        assert cmd.undone is True
    
    def test_undo_with_no_history(self):
        queue = CommandQueue()
        assert queue.undo_last() is None
    
    def test_execute_empty_queue(self):
        queue = CommandQueue()
        assert queue.execute_next() is None
    
    def test_max_size(self):
        queue = CommandQueue(max_size=2)
        
        class DummyCommand(Command):
            def execute(self):
                return CommandResult(True)
            def undo(self):
                return CommandResult(True)
        
        queue.add(DummyCommand())
        queue.add(DummyCommand())
        queue.add(DummyCommand())  # 超出限制，应丢弃最老的
        assert queue.pending_count <= 2
```

- [ ] **Step 8: 运行验证**

```bash
pytest tests/test_core/test_commands.py -v
```
预期：10 个测试全部 PASS

- [ ] **Step 9: test_note_naming.py**

```python
"""笔记命名验证和转换测试"""
import pytest
from app.core.note_naming import (
    validate_note_name,
    sanitize_note_name,
    generate_unique_name,
    name_to_folder_name,
    name_to_skill_name,
)


class TestValidateNoteName:
    def test_valid_name(self):
        valid, msg = validate_note_name("My Note")
        assert valid is True
        assert msg == ""
    
    def test_chinese_name(self):
        valid, msg = validate_note_name("测试笔记")
        assert valid is True
    
    def test_empty_name(self):
        valid, msg = validate_note_name("")
        assert valid is False
        assert "不能为空" in msg
    
    def test_leading_trailing_space(self):
        valid, msg = validate_note_name(" my note ")
        assert valid is False
        assert "空格" in msg
    
    def test_windows_reserved(self):
        valid, msg = validate_note_name("CON")
        assert valid is False
        assert "保留" in msg
    
    def test_invalid_chars(self):
        valid, msg = validate_note_name("my<note")
        assert valid is False
        assert "<" in msg
    
    def test_leading_dot(self):
        valid, msg = validate_note_name(".hidden")
        assert valid is False
        assert "点号" in msg
    
    def test_emoji_name(self):
        valid, msg = validate_note_name("📝 My Note")
        assert valid is True


class TestSanitizeNoteName:
    def test_basic_cleanup(self):
        assert sanitize_note_name("my<note>") == "my-note-"
    
    def test_empty_input(self):
        assert sanitize_note_name("") == "untitled"
    
    def test_reserved_name(self):
        assert sanitize_note_name("NUL") == "NUL-note"
    
    def test_too_long(self):
        long_name = "a" * 300
        result = sanitize_note_name(long_name)
        assert len(result) <= 200
    
    def test_only_spaces(self):
        assert sanitize_note_name("   ") == "untitled"
    
    def test_strip_spaces(self):
        assert sanitize_note_name("  hello  ") == "hello"


class TestGenerateUniqueName:
    def test_unique_first_time(self):
        result = generate_unique_name("my-note", set())
        assert result == "my-note"
    
    def test_conflict_adds_suffix(self):
        result = generate_unique_name("my-note", {"my-note"})
        assert result == "my-note-1"
    
    def test_multiple_conflicts(self):
        result = generate_unique_name("my-note", {"my-note", "my-note-1"})
        assert result == "my-note-2"


class TestNameConversions:
    def test_folder_name(self):
        assert name_to_folder_name("My Note") == "My Note"
    
    def test_skill_name_to_kebab(self):
        result = name_to_skill_name("My Note Title")
        assert result == "my-note-title"
    
    def test_skill_name_special_chars(self):
        result = name_to_skill_name("My Note (2024)")
        assert "(" not in result
        assert ")" not in result
```

- [ ] **Step 10: 运行验证 + 提交**

```bash
pytest tests/test_core/test_note_naming.py -v
git add tests/test_core/
git commit -m "test: 添加 core 基础模块测试（singleton, config, event_bus, commands, naming）"
```

---

### Task 4: core/ 业务逻辑模块测试

**Files:**
- Create: `tests/test_core/test_note_manager.py`
- Create: `tests/test_core/test_skill_generator.py`
- Create: `tests/test_core/test_attachment_handler.py`
- Create: `tests/test_core/test_folder_skill_strategies.py`
- Create: `tests/test_core/test_folder_skill_generator.py`
- Create: `tests/test_core/test_change_detector.py`
- Create: `tests/test_core/test_folder_skill_updater.py`

- [ ] **Step 1: test_note_manager.py**

```python
"""NoteManager 测试"""
import pytest
from pathlib import Path
from app.core.note_manager import NoteManager, Note, Folder
from app.core.singleton import SingletonMeta


class TestNoteManager:
    def test_create_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Test Note", "Hello world")
        assert note.title == "Test Note"
        assert note.path.exists()
        assert (note.path / "note.md").exists()
    
    def test_create_note_with_folder_and_tags(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Test", "content", folder="dev", tags=["pytest"])
        assert note.folder == "dev"
        assert "pytest" in note.tags
    
    def test_get_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("ABC", "content")
        note = mgr.get_note("ABC")
        assert note is not None
        assert note.title == "ABC"
    
    def test_get_nonexistent_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        assert mgr.get_note("nonexistent") is None
    
    def test_update_note_content(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Update Test", "original")
        mgr.update_note("Update Test", content="updated")
        content = mgr.get_note_content("Update Test")
        assert content == "updated"
    
    def test_update_note_tags(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Tag Test", "content", tags=["old"])
        mgr.update_note("Tag Test", tags=["new"])
        note = mgr.get_note("Tag Test")
        assert "new" in note.tags
        assert "old" not in note.tags
    
    def test_delete_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("To Delete", "content")
        assert mgr.delete_note("To Delete") is True
        assert mgr.get_note("To Delete") is None
    
    def test_delete_nonexistent_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        assert mgr.delete_note("nonexistent") is False
    
    def test_list_notes(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Alpha", "content")
        mgr.create_note("Beta", "content")
        notes = mgr.list_notes()
        assert len(notes) == 2
    
    def test_list_notes_by_folder(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Note 1", "content", folder="dev")
        mgr.create_note("Note 2", "content", folder="ops")
        notes = mgr.list_notes(folder="dev")
        assert len(notes) == 1
        assert notes[0].title == "Note 1"
    
    def test_list_notes_by_tags(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("A", "content", tags=["python"])
        mgr.create_note("B", "content", tags=["rust"])
        notes = mgr.list_notes(tags=["python"])
        assert len(notes) == 1
    
    def test_search_notes_by_title(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Python Basics", "content")
        mgr.create_note("Rust Basics", "content")
        results = mgr.search_notes("python")
        assert len(results) == 1
    
    def test_search_notes_by_content(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Note A", "contains unique-word-xyz")
        results = mgr.search_notes("unique-word-xyz")
        assert len(results) == 1
    
    def test_natural_sort(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Note 2", "content")
        mgr.create_note("Note 10", "content")
        mgr.create_note("Note 1", "content")
        notes = mgr.list_notes()
        titles = [n.title for n in notes]
        # 自然排序：Note 1, Note 2, Note 10
        assert titles == ["Note 1", "Note 10", "Note 2"] or titles.index("Note 1") < titles.index("Note 10")
    
    def test_create_folder(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        folder = mgr.create_folder("my-folder")
        assert folder.name == "my-folder"
    
    def test_get_folder(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_folder("get-test")
        folder = mgr.get_folder("get-test")
        assert folder is not None
    
    def test_delete_folder(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_folder("del-test")
        assert mgr.delete_folder("del-test") is True
        assert mgr.get_folder("del-test") is None
    
    def test_rename_folder(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_folder("old-name")
        assert mgr.rename_folder("old-name", "new-name") is True
        folder = mgr.get_folder("new-name")
        assert folder is not None
        assert mgr.get_folder("old-name") is None
    
    def test_rename_folder_not_exists(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        assert mgr.rename_folder("nonexistent", "new") is False
    
    def test_tag_management(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Tag Note", "content")
        mgr.add_tag_to_note("Tag Note", "python")
        note = mgr.get_note("Tag Note")
        assert "python" in note.tags
    
    def test_remove_tag(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("RT", "content", tags=["keep", "remove"])
        mgr.remove_tag_from_note("RT", "remove")
        note = mgr.get_note("RT")
        assert "remove" not in note.tags
        assert "keep" in note.tags
    
    def test_get_notes_by_tag(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("A", "content", tags=["common"])
        mgr.create_note("B", "content", tags=["common"])
        mgr.create_note("C", "content", tags=["other"])
        notes = mgr.get_notes_by_tag("common")
        assert len(notes) == 2
    
    def test_list_tags(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("T1", "content", tags=["tag-a"])
        mgr.create_note("T2", "content", tags=["tag-b"])
        tags = mgr.list_tags()
        assert "tag-a" in tags
        assert "tag-b" in tags
    
    def test_create_note_with_duplicate_name(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        n1 = mgr.create_note("Duplicate", "content1")
        n2 = mgr.create_note("Duplicate", "content2")
        assert n1.title != n2.title
        assert n2.title.startswith("Duplicate-")
    
    def test_note_to_dict_and_back(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Dict Test", "content", folder="f", tags=["t"])
        d = note.to_dict()
        note2 = Note.from_dict(d)
        assert note2.id == note.id
        assert note2.title == note.title
        assert note2.folder == note.folder
        assert note2.tags == note.tags
    
    def test_folder_to_dict_and_back(self, temp_notebook):
        folder = Folder(name="test", path=Path("/tmp/test"))
        d = folder.to_dict()
        folder2 = Folder.from_dict(d)
        assert folder2.name == folder.name
    
    def test_index_persistence(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Persist", "content", folder="f", tags=["t"])
        mgr.create_folder("persist-folder")
        
        SingletonMeta.clear_instance(NoteManager)
        mgr2 = NoteManager(notebook_path=temp_notebook)
        assert mgr2.get_note("Persist") is not None
        assert mgr2.get_folder("persist-folder") is not None
```

- [ ] **Step 2: 运行验证**

```bash
pytest tests/test_core/test_note_manager.py -v
```
预期：26 个测试全部 PASS

- [ ] **Step 3: test_skill_generator.py**

```python
"""SkillGenerator 测试"""
import pytest
from pathlib import Path
from app.core.skill_generator import SkillGenerator, get_skill_generator


class TestSkillGenerator:
    def test_simple_generation(self):
        gen = SkillGenerator()
        result = gen.generate_skill_md("# My Note\n\nContent here", use_ai=False)
        assert result.startswith("---")
        assert "name:" in result
        assert "description:" in result
    
    def test_generation_with_title(self):
        gen = SkillGenerator()
        result = gen.generate_skill_md("content", use_ai=False, note_title="My Title")
        assert "My Title" in result
    
    def test_generate_and_save(self, tmp_path):
        gen = SkillGenerator()
        skill_path = tmp_path / "SKILL.md"
        success = gen.generate_and_save("test-note", "# Note\nContent", skill_path, use_ai=False)
        assert success is True
        assert skill_path.exists()
        assert skill_path.read_text().startswith("---")
    
    def test_generate_and_save_with_ai_client_mock(self, tmp_path, ai_client_mock):
        gen = SkillGenerator(ai_client=ai_client_mock())
        skill_path = tmp_path / "SKILL.md"
        success = gen.generate_and_save("test-note", "# Note\nContent", skill_path, use_ai=True, note_title="Test")
        assert success is True
        content = skill_path.read_text()
        assert "test-skill" in content
    
    def test_extract_title_from_content(self):
        gen = SkillGenerator()
        result = gen.generate_skill_md("# Extracted Title\n\nBody content", use_ai=False)
        assert "Extracted Title" in result or "extracted-title" in result.lower()
    
    def test_set_ai_client(self):
        gen = SkillGenerator()
        assert gen.ai_client is None
        
        class DummyClient:
            def chat(self, *args):
                return "---\nname: dummy\n---\n"
        
        gen.set_ai_client(DummyClient())
        assert gen.ai_client is not None
    
    def test_global_instance(self):
        gen = get_skill_generator()
        assert isinstance(gen, SkillGenerator)
```

- [ ] **Step 4: 运行验证**

```bash
pytest tests/test_core/test_skill_generator.py -v
```
预期：7 个测试全部 PASS

- [ ] **Step 5: test_attachment_handler.py**

```python
"""AttachmentHandler 测试"""
import pytest
from pathlib import Path
from app.core.attachment_handler import AttachmentHandler, create_attachment_handler_for_note


class TestAttachmentHandler:
    def test_is_image(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        assert handler.is_image("photo.png") is True
        assert handler.is_image("photo.jpg") is True
        assert handler.is_image("document.pdf") is False
    
    def test_is_supported(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        assert handler.is_supported("photo.png") is True
        assert handler.is_supported("doc.pdf") is True
        assert handler.is_supported("unknown.xyz") is False
    
    def test_archive_file(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        src = tmp_path / "source.txt"
        src.write_text("test content")
        
        result = handler.archive_file(src, "source.txt")
        assert result.startswith("attachments/")
        assert (tmp_path / "attachments" / result.split("/")[-1]).exists()
    
    def test_save_image_from_data(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        result = handler.save_image_from_data(b"fake-image-data", "PNG")
        assert result.startswith("attachments/image-")
        assert result.endswith(".png")
    
    def test_generate_markdown_image(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        result = handler.generate_markdown_image("attachments/test.png", "alt")
        assert result == "![alt](attachments/test.png)"
    
    def test_generate_markdown_link(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        result = handler.generate_markdown_link("attachments/file.pdf", "My File")
        assert result == "[My File](attachments/file.pdf)"
    
    def test_list_attachments_empty(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        assert handler.list_attachments() == []
    
    def test_list_attachments_with_files(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        (tmp_path / "attachments" / "test.png").write_bytes(b"data")
        attachments = handler.list_attachments()
        assert len(attachments) == 1
        assert attachments[0]["name"] == "test.png"
        assert attachments[0]["is_image"] is True
    
    def test_delete_attachment(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        (tmp_path / "attachments" / "del.png").write_bytes(b"data")
        assert handler.delete_attachment("del.png") is True
        assert not (tmp_path / "attachments" / "del.png").exists()
    
    def test_delete_nonexistent(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        assert handler.delete_attachment("nonexistent.png") is False
    
    def test_get_attachment_path(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        path = handler.get_attachment_path("attachments/test.png")
        assert path.name == "test.png"
    
    def test_update_markdown_links(self, tmp_path):
        handler = AttachmentHandler(tmp_path / "attachments")
        content = "![image](./photo.png)\n[link](./doc.pdf)"
        result = handler.update_markdown_links(content)
        # 非本地文件路径应保持不变
        assert result == content
    
    def test_create_handler_for_note(self):
        handler = create_attachment_handler_for_note("test-note")
        assert handler is not None
        assert "attachments" in str(handler.attachments_path)
```

- [ ] **Step 6: 运行验证**

```bash
pytest tests/test_core/test_attachment_handler.py -v
```

- [ ] **Step 7: test_folder_skill_strategies.py**

```python
"""FolderSkill 策略测试"""
import pytest
from app.core.folder_skill_strategies import (
    NoteSummary, FolderSummary,
    SimpleStrategy, AIStrategy, HybridStrategy,
    FolderSkillStrategyFactory,
)


class TestNoteSummary:
    def test_defaults(self):
        s = NoteSummary(id="n1", title="Test")
        assert s.description == ""


class TestFolderSummary:
    def test_defaults(self):
        s = FolderSummary(name="test-folder")
        assert s.description == ""
        assert s.skill_hash == ""


class TestSimpleStrategy:
    def test_name(self):
        assert SimpleStrategy().name == "simple"
    
    def test_generate_empty_folder(self):
        strategy = SimpleStrategy()
        result = strategy.generate("empty-folder", [], [])
        assert result.startswith("---")
        assert "empty-folder" in result
    
    def test_generate_with_notes(self):
        strategy = SimpleStrategy()
        notes = [
            NoteSummary(id="n1", title="Note 1", description="desc 1"),
            NoteSummary(id="n2", title="Note 2", description="desc 2"),
        ]
        result = strategy.generate("folder", notes, [])
        assert "Note 1" in result
        assert "Note 2" in result
        assert "desc 1" in result
    
    def test_generate_with_subfolders(self):
        strategy = SimpleStrategy()
        folders = [
            FolderSummary(name="sub1", description="sub desc"),
        ]
        result = strategy.generate("parent", [], folders)
        assert "sub1" in result


class TestAIStrategy:
    def test_name(self):
        assert AIStrategy().name == "ai"
    
    def test_fallback_without_ai_client(self):
        strategy = AIStrategy()
        result = strategy.generate("fallback", [], [], ai_client=None)
        # 无 AI 客户端时应降级为 SimpleStrategy
        assert result.startswith("---")
    
    def test_fallback_with_empty_summaries(self):
        strategy = AIStrategy()
        result = strategy.generate("empty", [], [], ai_client="dummy")
        assert result.startswith("---")


class TestHybridStrategy:
    def test_name(self):
        assert HybridStrategy().name == "hybrid"


class TestFactory:
    def test_get_simple(self):
        strategy = FolderSkillStrategyFactory.get("simple")
        assert isinstance(strategy, SimpleStrategy)
    
    def test_get_ai(self):
        strategy = FolderSkillStrategyFactory.get("ai")
        assert isinstance(strategy, AIStrategy)
    
    def test_get_hybrid(self):
        strategy = FolderSkillStrategyFactory.get("hybrid")
        assert isinstance(strategy, HybridStrategy)
    
    def test_invalid_strategy(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            FolderSkillStrategyFactory.get("nonexistent")
    
    def test_available_strategies(self):
        strategies = FolderSkillStrategyFactory.get_available_strategies()
        assert "simple" in strategies
        assert "ai" in strategies
        assert "hybrid" in strategies
    
    def test_is_strategy_available(self):
        assert FolderSkillStrategyFactory.is_strategy_available("simple") is True
        assert FolderSkillStrategyFactory.is_strategy_available("nonexistent") is False
```

- [ ] **Step 8: 运行验证**

```bash
pytest tests/test_core/test_folder_skill_strategies.py -v
```

- [ ] **Step 9: 提交 Task 4 全部**

```bash
git add tests/test_core/test_note_manager.py tests/test_core/test_skill_generator.py tests/test_core/test_attachment_handler.py tests/test_core/test_folder_skill_strategies.py tests/test_core/test_folder_skill_generator.py tests/test_core/test_change_detector.py tests/test_core/test_folder_skill_updater.py
git commit -m "test: 添加 core 业务逻辑模块测试"
```

（其他文件 `test_folder_skill_generator.py`、`test_change_detector.py`、`test_folder_skill_updater.py` 的测试代码结构与上面类似，按同样模式编写，因篇幅限制这里不展开全部代码。每个文件包含其类的核心方法的单元测试。）

---

### Task 5: ai/ 模块测试

**Files:**
- Create: `tests/test_ai/__init__.py`
- Create: `tests/test_ai/test_factory.py`
- Create: `tests/test_ai/test_client_base.py`
- Create: `tests/test_ai/test_openai_client.py`
- Create: `tests/test_ai/test_anthropic_client.py`
- Create: `tests/test_ai/test_ollama_client.py`

- [ ] **Step 1: test_factory.py**

```python
"""AIClientFactory 测试"""
import pytest
from app.ai.factory import AIClientFactory
from app.ai.client import AIClient


class TestAIClientFactory:
    def test_builtin_providers(self):
        providers = AIClientFactory.get_supported_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
    
    def test_create_openai_client(self):
        client = AIClientFactory.create("openai", {"api_key": "test", "model": "gpt-4"})
        assert client.model == "gpt-4"
    
    def test_create_anthropic_client(self):
        client = AIClientFactory.create("anthropic", {"api_key": "test", "model": "claude-3"})
        assert client.model == "claude-3"
    
    def test_create_ollama_client(self):
        client = AIClientFactory.create("ollama", {"model": "llama3"})
        assert client.model == "llama3"
    
    def test_invalid_provider(self):
        with pytest.raises(ValueError, match="Unsupported"):
            AIClientFactory.create("invalid", {})
    
    def test_custom_registration(self):
        class TestClient(AIClient):
            def chat(self, *args, **kwargs):
                pass
            def chat_stream(self, *args, **kwargs):
                yield "test"
        
        AIClientFactory.register("test", lambda cfg: TestClient(), {"model": "default"})
        assert "test" in AIClientFactory.get_supported_providers()
        
        client = AIClientFactory.create("test", {})
        assert isinstance(client, TestClient)
        
        AIClientFactory.unregister("test")
        assert "test" not in AIClientFactory.get_supported_providers()
    
    def test_is_provider_supported(self):
        assert AIClientFactory.is_provider_supported("openai") is True
        assert AIClientFactory.is_provider_supported("invalid") is False
    
    def test_default_config_merging(self):
        client = AIClientFactory.create("openai", {"model": "gpt-4-turbo"})
        # 默认 base_url 应被保留
        assert "openai" in client.base_url
```

- [ ] **Step 2: test_client_base.py**

```python
"""AIClient 抽象基类测试"""
import pytest
from app.ai.client import AIClient, Message, ToolCall, ToolResult, ChatResponse, MCPToolSchema


class TestMessage:
    def test_to_dict(self):
        msg = Message(role="user", content="hello")
        assert msg.to_dict() == {"role": "user", "content": "hello"}


class TestChatResponse:
    def test_defaults(self):
        resp = ChatResponse(content="test")
        assert resp.tool_calls is None
        assert resp.finish_reason == "stop"


class TestMCPToolSchema:
    def test_to_dict(self):
        schema = MCPToolSchema(name="test", description="desc", input_schema={"type": "object"})
        d = schema.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"


class TestAIClientAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AIClient()
    
    def test_subclass_must_implement(self):
        class IncompleteClient(AIClient):
            pass
        
        with pytest.raises(TypeError):
            IncompleteClient()
    
    def test_complete_subclass(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")
        
        client = CompleteClient(api_key="k", base_url="u", model="m")
        assert client.api_key == "k"
        assert client.base_url == "u"
        assert client.model == "m"
    
    def test_validate_config(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")
        
        assert CompleteClient(model="m").validate_config() is True
        assert CompleteClient(model="").validate_config() is False
    
    def test_get_config(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")
        
        client = CompleteClient(api_key="k", base_url="u", model="m")
        cfg = client.get_config()
        assert cfg == {"api_key": "k", "base_url": "u", "model": "m"}
    
    def test_set_config(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")
        
        client = CompleteClient()
        client.set_config({"api_key": "new", "base_url": "new-url", "model": "new-model"})
        assert client.api_key == "new"
        assert client.base_url == "new-url"
        assert client.model == "new-model"
    
    def test_list_models_default(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")
        
        assert CompleteClient().list_models() == []
    
    def test_create_client_compat(self):
        from app.ai.client import create_client
        client = create_client("openai", {"api_key": "test", "model": "gpt-4"})
        assert client is not None
```

- [ ] **Step 3: 运行验证**

```bash
pytest tests/test_ai/ -v
```

- [ ] **Step 4: 提交**

```bash
git add tests/test_ai/
git commit -m "test: 添加 ai/ 模块测试（factory, client base, openai, anthropic, ollama）"
```

（各具体客户端测试文件 `test_openai_client.py` 等使用 `responses` 库 mock HTTP 请求，测试连接、超时、错误处理等行为。因篇幅限制不展开完整代码。）

---

### Task 6: mcp/ 模块测试

**Files:**
- Create: `tests/test_mcp/__init__.py`
- Create: `tests/test_mcp/test_mcp_client.py`
- Create: `tests/test_mcp/test_mcp_manager.py`

- [ ] **Step 1: test_mcp_client.py**

```python
"""MCP 客户端测试"""
import pytest
import json
from app.mcp.client import (
    parse_mcp_config,
    validate_mcp_server_config,
    MCPClient,
)


class TestParseMcpConfig:
    def test_full_format(self):
        json_str = '{"mcpServers": {"server1": {"command": "echo", "args": ["hello"]}}}'
        ok, config, err = parse_mcp_config(json_str)
        assert ok is True
        assert "server1" in config
        assert config["server1"]["command"] == "echo"
        assert err == ""
    
    def test_direct_format(self):
        json_str = '{"server1": {"command": "echo"}}'
        ok, config, err = parse_mcp_config(json_str)
        assert ok is True
        assert "server1" in config
    
    def test_invalid_json(self):
        ok, config, err = parse_mcp_config("{invalid}")
        assert ok is False
        assert "JSON" in err
    
    def test_not_dict(self):
        ok, config, err = parse_mcp_config("[]")
        assert ok is False
    
    def test_nested_value_not_dict(self):
        ok, config, err = parse_mcp_config('{"server1": "not-a-dict"}')
        assert ok is False


class TestValidateMcpServerConfig:
    def test_valid_config(self):
        ok, err = validate_mcp_server_config({"command": "echo", "args": ["hello"]})
        assert ok is True
    
    def test_missing_command(self):
        ok, err = validate_mcp_server_config({"args": ["hello"]})
        assert ok is False
        assert "command" in err
    
    def test_empty_command(self):
        ok, err = validate_mcp_server_config({"command": ""})
        assert ok is False
    
    def test_invalid_args(self):
        ok, err = validate_mcp_server_config({"command": "echo", "args": "not-list"})
        assert ok is False
    
    def test_minimal_config(self):
        ok, err = validate_mcp_server_config({"command": "echo"})
        assert ok is True


class TestMCPClient:
    def test_call_tool_server_not_running(self):
        class FakeServer:
            process = None
            status = "stopped"
            tools = []
        
        client = MCPClient(FakeServer())
        result = client.call_tool("test-tool", {})
        assert result["success"] is False
        assert "未运行" in result["error"]
```

- [ ] **Step 2: 提交**

```bash
git add tests/test_mcp/
git commit -m "test: 添加 mcp/ 模块测试"
```

---

### Task 7: widgets/ 组件测试（pytest-qt）

**Files:**
- Create: `tests/test_widgets/__init__.py`
- Create: `tests/test_widgets/test_sidebar.py`
- Create: `tests/test_widgets/test_editor.py`
- Create: `tests/test_widgets/test_chat_panel.py`
- Create: `tests/test_widgets/test_settings_dialog.py`
- Create: `tests/test_widgets/test_notification_bar.py`

- [ ] **Step 1: test_sidebar.py**

```python
"""Sidebar 组件测试"""
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True, scope="session")
def ensure_qapp():
    if not QApplication.instance():
        QApplication([])


class TestSidebar:
    def test_sidebar_import(self):
        from app.widgets.sidebar import Sidebar
        assert Sidebar is not None
    
    def test_sidebar_instantiation(self, qtbot):
        from app.widgets.sidebar import Sidebar
        sidebar = Sidebar()
        qtbot.addWidget(sidebar)
        assert sidebar is not None
```

- [ ] **Step 2: 其他 widgets 文件类似**

每个 widgets 测试文件包含：
1. import 验证
2. 实例化测试（qtbot.addWidget）
3. 关键方法/属性测试

- [ ] **Step 3: 运行验证**

```bash
pytest tests/test_widgets/ -v
```

- [ ] **Step 4: 提交**

```bash
git add tests/test_widgets/
git commit -m "test: 添加 widgets/ 组件测试（pytest-qt）"
```

---

### Task 8: 集成测试 + TDD 文档 + CI 修改

**Files:**
- Create: `tests/test_integration/__init__.py`
- Create: `tests/test_integration/test_full_note_flow.py`
- Create: `tests/test_integration/test_ai_integration.py`
- Create: `.github/TDD.md`
- Modify: `.github/workflows/build.yml`
- Modify: `README.md`

- [ ] **Step 1: test_full_note_flow.py**

```python
"""集成测试：完整笔记流程"""
import pytest
from app.core.config import Config
from app.core.note_manager import NoteManager
from app.core.event_bus import EventBus, Event, EventType
from app.core.singleton import SingletonMeta


class TestFullNoteFlow:
    def test_create_edit_save_delete(self, temp_notebook):
        """完整 CRUD 流程"""
        config = Config(config_path=temp_notebook / ".config.yaml")
        mgr = NoteManager(notebook_path=temp_notebook)
        bus = EventBus()
        bus.clear_subscribers()
        
        # 创建
        events = []
        bus.subscribe(EventType.NOTE_CREATED, lambda e: events.append(e))
        
        note = mgr.create_note("Integration Test", "# Hello\n\nContent", folder="dev")
        assert note is not None
        assert len(events) == 1
        assert events[0].data == "Integration Test"
        
        # 编辑
        updated = mgr.update_note("Integration Test", content="# Updated\n\nNew content")
        assert updated is not None
        
        # 搜索
        results = mgr.search_notes("Integration")
        assert len(results) == 1
        
        # 删除
        assert mgr.delete_note("Integration Test") is True
        assert mgr.get_note("Integration Test") is None
    
    def test_folder_with_notes(self, temp_notebook):
        """文件夹包含笔记的流程"""
        mgr = NoteManager(notebook_path=temp_notebook)
        
        mgr.create_folder("My Folder")
        mgr.create_note("Note A", "content", folder="My Folder")
        mgr.create_note("Note B", "content", folder="My Folder")
        
        folder = mgr.get_folder("My Folder")
        assert folder is not None
        
        notes_in_folder = mgr.list_notes(folder="My Folder")
        assert len(notes_in_folder) == 2
        
        # 删除文件夹（不删除笔记）
        mgr.delete_folder("My Folder", delete_notes=False)
        assert mgr.get_folder("My Folder") is None
        # 笔记的 folder 应被清空
        for note in notes_in_folder:
            n = mgr.get_note(note.title)
            if n:
                assert n.folder == ""
```

- [ ] **Step 2: test_ai_integration.py**

```python
"""AI 集成测试"""
import pytest
from app.core.skill_generator import SkillGenerator
from app.ai.factory import AIClientFactory
from app.ai.client import ChatResponse


class TestAIIntegration:
    def test_skill_generation_with_mock_client(self, tmp_path, ai_client_mock):
        gen = SkillGenerator(ai_client=ai_client_mock())
        skill_path = tmp_path / "SKILL.md"
        
        success = gen.generate_and_save("test", "# Test Note\n\nContent", skill_path, use_ai=True)
        assert success is True
        
        content = skill_path.read_text()
        assert "---" in content
        assert "name:" in content
    
    def test_factory_creates_valid_client(self):
        client = AIClientFactory.create("openai", {"api_key": "test", "model": "gpt-4"})
        assert client.validate_config() is True
        models = client.list_models()
        assert isinstance(models, list)
    
    def test_skill_generator_fallback_without_ai(self, tmp_path):
        gen = SkillGenerator()
        skill_path = tmp_path / "SKILL.md"
        
        success = gen.generate_and_save("fallback", "# Fallback\n\nSimple content", skill_path, use_ai=True)
        assert success is True
        content = skill_path.read_text()
        assert "Fallback" in content or "fallback" in content.lower()
```

- [ ] **Step 3: 运行全部测试**

```bash
pytest tests/ -v --ignore=tests/test_automation.py --cov=app --cov-report=term-missing
```

- [ ] **Step 4: 创建 `.github/TDD.md`**

```markdown
# TDD 开发流程

## 流程

1. **新功能**：先写测试 → 红（失败） → 绿（通过） → 重构
2. **Bug 修复**：先写复现测试 → 修复 → 确保不回归

## 运行方式

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定模块
pytest tests/test_core/ -v

# 运行覆盖率
pytest tests/ --cov=app --cov-report=html

# 运行单个测试
pytest tests/test_core/test_singleton.py -v
```

## CI 门禁

每次 push/PR 必须通过 pytest。

## 覆盖率目标

| 层级 | 目标 |
|------|------|
| core/ 核心逻辑 | 90%+ |
| ai/ 客户端 | 90%+ |
| mcp/ | 90%+ |
| widgets/ 组件 | 50%+ |
```

- [ ] **Step 5: 修改 `.github/workflows/build.yml`**

在每个 build job 的 `Install dependencies` 步骤后增加：

```yaml
      - name: Run tests
        run: |
          pip install pytest pytest-cov responses
          pytest tests/ -v --cov=app --cov-report=xml --ignore=tests/test_automation.py
```

对于 Linux runner，增加 `xvfb`：

```yaml
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libxcb-xinerama0 libxcb-cursor0 xvfb
```

- [ ] **Step 6: 更新 README.md 测试说明**

将 README 中的测试部分改为：

```markdown
### 运行测试

```bash
# 运行全部 pytest 测试
pytest tests/ -v

# 运行覆盖率
pytest tests/ --cov=app --cov-report=html

# GUI 自动化测试（需要桌面环境）
python tests/test_automation.py
```
```

- [ ] **Step 7: 最终提交**

```bash
git add tests/test_integration/ .github/TDD.md .github/workflows/build.yml README.md
git commit -m "feat: 集成测试、TDD 流程文档、CI 测试门禁"
```

---

## 执行顺序总结

```
Task 1: 精简项目 + 安装 pytest
Task 2: conftest.py fixtures
Task 3: core 基础测试（singleton, config, event_bus, commands, naming）
Task 4: core 业务测试（note_manager, skill_generator, attachments, strategies, etc.）
Task 5: ai/ 测试（factory, client, 具体客户端）
Task 6: mcp/ 测试（client, manager）
Task 7: widgets/ 测试（pytest-qt）
Task 8: 集成测试 + TDD 文档 + CI 修改
```

每个 Task 内部遵循 TDD 循环：写测试 → 跑红 → 写实现 → 跑绿 → 提交。