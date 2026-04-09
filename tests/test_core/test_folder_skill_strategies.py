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
