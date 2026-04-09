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
        valid, msg = validate_note_name("\U0001f4dd My Note")
        assert valid is True

    def test_too_long_name(self):
        long_name = "a" * 250
        valid, msg = validate_note_name(long_name)
        assert valid is False
        assert "不能" in msg

    def test_trailing_dot(self):
        valid, msg = validate_note_name("note.")
        assert valid is False
        assert "点号" in msg

    def test_control_char(self):
        valid, msg = validate_note_name("note\x00name")
        assert valid is False
        assert "控制" in msg


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

    def test_replace_invalid_chars(self):
        result = sanitize_note_name('file:name/test')
        assert ":" not in result
        assert "/" not in result


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

    def test_skip_existing_suffixes(self):
        result = generate_unique_name("my-note", {"my-note", "my-note-1", "my-note-2"})
        assert result == "my-note-3"


class TestNameConversions:
    def test_folder_name(self):
        result = name_to_folder_name("My Note")
        assert "My" in result

    def test_skill_name_to_kebab(self):
        result = name_to_skill_name("My Note Title")
        assert result == "my-note-title"

    def test_skill_name_special_chars(self):
        result = name_to_skill_name("My Note (2024)")
        assert "(" not in result
        assert ")" not in result
        assert "-" in result

    def test_skill_name_chinese(self):
        result = name_to_skill_name("测试笔记")
        assert len(result) > 0
