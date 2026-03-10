"""Markdown 编辑器模块

使用 QWebEngine 加载 EasyMDE 编辑器。
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl, Signal, Slot, QObject
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget, QVBoxLayout

# EasyMDE HTML 模板
EDITOR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Editor</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css">
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
    </style>
</head>
<body>
    <textarea id="editor"></textarea>
    <script src="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js"></script>
    <script>
        var editor;
        var bridge;

        function initEditor() {{
            editor = new EasyMDE({{
                element: document.getElementById('editor'),
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

        # WebEngine 视图
        self.web_view = QWebEngineView()
        self.web_view.page().setWebChannel(self._channel)

        layout.addWidget(self.web_view)

        # 加载编辑器
        self._load_editor()

    def _load_editor(self) -> None:
        """加载编辑器"""
        from ..core.config import get_config

        config = get_config()
        font_size = config.editor_font_size

        html = EDITOR_HTML.format(font_size=font_size)
        self.web_view.setHtml(html, QUrl("about:blank"))

    def _connect_signals(self) -> None:
        """连接信号"""
        self._bridge.content_changed.connect(self._on_content_changed)

    @Slot(str)
    def _on_content_changed(self, content: str) -> None:
        """内容改变"""
        self.content_changed.emit()

    def set_content(self, content: str, title: str = "") -> None:
        """设置编辑器内容"""
        js = f"setContent({repr(content)});"
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