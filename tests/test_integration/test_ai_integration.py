"""Integration tests for AI-related workflows.

Tests SKILL generation with AI, provider switching, streaming, fallback,
config persistence, and error handling. Uses real components with mocked
external API calls.
"""
import pytest
from pathlib import Path

from app.core.note_manager import NoteManager
from app.core.skill_generator import SkillGenerator, get_skill_generator
from app.core.config import Config
from app.core.singleton import SingletonMeta
from app.ai.factory import AIClientFactory
from app.ai.client import AIClient, ChatResponse


class MockStreamingClient(AIClient):
    """Mock AI client that supports streaming for integration tests."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._call_count = 0

    def chat(self, messages, **kwargs):
        self._call_count += 1
        return """---
name: streaming-test-skill
description: |
  A test skill generated with streaming AI.
allowed-tools: [Read, Write, Bash]
---

## Overview

This is a test SKILL.md generated via streaming AI integration.
"""

    def chat_stream(self, messages, **kwargs):
        """Yields response chunks simulating streaming."""
        chunks = [
            "---\n",
            "name: stream-skill\n",
            "description: |\n",
            "  Streaming generated skill.\n",
            "allowed-tools: [Read, Write, Bash]\n",
            "---\n\n",
            "## Overview\n",
            "\n",
            "Streaming content here.\n",
        ]
        for chunk in chunks:
            yield chunk

    def list_models(self):
        return ["mock-model-v1", "mock-model-v2", "mock-model-v3"]


class MockFailingClient(AIClient):
    """Mock AI client that always raises an exception."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._call_count = 0

    def chat(self, messages, **kwargs):
        self._call_count += 1
        raise RuntimeError("Simulated API failure")

    def chat_stream(self, messages, **kwargs):
        self._call_count += 1
        raise RuntimeError("Simulated streaming failure")

    def list_models(self):
        raise RuntimeError("Cannot list models")


class TestAISkillGeneration:
    """SKILL generation with mock AI client integration tests."""

    def test_skill_generation_with_mock_ai(self, temp_notebook, ai_client_mock):
        """Create note -> AI generate SKILL -> verify SKILL.md with proper content."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("AI Skill Test", "# AI Generated\n\nThis is AI content.")

        gen = SkillGenerator(ai_client=ai_client_mock())
        skill_path = note.path / "SKILL.md"
        success = gen.generate_and_save(
            note.id,
            "# AI Generated\n\nThis is AI content.",
            skill_path,
            use_ai=True,
            note_title="AI Skill Test",
        )

        assert success is True
        assert skill_path.exists()

        content = skill_path.read_text(encoding="utf-8")
        # AI response name gets replaced based on note_title by SkillGenerator
        assert "ai-skill-test" in content.lower()

    def test_skill_md_yaml_frontmatter_with_ai(self, temp_notebook, ai_client_mock):
        """AI-generated SKILL.md has proper YAML frontmatter."""
        import yaml

        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("YAML AI Test", "# Test Content\n\nAI generated content.")

        gen = SkillGenerator(ai_client=ai_client_mock())
        skill_path = note.path / "SKILL.md"
        gen.generate_and_save(note.id, "# Test Content\n\nAI generated content.", skill_path, use_ai=True)

        content = skill_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        assert len(parts) >= 3

        frontmatter = yaml.safe_load(parts[1].strip())
        assert frontmatter is not None
        assert "name" in frontmatter
        assert "description" in frontmatter

    def test_skill_generation_fallback_to_simple_when_ai_fails(self, temp_notebook):
        """When AI client raises exception, fallback to simple generation."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Fallback Test", "# Fallback Content\n\nShould fallback.")

        gen = SkillGenerator(ai_client=MockFailingClient())
        skill_path = note.path / "SKILL.md"

        # Should not raise, should fall back to simple generation
        success = gen.generate_and_save(
            note.id,
            "# Fallback Content\n\nShould fallback.",
            skill_path,
            use_ai=True,
        )

        assert success is True
        content = skill_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name:" in content

    def test_skill_generation_without_ai_client_uses_simple(self, temp_notebook):
        """When no AI client is set, use_ai=True falls back to simple generation."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("No Client Test", "# Simple\n\nNo AI client.")

        gen = SkillGenerator()  # No AI client
        assert gen.ai_client is None

        skill_path = note.path / "SKILL.md"
        success = gen.generate_and_save(note.id, "# Simple\n\nNo AI client.", skill_path, use_ai=True)

        assert success is True
        content = skill_path.read_text(encoding="utf-8")
        assert "---" in content
        assert "name:" in content


class TestAIClientFactoryIntegration:
    """AI client factory integration with Config and SkillGenerator."""

    def test_factory_provider_switching(self, temp_notebook):
        """Switch between AI providers via factory."""
        # Create clients from different providers
        openai_client = AIClientFactory.create("openai", {"api_key": "test-key", "model": "gpt-4"})
        assert "openai" in openai_client.base_url
        assert openai_client.model == "gpt-4"

        anthropic_client = AIClientFactory.create("anthropic", {"api_key": "test-key", "model": "claude-3"})
        assert "anthropic" in anthropic_client.base_url

        ollama_client = AIClientFactory.create("ollama", {"model": "llama3"})
        assert "localhost" in ollama_client.base_url

    def test_factory_with_skill_generator(self, temp_notebook):
        """Create client via factory -> use with SkillGenerator."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Factory Test", "# Factory Content\n\nCreated via factory.")

        # Create a mock client through factory
        AIClientFactory.register(
            "mock-test",
            lambda cfg: MockStreamingClient(**cfg),
            {"api_key": "test", "model": "mock-model"}
        )

        client = AIClientFactory.create("mock-test", {"api_key": "test"})
        gen = SkillGenerator(ai_client=client)

        skill_path = note.path / "SKILL.md"
        success = gen.generate_and_save(
            note.id,
            "# Factory Content\n\nCreated via factory.",
            skill_path,
            use_ai=True,
            note_title="Factory Test",
        )

        assert success is True
        assert skill_path.exists()

        # Cleanup
        AIClientFactory.unregister("mock-test")

    def test_factory_unsupported_provider(self):
        """Requesting unsupported provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported"):
            AIClientFactory.create("nonexistent-provider", {})

    def test_factory_registered_custom_provider(self):
        """Register and use a custom AI provider."""

        class CustomClient(AIClient):
            def chat(self, *args, **kwargs):
                return "---\nname: custom-skill\ndescription: Custom\n---\nBody"

            def chat_stream(self, *args, **kwargs):
                yield "custom"

        AIClientFactory.register(
            "custom-provider",
            lambda cfg: CustomClient(api_key=cfg.get("api_key", "")),
        )

        assert "custom-provider" in AIClientFactory.get_supported_providers()
        assert AIClientFactory.is_provider_supported("custom-provider")

        client = AIClientFactory.create("custom-provider", {"api_key": "key"})
        assert isinstance(client, CustomClient)

        # Cleanup
        AIClientFactory.unregister("custom-provider")
        assert "custom-provider" not in AIClientFactory.get_supported_providers()


class TestAIConfigIntegration:
    """AI provider config changes and persistence."""

    def test_ai_provider_config_changes_persist(self, config_with_temp):
        """Change AI provider config -> save -> reload -> changes persist."""
        config, temp_path = config_with_temp

        # Change provider
        config.ai_provider = "anthropic"
        config.save()

        # Verify current config
        assert config.ai_provider == "anthropic"

        # Reload from disk
        SingletonMeta.clear_instance(Config)
        config2 = Config(config_path=temp_path / ".config.yaml")
        assert config2.ai_provider == "anthropic"

    def test_ai_config_set_and_get(self, config_with_temp):
        """Set AI config for provider -> retrieve it."""
        config, _ = config_with_temp

        config.set_ai_config("openai", {
            "api_key": "new-key",
            "model": "gpt-4-turbo",
            "base_url": "https://custom.api",
        })

        ai_config = config.get_ai_config("openai")
        assert ai_config["api_key"] == "new-key"
        assert ai_config["model"] == "gpt-4-turbo"

    def test_ai_provider_property_roundtrip(self, config_with_temp):
        """AI provider property getter/setter roundtrip."""
        config, _ = config_with_temp

        config.ai_provider = "ollama"
        assert config.ai_provider == "ollama"

        config.ai_provider = "openai"
        assert config.ai_provider == "openai"

    def test_empty_ai_key_config(self, config_with_temp):
        """AI config with empty key still works (validation is client-side)."""
        config, _ = config_with_temp

        config.set_ai_config("openai", {
            "api_key": "",
            "model": "gpt-4",
        })

        ai_config = config.get_ai_config("openai")
        assert ai_config["api_key"] == ""


class TestAIModelListing:
    """Model listing integration."""

    def test_model_listing_via_mock_client(self):
        """List models through mock AI client."""
        client = MockStreamingClient(api_key="test", model="test")
        models = client.list_models()

        assert isinstance(models, list)
        assert len(models) == 3
        assert "mock-model-v1" in models

    def test_factory_builtin_providers_available(self):
        """All three builtin providers are available."""
        providers = AIClientFactory.get_supported_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_client_config_get_set(self):
        """Client get_config/set_config roundtrip."""
        client = MockStreamingClient(api_key="old-key", model="old-model")

        client.set_config({"api_key": "new-key", "model": "new-model"})
        config = client.get_config()

        assert config["api_key"] == "new-key"
        assert config["model"] == "new-model"


class TestAIErrorHandling:
    """Error handling for AI-related operations."""

    def test_empty_ai_key_raises_on_api_call(self, temp_notebook):
        """SKILL generation with empty API key: AI call fails, falls back to simple."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Empty Key Test", "# Content\n\nEmpty key test.")

        # OpenAI client with empty key will fail on API call
        client = AIClientFactory.create("openai", {"api_key": "", "model": "gpt-4"})
        gen = SkillGenerator(ai_client=client)

        skill_path = note.path / "SKILL.md"
        # Should not raise; should fall back to simple generation
        success = gen.generate_and_save(
            note.id,
            "# Content\n\nEmpty key test.",
            skill_path,
            use_ai=True,
        )

        assert success is True
        content = skill_path.read_text(encoding="utf-8")
        # Should have fallen back to simple generation
        assert "---" in content

    def test_failing_ai_client_fallback(self, temp_notebook):
        """When AI client consistently fails, SKILL generation still succeeds via fallback."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Fail Test", "# Important Content\n\nMust generate SKILL.")

        gen = SkillGenerator(ai_client=MockFailingClient())
        skill_path = note.path / "SKILL.md"

        # Should not raise exception
        result = gen.generate_skill_md("# Important Content\n\nMust generate SKILL.", use_ai=True)

        assert result.startswith("---")
        assert "name:" in result

    def test_skill_generator_without_ai_fails_gracefully(self, temp_notebook):
        """SkillGenerator with no AI client and use_ai=True still generates."""
        gen = SkillGenerator()
        result = gen.generate_skill_md("# Test\n\nContent", use_ai=True, note_title="Test")

        assert "---" in result
        assert "name:" in result


class TestAIFullIntegration:
    """Full end-to-end AI integration flows."""

    def test_full_flow_create_note_ai_skill_verify_frontmatter(
        self, temp_notebook, ai_client_mock
    ):
        """Full flow: create note -> AI generate SKILL -> verify SKILL.md content has proper YAML frontmatter."""
        import yaml

        mgr = NoteManager(notebook_path=temp_notebook)

        # Step 1: Create note
        content = """# Machine Learning Pipeline

## Overview

Build and deploy ML pipelines using scikit-learn.

## Steps

1. Data preprocessing
2. Model training
3. Evaluation
4. Deployment
"""
        note = mgr.create_note("ML Pipeline", content)

        # Step 2: Generate SKILL with mock AI
        gen = SkillGenerator(ai_client=ai_client_mock())
        skill_path = note.path / "SKILL.md"
        success = gen.generate_and_save(
            note.id,
            content,
            skill_path,
            use_ai=True,
            note_title="ML Pipeline",
        )

        # Step 3: Verify
        assert success is True
        assert skill_path.exists()

        skill_content = skill_path.read_text(encoding="utf-8")

        # Verify YAML frontmatter
        parts = skill_content.split("---", 2)
        assert len(parts) >= 3

        frontmatter = yaml.safe_load(parts[1].strip())
        assert frontmatter is not None
        assert "name" in frontmatter
        assert "description" in frontmatter
        assert isinstance(frontmatter["description"], str)
        assert len(frontmatter["description"]) > 0

        # Verify body exists
        body = parts[2].strip()
        assert len(body) > 0

    def test_stream_chat_integration(self, temp_notebook):
        """Stream chat integration with SkillGenerator-compatible client."""
        client = MockStreamingClient(api_key="test", model="stream-model")

        # Collect streamed chunks
        chunks = list(client.chat_stream([{"role": "user", "content": "test"}]))
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert "---" in full_response
        assert "name:" in full_response

    def test_multiple_notes_with_ai_skills(self, temp_notebook, ai_client_mock):
        """Create multiple notes and generate SKILL.md for each."""
        mgr = NoteManager(notebook_path=temp_notebook)
        gen = SkillGenerator(ai_client=ai_client_mock())

        notes_data = [
            ("Note Alpha", "# Alpha\n\nAlpha content"),
            ("Note Beta", "# Beta\n\nBeta content"),
            ("Note Gamma", "# Gamma\n\nGamma content"),
        ]

        for title, content in notes_data:
            note = mgr.create_note(title, content)
            skill_path = note.path / "SKILL.md"
            gen.generate_and_save(note.id, content, skill_path, use_ai=True)
            assert skill_path.exists()
            skill_content = skill_path.read_text(encoding="utf-8")
            assert "---" in skill_content

    def test_ai_client_switching_in_skill_generator(self, temp_notebook, ai_client_mock):
        """Switch AI client in SkillGenerator and verify it works."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Switch Test", "# Switch\n\nContent")

        # Start with no AI client
        gen = SkillGenerator()
        skill_path = note.path / "SKILL.md"
        gen.generate_and_save(note.id, "# Switch\n\nContent", skill_path, use_ai=True, note_title="Switch Test")

        content_before = skill_path.read_text(encoding="utf-8")

        # Set mock AI client
        gen.set_ai_client(ai_client_mock())
        gen.generate_and_save(note.id, "# Switch\n\nContent", skill_path, use_ai=True, note_title="Switch Test")

        content_after = skill_path.read_text(encoding="utf-8")

        # Content should be different (AI vs simple generation)
        assert content_before != content_after

    def test_global_skill_generator_with_ai(self, temp_notebook, ai_client_mock):
        """Global SkillGenerator instance works with AI client."""
        import app.core.skill_generator as sg

        # Reset global
        sg._skill_generator = None

        gen = get_skill_generator()
        gen.set_ai_client(ai_client_mock())

        result = gen.generate_skill_md("# Test\n\nGlobal test", use_ai=True, note_title="Global Test")
        assert "---" in result
        assert "name:" in result

        # Reset for other tests
        sg._skill_generator = None
