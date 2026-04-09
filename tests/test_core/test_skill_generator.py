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
        assert "my-title" in result.lower() or "My Title" in result

    def test_generate_and_save(self, tmp_path):
        gen = SkillGenerator()
        skill_path = tmp_path / "SKILL.md"
        success = gen.generate_and_save("test-note", "# Note\nContent", skill_path, use_ai=False)
        assert success is True
        assert skill_path.exists()
        assert skill_path.read_text(encoding="utf-8").startswith("---")

    def test_generate_and_save_with_ai_client_mock(self, tmp_path, ai_client_mock):
        gen = SkillGenerator(ai_client=ai_client_mock())
        skill_path = tmp_path / "SKILL.md"
        success = gen.generate_and_save("test-note", "# Note\nContent", skill_path, use_ai=True, note_title="Test")
        assert success is True
        content = skill_path.read_text(encoding="utf-8")
        assert "name:" in content
        assert "description:" in content

    def test_set_ai_client(self):
        gen = SkillGenerator()
        assert gen.ai_client is None

        class DummyClient:
            def chat(self, *args, **kwargs):
                return "---\nname: dummy\n---\n"

        gen.set_ai_client(DummyClient())
        assert gen.ai_client is not None

    def test_global_instance(self):
        gen = get_skill_generator()
        assert isinstance(gen, SkillGenerator)

    def test_ai_generation_fallback_without_client(self):
        """没有 AI 客户端时 use_ai=True 应降级为简单生成"""
        gen = SkillGenerator()
        result = gen.generate_skill_md("# Fallback\n\nSimple content", use_ai=True)
        assert result.startswith("---")
