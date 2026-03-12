"""Markdown 编辑器模块

使用 QWebEngine 加载 EasyMDE 编辑器。
"""

import os
import logging
from typing import Any

from PySide6.QtCore import QUrl, Signal, Slot, QObject, Qt, QEvent, QTimer
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
        html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .EasyMDEContainer {{
            height: 100%;
            display: flex;
            flex-direction: column;
        }}
        .CodeMirror {{
            height: auto !important;
            flex: 1;
            border: none !important;
            font-size: {font_size}px;
        }}
        .editor-preview {{
            font-size: {font_size}px;
        }}
        .CodeMirror-scroll {{
            overflow-y: auto !important;
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
            flex-shrink: 0;
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
                    'undo', 'redo', '|',
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
        # 定时器用于强制重置 zoomFactor
        self._zoom_reset_timer = QTimer(self)
        self._zoom_reset_timer.timeout.connect(self._force_reset_zoom)

    def _force_reset_zoom(self) -> None:
        """强制重置 zoomFactor 为 1.0"""
        if self.zoomFactor() != 1.0:
            self.setZoomFactor(1.0)
        self._zoom_reset_timer.stop()

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
        # 立即重置 zoomFactor 并启动定时器确保重置
        self.setZoomFactor(1.0)
        self._zoom_reset_timer.start(50)  # 50ms 后再次检查

    def get_font_size(self) -> int:
        """获取当前字体大小"""
        return self._current_font_size

    def wheelEvent(self, event: QWheelEvent) -> None:
        """处理滚轮事件，拦截 Ctrl + 滚动缩放字体"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # 计算新的字体大小
            delta = event.angleDelta().y()
            if delta > 0:
                new_size = self._current_font_size + self.FONT_SIZE_STEP
            else:
                new_size = self._current_font_size - self.FONT_SIZE_STEP

            # 限制范围并应用
            if self.MIN_FONT_SIZE <= new_size <= self.MAX_FONT_SIZE:
                self.set_font_size(new_size)

            # 接受事件，阻止传递到 Chromium
            event.accept()
            return

        # 非 Ctrl + 滚动，使用默认行为
        super().wheelEvent(event)


class Editor(QWidget):
    """Markdown 编辑器组件"""

    content_changed = Signal()
    save_requested = Signal()

    def __init__(self):
        super().__init__()

        self._bridge = EditorBridge()
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)

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