"""Markdown 编辑器模块

使用 QWebEngine 加载 EasyMDE 编辑器。
"""

import os
import logging
from typing import Any

from PySide6.QtCore import QUrl, Signal, Slot, QObject, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QWheelEvent

logger = logging.getLogger(__name__)

# EasyMDE HTML 模板 - 使用本地静态资源
# 注意：CSS 和 JS 路径会在运行时替换为本地文件路径
EDITOR_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Editor</title>
    <!-- Font Awesome - EasyMDE 工具栏图标依赖 -->
    <link rel="stylesheet" href="{fa_css_path}">
    <link rel="stylesheet" href="{easymde_css_path}">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .EasyMDEContainer {{
            height: 100vh;
        }}
        .CodeMirror {{
            height: 100% !important;
            border: none !important;
            font-size: {font_size}px;
        }}
        .editor-preview {{
            font-size: {font_size}px;
        }}
        /* 确保工具栏可见 - 高度与左右工具栏一致 (36px) */
        .editor-toolbar {{
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            background-color: #FBF7F2 !important;
            border: none !important;
            border-bottom: 1px solid #E8DFD5 !important;
            border-radius: 0 !important;
            padding: 4px 8px !important;
            height: 36px !important;
            min-height: 36px !important;
            box-sizing: border-box !important;
        }}
        .editor-toolbar button {{
            color: #5A4A3A !important;
        }}
        .editor-toolbar button:hover {{
            background-color: #FDF6ED !important;
        }}
        .editor-toolbar button.active {{
            background-color: #FDF6ED !important;
            color: #8B5A2B !important;
        }}
    </style>
</head>
<body>
    <textarea id="mde-editor"></textarea>
    <script src="{easymde_js_path}"></script>
    <script>
        var editor;
        var bridge;

        function initEditor() {{
            editor = new EasyMDE({{
                element: document.getElementById('mde-editor'),
                autofocus: true,
                spellChecker: false,
                status: false,
                toolbar: [
                    'bold', 'italic', 'heading', '|',
                    'quote', 'unordered-list', 'ordered-list', '|',
                    'link', 'image', 'code', '|',
                    'preview', 'side-by-side', 'fullscreen', '|',
                    'guide'
                ],
                previewRender: function(plainText) {{
                    return this.parent.markdown(plainText);
                }}
            }});

            editor.codemirror.on('change', function() {{
                if (bridge) {{
                    bridge.onContentChanged(editor.value());
                }}
            }});
        }}

        function setContent(content) {{
            if (editor) {{
                editor.value(content);
            }}
        }}

        function getContent() {{
            return editor ? editor.value() : '';
        }}

        function setBridge(b) {{
            bridge = b;
        }}

        document.addEventListener('DOMContentLoaded', initEditor);
    </script>
</body>
</html>
"""


class EditorBridge(QObject):
    """Python-JS 桥接类"""

    content_changed = Signal(str)

    def __init__(self):
        super().__init__()

    @Slot(str)
    def onContentChanged(self, content: str) -> None:
        """内容改变回调"""
        self.content_changed.emit(content)


class EditorWebView(QWebEngineView):
    """自定义 WebEngineView，处理 Ctrl + 滚动缩放"""

    # 字体大小范围限制
    MIN_FONT_SIZE = 10
    MAX_FONT_SIZE = 32
    FONT_SIZE_STEP = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_font_size = 14  # 默认字体大小
        # 确保 zoomFactor 始终为 1.0，禁用页面级别的缩放
        self.setZoomFactor(1.0)

    def set_font_size(self, size: int) -> None:
        """设置编辑器字体大小"""
        self._current_font_size = max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, size))
        js = f"""
        if (typeof editor !== 'undefined' && editor) {{
            var cm = document.querySelector('.CodeMirror');
            var preview = document.querySelector('.editor-preview');
            if (cm) cm.style.fontSize = '{self._current_font_size}px';
            if (preview) preview.style.fontSize = '{self._current_font_size}px';
        }}
        """
        self.page().runJavaScript(js)

    def get_font_size(self) -> int:
        """获取当前字体大小"""
        return self._current_font_size

    def wheelEvent(self, event: QWheelEvent) -> None:
        """处理滚轮事件，拦截 Ctrl + 滚动"""
        # 检查是否按下了 Ctrl 键
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # 计算新的字体大小
            delta = event.angleDelta().y()
            if delta > 0:
                # 向上滚动，放大字体
                new_size = self._current_font_size + self.FONT_SIZE_STEP
            else:
                # 向下滚动，缩小字体
                new_size = self._current_font_size - self.FONT_SIZE_STEP

            # 限制范围
            if self.MIN_FONT_SIZE <= new_size <= self.MAX_FONT_SIZE:
                self.set_font_size(new_size)

            # 接受事件，阻止默认的页面缩放行为
            event.accept()
            # 强制确保 zoomFactor 始终为 1.0，防止工具栏被缩放
            # 这是关键：即使 Chromium 内部处理了缩放，我们也立即重置
            if self.zoomFactor() != 1.0:
                self.setZoomFactor(1.0)
            return

        # 非 Ctrl + 滚动，使用默认行为
        super().wheelEvent(event)


class Editor(QWidget):
    """Markdown 编辑器组件"""

    content_changed = Signal()
    save_requested = Signal()

    MAX_HISTORY = 20  # 最大历史记录数

    def __init__(self):
        super().__init__()

        self._bridge = EditorBridge()
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)

        # 编辑历史 - 每个笔记独立的历史记录
        # 结构: {note_id: {"history": [content1, content2, ...], "index": int}}
        self._note_histories: dict[str, dict] = {}
        self._current_note_id: str = ""

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 使用自定义的 WebEngineView，支持 Ctrl + 滚动调整字体大小
        self.web_view = EditorWebView()
        self.web_view.page().setWebChannel(self._channel)

        layout.addWidget(self.web_view)

        # 加载编辑器
        self._load_editor()

    def _load_editor(self) -> None:
        """加载编辑器"""
        from ..core.config import get_config
        from ..core.static_resources import (
            ensure_static_files,
            get_easymde_css_path,
            get_easymde_js_path,
            get_fontawesome_css_path,
            get_static_path
        )

        # 确保静态资源存在
        if not ensure_static_files():
            logger.warning("Failed to ensure static files, editor may not work correctly")

        config = get_config()
        font_size = config.editor_font_size

        # 同步字体大小到自定义 WebView
        self.web_view._current_font_size = font_size

        # 获取本地文件路径
        static_path = get_static_path()
        easymde_css = get_easymde_css_path()
        easymde_js = get_easymde_js_path()
        fa_css = get_fontawesome_css_path()

        # 格式化 HTML 模板
        html = EDITOR_HTML_TEMPLATE.format(
            font_size=font_size,
            fa_css_path=QUrl.fromLocalFile(fa_css).toString(),
            easymde_css_path=QUrl.fromLocalFile(easymde_css).toString(),
            easymde_js_path=QUrl.fromLocalFile(easymde_js).toString()
        )

        # 使用本地文件路径作为 baseUrl，确保相对路径正确解析
        # 注意：baseUrl 需要以 / 结尾才能正确解析相对路径
        base_url = QUrl.fromLocalFile(static_path + os.sep)
        self.web_view.setHtml(html, base_url)

    def _connect_signals(self) -> None:
        """连接信号"""
        self._bridge.content_changed.connect(self._on_content_changed)

    @Slot(str)
    def _on_content_changed(self, content: str) -> None:
        """内容改变"""
        self.content_changed.emit()

    def set_content(self, content: str, title: str = "", note_id: str = "") -> None:
        """设置编辑器内容"""
        # 使用JavaScript安全地设置内容，检查editor是否存在
        js = f"""
        if (typeof editor !== 'undefined' && editor) {{
            editor.value({repr(content)});
        }}
        """
        self.web_view.page().runJavaScript(js)

        if title:
            self.setWindowTitle(title)

        # 切换笔记时初始化历史记录
        if note_id and note_id != self._current_note_id:
            self._current_note_id = note_id
            # 为新笔记创建历史记录
            if note_id not in self._note_histories:
                self._note_histories[note_id] = {
                    "history": [content],
                    "index": 0
                }

    def _add_to_history(self, content: str) -> None:
        """添加内容到当前笔记的历史记录"""
        if not self._current_note_id:
            return

        note_history = self._note_histories.get(self._current_note_id)
        if not note_history:
            return

        history = note_history["history"]
        index = note_history["index"]

        # 如果当前不在历史末尾，截断后面的记录
        if index < len(history) - 1:
            history = history[:index + 1]
            note_history["history"] = history

        # 如果内容与最后一个记录相同，不添加
        if history and history[-1] == content:
            return

        # 添加新记录
        history.append(content)

        # 限制历史记录数量
        if len(history) > self.MAX_HISTORY:
            history.pop(0)
            note_history["index"] = len(history) - 1
        else:
            note_history["index"] = len(history) - 1

    def save_current_to_history(self) -> None:
        """保存当前内容到历史记录（由外部调用）"""
        if not self._current_note_id:
            return

        # 获取当前内容
        def callback(content: str) -> None:
            if content:
                self._add_to_history(content)

        self.web_view.page().runJavaScript("editor ? editor.value() : '';", callback)

    def can_go_back(self) -> bool:
        """是否可以后退"""
        if not self._current_note_id:
            return False
        note_history = self._note_histories.get(self._current_note_id)
        if not note_history:
            return False
        return note_history["index"] > 0

    def can_go_forward(self) -> bool:
        """是否可以前进"""
        if not self._current_note_id:
            return False
        note_history = self._note_histories.get(self._current_note_id)
        if not note_history:
            return False
        return note_history["index"] < len(note_history["history"]) - 1

    def go_back(self) -> str | None:
        """后退，返回内容"""
        if not self.can_go_back():
            return None

        note_history = self._note_histories[self._current_note_id]
        note_history["index"] -= 1
        content = note_history["history"][note_history["index"]]
        return content

    def go_forward(self) -> str | None:
        """前进，返回内容"""
        if not self.can_go_forward():
            return None

        note_history = self._note_histories[self._current_note_id]
        note_history["index"] += 1
        content = note_history["history"][note_history["index"]]
        return content

    def get_content(self) -> str:
        """获取编辑器内容"""
        # 使用同步方式获取 JS 返回值
        from PySide6.QtCore import QEventLoop, QTimer

        result = []

        def callback(content: str) -> None:
            result.append(content if content else "")

        self.web_view.page().runJavaScript("getContent();", callback)

        # 使用事件循环等待回调
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()

        return result[0] if result else ""

    def clear(self) -> None:
        """清空编辑器"""
        self.set_content("")

    def reload_editor(self) -> None:
        """重新加载编辑器"""
        self._load_editor()

    def insert_text(self, text: str) -> None:
        """插入文本"""
        js = f"""
        if (editor) {{
            var cm = editor.codemirror;
            var pos = cm.getCursor();
            cm.replaceRange({repr(text)}, pos);
        }}
        """
        self.web_view.page().runJavaScript(js)

    def insert_image(self, image_path: str, alt_text: str = "") -> None:
        """插入图片"""
        markdown = f"![{alt_text}]({image_path})"
        self.insert_text(markdown)

    def insert_link(self, url: str, text: str = "") -> None:
        """插入链接"""
        if not text:
            text = url
        markdown = f"[{text}]({url})"
        self.insert_text(markdown)