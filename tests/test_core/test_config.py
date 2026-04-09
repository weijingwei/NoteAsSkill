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

    def test_theme_property(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.theme = "dark"
        assert config.theme == "dark"

    def test_editor_font_size(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.editor_font_size == 14
        config.editor_font_size = 16
        assert config.editor_font_size == 16

    def test_preview_mode(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.preview_mode == "split"
        config.preview_mode = "editor"
        assert config.preview_mode == "editor"

    def test_folder_skill_properties(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.folder_skill_enabled is True
        assert config.folder_skill_auto_update is True
        assert config.folder_skill_update_delay == 30
        assert config.folder_skill_generation_mode == "hybrid"

    def test_git_properties(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.git_enabled is False
        assert config.git_branch == "main"

    def test_mcp_properties(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        assert config.mcp_enabled is False
        assert config.mcp_servers == {}

    def test_get_ai_config_for_provider(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        ai_config = config.get_ai_config("openai")
        assert "base_url" in ai_config
        assert ai_config["model"] == "gpt-4"

    def test_set_ai_config(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.set_ai_config("custom", {"api_key": "test", "model": "custom-model"})
        assert config.get_ai_config("custom")["api_key"] == "test"

    def test_mcp_server_management(self, temp_notebook):
        config = Config(config_path=temp_notebook / ".config.yaml")
        config.set_mcp_server("test-server", {"command": "test"})
        assert config.get_mcp_server("test-server")["command"] == "test"

        assert config.remove_mcp_server("test-server") is True
        assert config.get_mcp_server("test-server") is None
        assert config.remove_mcp_server("nonexistent") is False

    def test_load_creates_file_if_not_exists(self, temp_notebook):
        config_path = temp_notebook / ".config.yaml"
        assert not config_path.exists()
        Config(config_path=config_path)
        assert config_path.exists()


class TestGetConfig:
    def test_returns_singleton(self):
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2


class TestReloadConfig:
    def test_creates_new_instance(self, temp_notebook):
        original = Config(config_path=temp_notebook / ".config.yaml")
        reloaded = reload_config()
        assert reloaded is not original or reloaded is get_config()


class TestSystemConfig:
    def test_get_version(self):
        version = get_version()
        assert version.startswith("v")

    def test_get_system_config(self):
        config = get_system_config()
        assert "version" in config
        assert "app" in config
