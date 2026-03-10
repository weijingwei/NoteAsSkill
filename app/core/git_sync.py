"""Git 同步模块

负责将用户笔记内容同步到指定的 git 仓库。
"""

import subprocess
from pathlib import Path
from typing import Any
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from .config import get_config


class GitSyncWorker(QThread):
    """Git 同步工作线程"""

    progress = Signal(str)       # 进度消息
    success = Signal(str)        # 成功消息
    error = Signal(str)          # 错误消息

    def __init__(self, notebook_path: Path):
        super().__init__()
        self.notebook_path = notebook_path

    def run(self) -> None:
        """执行同步"""
        config = get_config()

        if not config.git_enabled:
            self.error.emit("Git 同步未启用")
            return

        if not config.git_remote_url:
            self.error.emit("未配置 Git 远程仓库地址")
            return

        try:
            # 1. 检查是否已初始化 git
            git_dir = self.notebook_path / ".git"
            if not git_dir.exists():
                self.progress.emit("正在初始化 Git 仓库...")
                self._run_git("init")

            # 2. 配置远程仓库
            self.progress.emit("正在配置远程仓库...")
            self._run_git("remote", "remove", "origin", check=False)
            self._run_git("remote", "add", "origin", config.git_remote_url)

            # 3. 添加所有更改
            self.progress.emit("正在添加更改...")
            self._run_git("add", "-A")

            # 4. 检查是否有更改
            result = self._run_git("status", "--porcelain", capture=True)
            if not result.strip():
                self.success.emit("没有需要同步的更改")
                return

            # 5. 提交
            self.progress.emit("正在提交...")
            commit_msg = f"{config.git_commit_message} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self._run_git("commit", "-m", commit_msg)

            # 6. 推送
            self.progress.emit("正在推送...")
            branch = config.git_branch
            self._run_git("push", "-u", "origin", branch, check=False)

            # 如果推送失败，尝试先拉取再推送
            result = self._run_git("push", "origin", branch, capture=True, check=False)
            if "failed" in result.lower() or "error" in result.lower():
                self.progress.emit("正在拉取远程更改...")
                self._run_git("pull", "--rebase", "origin", branch, check=False)
                self.progress.emit("正在重新推送...")
                self._run_git("push", "origin", branch)

            self.success.emit("同步完成")

        except Exception as e:
            self.error.emit(f"同步失败: {str(e)}")

    def _run_git(
        self,
        *args: str,
        capture: bool = False,
        check: bool = True
    ) -> str:
        """执行 git 命令

        Args:
            *args: git 命令参数
            capture: 是否捕获输出
            check: 是否检查返回码

        Returns:
            命令输出
        """
        cmd = ["git"] + list(args)

        kwargs = {
            "cwd": str(self.notebook_path),
            "text": True,
        }

        if capture:
            kwargs["capture_output"] = True
        else:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

        result = subprocess.run(cmd, **kwargs)

        if check and result.returncode != 0:
            error_msg = result.stderr if hasattr(result, 'stderr') else "未知错误"
            raise Exception(f"Git 命令失败: {' '.join(args)}\n{error_msg}")

        return result.stdout if capture else ""


class GitSyncManager:
    """Git 同步管理器"""

    def __init__(self):
        """初始化管理器"""
        from .note_manager import get_note_manager
        note_manager = get_note_manager()
        self.notebook_path = note_manager.notebook_path
        self._worker: GitSyncWorker | None = None

    def is_syncing(self) -> bool:
        """是否正在同步"""
        return self._worker is not None and self._worker.isRunning()

    def sync(
        self,
        on_progress: Any = None,
        on_success: Any = None,
        on_error: Any = None
    ) -> bool:
        """开始同步

        Args:
            on_progress: 进度回调
            on_success: 成功回调
            on_error: 错误回调

        Returns:
            是否成功启动同步
        """
        if self.is_syncing():
            return False

        config = get_config()
        if not config.git_enabled or not config.git_remote_url:
            return False

        self._worker = GitSyncWorker(self.notebook_path)

        if on_progress:
            self._worker.progress.connect(on_progress)
        if on_success:
            self._worker.success.connect(on_success)
        if on_error:
            self._worker.error.connect(on_error)

        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        return True

    def _on_finished(self) -> None:
        """同步完成"""
        self._worker = None


# 全局实例
_git_sync_manager: GitSyncManager | None = None


def get_git_sync_manager() -> GitSyncManager:
    """获取全局 Git 同步管理器实例"""
    global _git_sync_manager
    if _git_sync_manager is None:
        _git_sync_manager = GitSyncManager()
    return _git_sync_manager