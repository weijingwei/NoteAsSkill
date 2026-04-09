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
