"""Worker 线程基类模块

提供可复用的 QThread 基类，封装通用的线程管理逻辑。
"""

from typing import Any

from PySide6.QtCore import QThread, Signal


class BaseWorker(QThread):
    """Worker 线程基类

    封装了通用的线程执行逻辑，包括：
    - 异常捕获
    - 结果信号发射
    - 线程清理

    子类应重写 do_work() 方法。
    """

    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def run(self) -> None:
        """线程入口 - 执行工作并处理异常"""
        try:
            result = self.do_work()
            if not self._is_cancelled:
                self.finished.emit(True, result or "")
        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(False, str(e))

    def do_work(self) -> str:
        """执行实际工作

        子类应重写此方法。

        Returns:
            工作结果消息
        """
        return ""

    def cancel(self) -> None:
        """取消工作"""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._is_cancelled

    def report_progress(self, message: str) -> None:
        """报告进度

        Args:
            message: 进度消息
        """
        self.progress.emit(message)


class WorkerManager:
    """Worker 线程管理器

    统一管理 Worker 线程的生命周期，包括：
    - 创建
    - 启动
    - 清理
    """

    def __init__(self):
        self._workers: dict[str, BaseWorker] = {}

    def start_worker(self, name: str, worker: BaseWorker, on_finished: callable = None) -> None:
        """启动一个 Worker

        Args:
            name: Worker 名称（用于标识）
            worker: Worker 实例
            on_finished: 完成回调函数
        """
        if name in self._workers:
            old_worker = self._workers[name]
            if old_worker.isRunning():
                old_worker.cancel()
                old_worker.wait(2000)
                old_worker.deleteLater()

        self._workers[name] = worker

        if on_finished:
            worker.finished.connect(on_finished)

        worker.finished.connect(lambda: self._on_worker_finished(name))
        worker.start()

    def _on_worker_finished(self, name: str) -> None:
        """Worker 完成时的处理"""
        if name in self._workers:
            worker = self._workers[name]
            worker.deleteLater()
            del self._workers[name]

    def cancel_worker(self, name: str) -> bool:
        """取消指定的 Worker

        Args:
            name: Worker 名称

        Returns:
            是否成功取消
        """
        if name in self._workers:
            worker = self._workers[name]
            if worker.isRunning():
                worker.cancel()
                return worker.wait(2000)
        return False

    def cancel_all(self) -> None:
        """取消所有 Worker"""
        for name in list(self._workers.keys()):
            self.cancel_worker(name)

    def wait_all(self, timeout: int = 5000) -> None:
        """等待所有 Worker 完成

        Args:
            timeout: 超时时间（毫秒）
        """
        for worker in self._workers.values():
            if worker.isRunning():
                worker.wait(timeout)


_worker_manager: WorkerManager | None = None


def get_worker_manager() -> WorkerManager:
    """获取全局 Worker 管理器实例"""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager()
    return _worker_manager
