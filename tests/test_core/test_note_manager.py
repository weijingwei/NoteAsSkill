"""NoteManager 测试"""
import pytest
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

    def test_delete_folder_with_notes_no_delete(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_folder("f1")
        mgr.create_note("N1", "content", folder="f1")
        mgr.delete_folder("f1", delete_notes=False)
        note = mgr.get_note("N1")
        assert note is not None
        assert note.folder == ""

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

    def test_add_tag_to_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("Tag Note", "content")
        assert mgr.add_tag_to_note("Tag Note", "python") is True
        note = mgr.get_note("Tag Note")
        assert "python" in note.tags

    def test_remove_tag_from_note(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("RT", "content", tags=["keep", "remove"])
        assert mgr.remove_tag_from_note("RT", "remove") is True
        note = mgr.get_note("RT")
        assert "remove" not in note.tags
        assert "keep" in note.tags

    def test_list_tags(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("T1", "content", tags=["tag-a"])
        mgr.create_note("T2", "content", tags=["tag-b"])
        tags = mgr.list_tags()
        assert "tag-a" in tags
        assert "tag-b" in tags

    def test_get_notes_by_tag(self, temp_notebook):
        mgr = NoteManager(notebook_path=temp_notebook)
        mgr.create_note("A", "content", tags=["common"])
        mgr.create_note("B", "content", tags=["common"])
        mgr.create_note("C", "content", tags=["other"])
        notes = mgr.get_notes_by_tag("common")
        assert len(notes) == 2

    def test_duplicate_note_name(self, temp_notebook):
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
        folder = Folder(name="test", path=temp_notebook / "skills" / "test")
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
