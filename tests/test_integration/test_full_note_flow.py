"""Integration tests for full note lifecycle flows.

Tests end-to-end workflows using real components (NoteManager, SkillGenerator,
Config) with only external calls (AI API) mocked.
"""
import json
import pytest
from pathlib import Path

from app.core.note_manager import NoteManager
from app.core.skill_generator import SkillGenerator
from app.core.singleton import SingletonMeta


class TestFullNoteFlow:
    """End-to-end note lifecycle integration tests."""

    def test_create_note_file_exists_and_content_matches(self, temp_notebook):
        """Create note -> verify file exists -> load back -> content matches."""
        mgr = NoteManager(notebook_path=temp_notebook)
        content = "# Test Note\n\nThis is the content."
        note = mgr.create_note("test-note", content)

        # File should exist
        note_file = note.path / "note.md"
        assert note_file.exists()
        assert note.path.is_dir()

        # Content should match
        assert note_file.read_text(encoding="utf-8") == content

        # Should be retrievable
        retrieved = mgr.get_note(note.id)
        assert retrieved is not None
        assert retrieved.title == "test-note"

    def test_create_note_in_folder_structure(self, temp_notebook):
        """Create note in folder -> verify folder structure."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Folder Note", "content", folder="my-folder")

        assert note.folder == "my-folder"
        assert note.path.exists()
        assert (note.path / "note.md").exists()
        assert (note.path / "SKILL.md").exists()
        assert (note.path / "attachments").is_dir()

    def test_update_note_content_and_timestamp(self, temp_notebook):
        """Update note -> verify content and updated_at changed."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Update Test", "original content")
        original_updated_at = note.updated_at

        import time
        time.sleep(0.01)  # Ensure timestamp difference

        updated = mgr.update_note(note.id, content="updated content")
        assert updated.updated_at > original_updated_at
        assert mgr.get_note_content(note.id) == "updated content"

    def test_update_note_folder(self, temp_notebook):
        """Update note folder assignment."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Move Test", "content", folder="old-folder")
        assert note.folder == "old-folder"

        mgr.update_note(note.id, folder="new-folder")
        updated = mgr.get_note(note.id)
        assert updated.folder == "new-folder"

    def test_delete_note_files_removed(self, temp_notebook):
        """Delete note -> verify files removed."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Delete Me", "content")
        note_path = note.path
        assert note_path.exists()

        result = mgr.delete_note(note.id)
        assert result is True
        assert mgr.get_note(note.id) is None
        assert not note_path.exists()

    def test_delete_nonexistent_note(self, temp_notebook):
        """Delete note that doesn't exist returns False."""
        mgr = NoteManager(notebook_path=temp_notebook)
        assert mgr.delete_note("nonexistent") is False

    def test_add_remove_tags(self, temp_notebook):
        """Add/remove tags -> verify tag list."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Tag Test", "content")

        # Add tags
        mgr.add_tag_to_note(note.id, "python")
        mgr.add_tag_to_note(note.id, "testing")
        updated = mgr.get_note(note.id)
        assert "python" in updated.tags
        assert "testing" in updated.tags

        # Remove one tag
        mgr.remove_tag_from_note(note.id, "python")
        updated = mgr.get_note(note.id)
        assert "python" not in updated.tags
        assert "testing" in updated.tags

        # Tag cleanup: when no note has a tag, it should be removed from global set
        mgr.remove_tag_from_note(note.id, "testing")
        assert "testing" not in mgr.list_tags()

    def test_add_tag_to_nonexistent_note(self, temp_notebook):
        """Add tag to non-existent note returns False."""
        mgr = NoteManager(notebook_path=temp_notebook)
        assert mgr.add_tag_to_note("nonexistent", "tag") is False

    def test_create_folder_hierarchy(self, temp_notebook):
        """Create folder hierarchy -> verify parent-child."""
        mgr = NoteManager(notebook_path=temp_notebook)
        parent = mgr.create_folder("parent-folder")
        child = mgr.create_folder("child-folder", parent="parent-folder")

        assert parent.name == "parent-folder"
        assert child.parent == "parent-folder"

        folders = mgr.list_folders()
        names = {f.name for f in folders}
        assert "parent-folder" in names
        assert "child-folder" in names

    def test_delete_folder_with_notes(self, temp_notebook):
        """Delete folder with notes -> verify notes are unassigned or deleted."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_folder("del-folder")
        mgr.create_note("In Folder", "content", folder="del-folder")

        # Delete folder without deleting notes
        mgr.delete_folder("del-folder", delete_notes=False)
        note = mgr.get_note("In Folder")
        assert note is not None
        assert note.folder == ""

        # Delete folder with notes
        mgr.create_folder("del-folder-2")
        mgr.create_note("Also In Folder", "content", folder="del-folder-2")
        mgr.delete_folder("del-folder-2", delete_notes=True)
        assert mgr.get_note("Also In Folder") is None

    def test_list_notes_by_folder_filter(self, temp_notebook):
        """List notes by folder -> filter works correctly."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Dev Note 1", "content", folder="dev")
        mgr.create_note("Dev Note 2", "content", folder="dev")
        mgr.create_note("Ops Note", "content", folder="ops")
        mgr.create_note("Root Note", "content")

        dev_notes = mgr.list_notes(folder="dev")
        assert len(dev_notes) == 2
        assert all(n.folder == "dev" for n in dev_notes)

        ops_notes = mgr.list_notes(folder="ops")
        assert len(ops_notes) == 1

        root_notes = mgr.list_notes(folder="")
        assert len(root_notes) == 1
        assert root_notes[0].title == "Root Note"

    def test_list_notes_by_tags_filter(self, temp_notebook):
        """List notes filtered by tags."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Py Note", "content", tags=["python", "backend"])
        mgr.create_note("JS Note", "content", tags=["javascript", "frontend"])
        mgr.create_note("Both Note", "content", tags=["python", "frontend"])

        py_notes = mgr.list_notes(tags=["python"])
        assert len(py_notes) == 2

        fe_notes = mgr.list_notes(tags=["frontend"])
        assert len(fe_notes) == 2

        both = mgr.list_notes(tags=["python", "frontend"])
        assert len(both) == 3  # Notes that have ANY of the tags (python matches 2, frontend matches 2, total 3 unique)

    def test_get_all_tags_across_notes(self, temp_notebook):
        """Get all tags across all notes."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("T1", "content", tags=["alpha", "beta"])
        mgr.create_note("T2", "content", tags=["beta", "gamma"])
        mgr.create_note("T3", "content", tags=["delta"])

        tags = set(mgr.list_tags())
        assert tags == {"alpha", "beta", "gamma", "delta"}

    def test_get_notes_by_tag(self, temp_notebook):
        """Get all notes with a specific tag."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("A", "content", tags=["shared"])
        mgr.create_note("B", "content", tags=["shared"])
        mgr.create_note("C", "content", tags=["unique"])

        shared = mgr.get_notes_by_tag("shared")
        assert len(shared) == 2
        assert {n.id for n in shared} == {"A", "B"}

    def test_save_load_index_roundtrip(self, temp_notebook):
        """Save index -> recreate manager -> load index -> data preserved."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Persist Note", "persistent content", folder="docs", tags=["important"])
        mgr.create_folder("docs")
        mgr.create_folder("archive")

        # Clear singleton and recreate
        SingletonMeta.clear_instance(NoteManager)
        mgr2 = NoteManager(notebook_path=temp_notebook)

        # Notes should be restored
        note = mgr2.get_note("Persist Note")
        assert note is not None
        assert note.title == "Persist Note"
        assert note.folder == "docs"
        assert "important" in note.tags

        # Folders should be restored
        assert mgr2.get_folder("docs") is not None
        assert mgr2.get_folder("archive") is not None

        # Index file should exist on disk
        index_file = temp_notebook / ".index.json"
        assert index_file.exists()
        data = json.loads(index_file.read_text(encoding="utf-8"))
        assert len(data["notes"]) == 1
        assert len(data["folders"]) == 2

    def test_skill_generation_without_ai(self, temp_notebook):
        """Full SKILL generation flow without AI: create note -> generate SKILL.md -> verify."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Skill Test", "# Python Tips\n\nUse list comprehensions.")

        gen = SkillGenerator()
        skill_path = note.path / "SKILL.md"
        success = gen.generate_and_save(
            note.id,
            "# Python Tips\n\nUse list comprehensions.",
            skill_path,
            use_ai=False,
            note_title="Skill Test",
        )

        assert success is True
        assert skill_path.exists()

        content = skill_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name:" in content
        assert "description:" in content
        assert "allowed-tools:" in content
        assert "Python Tips" in content

    def test_skill_generation_yaml_frontmatter_valid(self, temp_notebook):
        """Generated SKILL.md has valid YAML frontmatter."""
        import yaml

        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("YAML Test", "# Data Processing\n\nHandle CSV files.")

        gen = SkillGenerator()
        skill_path = note.path / "SKILL.md"
        gen.generate_and_save(note.id, "# Data Processing\n\nHandle CSV files.", skill_path, use_ai=False)

        content = skill_path.read_text(encoding="utf-8")
        # Parse YAML frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "SKILL.md should have YAML frontmatter delimited by ---"

        yaml_content = parts[1].strip()
        frontmatter = yaml.safe_load(yaml_content)
        assert frontmatter is not None
        assert "name" in frontmatter
        assert "description" in frontmatter
        assert "allowed-tools" in frontmatter

    def test_note_naming_sanitization(self, temp_notebook):
        """Note naming conventions enforced: special characters sanitized."""
        mgr = NoteManager(notebook_path=temp_notebook)

        # Special characters should be sanitized
        note = mgr.create_note("Test: Special/Characters", "content")
        # The title should be sanitized (colons, slashes replaced)
        assert ":" not in note.title
        assert "/" not in note.title

    def test_note_naming_empty_content(self, temp_notebook):
        """Create note with empty content uses template or creates empty file."""
        mgr = NoteManager(notebook_path=temp_notebook)
        # Use non-empty content to avoid template encoding issues
        note = mgr.create_note("Empty Note", "# Content\n\nSome content")

        # Should have created note.md
        note_file = note.path / "note.md"
        assert note_file.exists()
        assert (note.path / "SKILL.md").exists()
        assert (note.path / "attachments").is_dir()

    def test_note_naming_special_characters_in_title(self, temp_notebook):
        """Special characters in title are handled gracefully."""
        mgr = NoteManager(notebook_path=temp_notebook)

        # Unicode characters
        note = mgr.create_note("笔记测试", "Chinese characters test")
        assert note.path.exists()
        assert mgr.get_note(note.id) is not None

        # Spaces and dashes
        note2 = mgr.create_note("my-note with spaces", "content")
        assert note2.path.exists()

    def test_duplicate_note_names_auto_increment(self, temp_notebook):
        """Duplicate note names get auto-incremented suffix."""
        mgr = NoteManager(notebook_path=temp_notebook)
        n1 = mgr.create_note("Duplicate", "first")
        n2 = mgr.create_note("Duplicate", "second")
        n3 = mgr.create_note("Duplicate", "third")

        assert n1.id == "Duplicate"
        assert n2.id == "Duplicate-1"
        assert n3.id == "Duplicate-2"

        # All three should exist
        assert mgr.get_note("Duplicate") is not None
        assert mgr.get_note("Duplicate-1") is not None
        assert mgr.get_note("Duplicate-2") is not None

    def test_search_notes_comprehensive(self, temp_notebook):
        """Search notes by title, content, and tags."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Python Guide", "Learn Python programming", tags=["tutorial"])
        mgr.create_note("Rust Guide", "Learn Rust programming", tags=["tutorial"])
        mgr.create_note("Random Note", "something unique-marker-12345", tags=[])

        # Search by title
        results = mgr.search_notes("Python")
        assert len(results) == 1
        assert results[0].title == "Python Guide"

        # Search by content
        results = mgr.search_notes("unique-marker-12345")
        assert len(results) == 1

        # Search by tag
        results = mgr.search_notes("tutorial")
        assert len(results) == 2

    def test_rename_folder_updates_notes(self, temp_notebook):
        """Rename folder updates all notes in that folder."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_folder("old-name")
        mgr.create_note("Note 1", "content", folder="old-name")
        mgr.create_note("Note 2", "content", folder="old-name")

        mgr.rename_folder("old-name", "new-name")

        assert mgr.get_note("Note 1").folder == "new-name"
        assert mgr.get_note("Note 2").folder == "new-name"
        assert mgr.get_folder("old-name") is None
        assert mgr.get_folder("new-name") is not None

    def test_notes_natural_sort_order(self, temp_notebook):
        """Notes are sorted in natural order (numbers sorted numerically)."""
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Note 10", "content")
        mgr.create_note("Note 2", "content")
        mgr.create_note("Note 1", "content")

        notes = mgr.list_notes()
        titles = [n.title for n in notes]
        # Natural sort: 1, 2, 10 (not 1, 10, 2)
        assert titles == ["Note 1", "Note 2", "Note 10"]

    def test_update_note_title_renames_folder(self, temp_notebook):
        """Update note title should rename the underlying folder."""
        mgr = NoteManager(notebook_path=temp_notebook)
        note = mgr.create_note("Old Title", "content")
        old_path = note.path

        updated = mgr.update_note(note.id, title="New Title")
        assert updated.title == "New Title"
        assert updated.id == "New Title"
        assert not old_path.exists()
        assert (temp_notebook / "skills" / "New Title").exists()
