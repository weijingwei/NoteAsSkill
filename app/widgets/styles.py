"""样式常量和样式生成函数模块

集中管理 UI 样式，避免样式字符串重复。
"""

from typing import Any

from app.core.system_config import get_system_config_instance


def get_color(name: str, default: str = "#000000") -> str:
    """获取颜色值

    Args:
        name: 颜色名称
        default: 默认值

    Returns:
        颜色值（如 "#D4A574"）
    """
    return get_system_config_instance().color(name, default)


class Colors:
    """颜色常量"""

    PRIMARY = "#D4A574"
    PRIMARY_HOVER = "#C49564"
    PRIMARY_PRESSED = "#B48554"
    BACKGROUND = "#FFFEF9"
    BACKGROUND_ALT = "#FBF7F2"
    BORDER = "#E8DFD5"
    BORDER_FOCUS = "#D4A574"
    TEXT = "#3D3428"
    TEXT_SECONDARY = "#5A4A3A"
    TEXT_MUTED = "#8B7B6B"
    ACCENT = "#8B5A2B"
    SUCCESS = "#2E7D32"
    SUCCESS_BG = "#E8F5E9"
    ERROR = "#C0392B"
    ERROR_BG = "#FDECEA"
    WARNING = "#D4A574"


class FontSizes:
    """字体大小常量"""

    SMALL = 11
    NORMAL = 12
    MEDIUM = 13
    LARGE = 14
    TITLE = 16


class ButtonStyles:
    """按钮样式"""

    PRIMARY = f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {Colors.PRIMARY}, stop:1 {Colors.PRIMARY_HOVER});
            color: {Colors.BACKGROUND};
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {Colors.PRIMARY_HOVER}, stop:1 {Colors.PRIMARY_PRESSED});
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {Colors.PRIMARY_PRESSED}, stop:1 #A47544);
        }}
        QPushButton:disabled {{
            background: #D4C4B0;
            color: #8B7B6B;
        }}
    """

    SECONDARY = f"""
        QPushButton {{
            background-color: {Colors.BACKGROUND_ALT};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BORDER};
        }}
    """

    ICON = """
        QPushButton {
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 0px;
        }
        QPushButton:hover {
            background-color: #E8DFD5;
        }
    """

    ICON_DANGER = """
        QPushButton {
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 0px;
        }
        QPushButton:hover {
            background-color: #FADBD8;
        }
    """


class InputStyles:
    """输入框样式"""

    LINE_EDIT = f"""
        QLineEdit {{
            background-color: {Colors.BACKGROUND};
            border: 2px solid {Colors.BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            color: {Colors.TEXT};
        }}
        QLineEdit:focus {{
            border-color: {Colors.BORDER_FOCUS};
        }}
        QLineEdit:disabled {{
            background-color: {Colors.BORDER};
            color: {Colors.TEXT_MUTED};
        }}
    """

    TEXT_EDIT = f"""
        QTextEdit {{
            background-color: {Colors.BACKGROUND};
            border: 2px solid {Colors.BORDER};
            border-radius: 8px;
            padding: 8px;
            font-size: 13px;
            color: {Colors.TEXT};
        }}
        QTextEdit:focus {{
            border-color: {Colors.BORDER_FOCUS};
        }}
    """

    COMBO_BOX = f"""
        QComboBox {{
            background-color: {Colors.BACKGROUND};
            border: 2px solid {Colors.BORDER};
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 14px;
            color: {Colors.TEXT};
        }}
        QComboBox:focus {{
            border-color: {Colors.BORDER_FOCUS};
        }}
        QComboBox:disabled {{
            background-color: {Colors.BORDER};
            color: {Colors.TEXT_MUTED};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox::down-arrow {{
            image: none;
        }}
    """


class ListStyles:
    """列表样式"""

    LIST_WIDGET = f"""
        QListWidget {{
            background-color: {Colors.BACKGROUND};
            border: 1px solid {Colors.BORDER};
            border-radius: 8px;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 3px;
            border-radius: 4px;
            min-height: 32px;
        }}
        QListWidget::item:hover {{
            background-color: {Colors.BACKGROUND_ALT};
        }}
        QListWidget::item:selected {{
            background-color: #FDF6ED;
            color: {Colors.ACCENT};
        }}
    """


class ScrollBarStyles:
    """滚动条样式"""

    LIGHT = f"""
        QScrollBar:vertical {{
            background: {Colors.BACKGROUND};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.BORDER};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {Colors.PRIMARY};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """


def get_label_style(font_size: int = 14, color: str = Colors.TEXT, bold: bool = False) -> str:
    """生成标签样式

    Args:
        font_size: 字体大小
        color: 文字颜色
        bold: 是否加粗

    Returns:
        样式字符串
    """
    weight = "bold" if bold else "normal"
    return f"font-size: {font_size}px; color: {color}; font-weight: {weight};"


def get_group_box_style(title_color: str = Colors.ACCENT) -> str:
    """生成分组框样式

    Args:
        title_color: 标题颜色

    Returns:
        样式字符串
    """
    return f"""
        QGroupBox {{
            font-weight: 600;
            color: {title_color};
            border: 1px solid {Colors.BORDER};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
        }}
    """
