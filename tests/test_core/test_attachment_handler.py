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
        assert path.parent == tmp_path / "attachments"

    def test_create_handler_for_note(self):
        handler = create_attachment_handler_for_note("test-note")
        assert handler is not None
        assert "attachments" in str(handler.attachments_path)
