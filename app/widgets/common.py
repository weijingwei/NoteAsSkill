"""公共 UI 组件模块

提供可复用的 UI 组件，避免代码重复。
"""

from pathlib import Path

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPolygon
from PySide6.QtWidgets import QComboBox


class NoBorderComboBox(QComboBox):
    """无边框下拉框 - 解决 Windows 平台下拉列表黑边问题，使用 QPainter 绘制下拉箭头"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def showPopup(self) -> None:
        """显示下拉列表时移除容器边框"""
        super().showPopup()

        view = self.view()
        if view:
            view.window().setStyleSheet("border: none; background-color: #FFFEF9;")

    def paintEvent(self, event) -> None:
        """自定义绘制 - 绘制无边框背景和下拉箭头"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFEF9"))
        painter.drawRect(rect)

        arrow_x = self.width() - 20
        arrow_y = self.height() // 2
        arrow_size = 6

        painter.setPen(QPen(QColor("#8B5A2B"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        points = [
            QPoint(arrow_x - arrow_size, arrow_y - 2),
            QPoint(arrow_x, arrow_y + 4),
            QPoint(arrow_x + arrow_size, arrow_y - 2),
        ]

        painter.drawPolygon(QPolygon(points))

        painter.setPen(QPen(QColor("#E8DFD5"), 1))
        painter.drawLine(rect.right(), rect.top() + 4, rect.right(), rect.bottom() - 4)

        painter.end()


def load_icon(name: str) -> QIcon:
    """加载 SVG 图标

    Args:
        name: 图标名称（不带扩展名）

    Returns:
        QIcon 对象，如果文件不存在则返回空图标
    """
    icon_path = Path(__file__).parent.parent.parent / "assets" / f"{name}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class IconManager:
    """图标管理器 - 缓存已加载的图标"""

    _instance: "IconManager | None" = None
    _icons: dict[str, QIcon] = {}

    def __new__(cls) -> "IconManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self, name: str) -> QIcon:
        """获取图标（带缓存）

        Args:
            name: 图标名称

        Returns:
            QIcon 对象
        """
        if name not in self._icons:
            self._icons[name] = load_icon(name)
        return self._icons[name]

    def preload(self, names: list[str]) -> None:
        """预加载图标

        Args:
            names: 图标名称列表
        """
        for name in names:
            self.get(name)


def get_icon_manager() -> IconManager:
    """获取图标管理器实例"""
    return IconManager()
