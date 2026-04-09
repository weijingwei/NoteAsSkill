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

    def test_with_message(self):
        result = CommandResult(success=False, message="error occurred")
        assert result.success is False
        assert result.message == "error occurred"

    def test_with_data(self):
        result = CommandResult(success=True, data={"key": "value"})
        assert result.data == {"key": "value"}


class TestCommandType:
    def test_all_command_types_exist(self):
        assert CommandType.UPDATE_FOLDER_SKILL is not None
        assert CommandType.UPDATE_NOTE is not None
        assert CommandType.GENERATE_SKILL is not None
        assert CommandType.MOVE_NOTE is not None
        assert CommandType.DELETE_NOTE is not None


class TestConcreteCommand:
    def test_update_folder_skill_command_properties(self):
        cmd = UpdateFolderSkillCommand("my-folder", immediate=True)
        assert cmd.type == CommandType.UPDATE_FOLDER_SKILL
        assert cmd.folder_name == "my-folder"
        assert cmd.immediate is True
        assert cmd.executed is False

    def test_update_folder_skill_command_defaults(self):
        cmd = UpdateFolderSkillCommand("my-folder")
        assert cmd.immediate is False

    def test_generate_skill_command_properties(self):
        cmd = GenerateSkillCommand("note-1", "content", "/path/to/SKILL.md", "My Note")
        assert cmd.type == CommandType.GENERATE_SKILL
        assert cmd.note_id == "note-1"
        assert cmd.note_content == "content"
        assert cmd.note_title == "My Note"
        assert cmd.executed is False

    def test_generate_skill_command_default_title(self):
        cmd = GenerateSkillCommand("note-1", "content", "/path/to/SKILL.md")
        assert cmd.note_title == ""


class _DummyCommand(Command):
    """测试用的简单命令实现"""
    def __init__(self, command_type=CommandType.UPDATE_NOTE):
        super().__init__(command_type)
        self.execute_called = False
        self.undo_called = False

    def execute(self):
        self.execute_called = True
        self._executed = True
        self._result = CommandResult(True, "done")
        return self._result

    def undo(self):
        self.undo_called = True
        return CommandResult(True, "undone")


class _FailingCommand(Command):
    """执行会失败的命令"""
    def __init__(self):
        super().__init__(CommandType.UPDATE_NOTE)

    def execute(self):
        self._executed = False
        self._result = CommandResult(False, "failed")
        return self._result

    def undo(self):
        return CommandResult(True, "undone")


class TestCommandQueue:
    def test_add_and_execute(self):
        queue = CommandQueue()
        cmd = _DummyCommand()
        queue.add(cmd)
        assert queue.pending_count == 1

        result = queue.execute_next()
        assert result.success is True
        assert queue.pending_count == 0
        assert cmd.execute_called is True

    def test_execute_all(self):
        queue = CommandQueue()
        queue.add(_DummyCommand())
        queue.add(_DummyCommand())
        queue.add(_DummyCommand())

        results = queue.execute_all()
        assert len(results) == 3
        assert not queue.has_pending

    def test_clear_queue(self):
        queue = CommandQueue()
        queue.add(_DummyCommand())
        queue.add(_DummyCommand())
        queue.clear()
        assert queue.pending_count == 0

    def test_undo_last(self):
        queue = CommandQueue()
        cmd = _DummyCommand()
        queue.add(cmd)
        queue.execute_next()
        queue.undo_last()
        assert cmd.undo_called is True

    def test_undo_with_no_history(self):
        queue = CommandQueue()
        assert queue.undo_last() is None

    def test_execute_empty_queue(self):
        queue = CommandQueue()
        assert queue.execute_next() is None

    def test_max_size(self):
        queue = CommandQueue(max_size=2)
        queue.add(_DummyCommand())
        queue.add(_DummyCommand())
        queue.add(_DummyCommand())  # 超出限制，应丢弃最老的
        assert queue.pending_count <= 2

    def test_history_count(self):
        queue = CommandQueue()
        cmd = _DummyCommand()
        queue.add(cmd)
        queue.execute_next()
        assert queue.history_count == 1

    def test_history_empty_by_default(self):
        queue = CommandQueue()
        assert queue.history_count == 0

    def test_pending_by_default(self):
        queue = CommandQueue()
        assert queue.pending_count == 0
        assert not queue.has_pending

    def test_failed_command_not_added_to_history(self):
        queue = CommandQueue()
        queue.add(_FailingCommand())
        queue.execute_next()
        assert queue.history_count == 0

    def test_execute_all_on_empty_queue(self):
        queue = CommandQueue()
        results = queue.execute_all()
        assert results == []

    def test_undo_multiple_commands(self):
        queue = CommandQueue()
        cmd1 = _DummyCommand()
        cmd2 = _DummyCommand()
        queue.add(cmd1)
        queue.add(cmd2)
        queue.execute_all()
        assert queue.history_count == 2

        queue.undo_last()
        assert queue.history_count == 1
        assert cmd2.undo_called is True

        queue.undo_last()
        assert queue.history_count == 0
        assert cmd1.undo_called is True
