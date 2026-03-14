"""附件处理模块

负责附件的自动归档、粘贴图片和拖拽上传处理。
"""

import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QImage


class AttachmentHandler:
    """附件处理器"""

    # 支持的图片格式
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}

    # 支持的附件格式
    ATTACHMENT_EXTENSIONS = IMAGE_EXTENSIONS | {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".zip", ".tar", ".gz", ".rar",
        ".txt", ".csv", ".json", ".xml",
    }

    def __init__(self, attachments_path: Path):
        """初始化附件处理器

        Args:
            attachments_path: 附件存储目录
        """
        self.attachments_path = Path(attachments_path)
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """确保附件目录存在"""
        self.attachments_path.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, original_name: str) -> str:
        """生成唯一文件名

        Args:
            original_name: 原始文件名

        Returns:
            唯一文件名
        """
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix.lower()

        # 清理文件名
        stem = re.sub(r"[^\w\u4e00-\u9fff-]", "-", stem)
        stem = re.sub(r"-+", "-", stem).strip("-") or "file"

        # 添加时间戳避免冲突
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_name = f"{stem}-{timestamp}{suffix}"

        # 如果仍然冲突，添加 UUID
        if (self.attachments_path / new_name).exists():
            new_name = f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"

        return new_name

    def is_image(self, filename: str) -> bool:
        """检查是否为图片文件

        Args:
            filename: 文件名

        Returns:
            是否为图片
        """
        return Path(filename).suffix.lower() in self.IMAGE_EXTENSIONS

    def is_supported(self, filename: str) -> bool:
        """检查是否为支持的附件格式

        Args:
            filename: 文件名

        Returns:
            是否支持
        """
        return Path(filename).suffix.lower() in self.ATTACHMENT_EXTENSIONS

    def archive_file(self, source_path: Path, original_name: str | None = None) -> str:
        """归档文件

        Args:
            source_path: 源文件路径
            original_name: 原始文件名（可选）

        Returns:
            归档后的相对路径
        """
        if original_name is None:
            original_name = source_path.name

        new_name = self._generate_filename(original_name)
        dest_path = self.attachments_path / new_name

        shutil.copy2(source_path, dest_path)

        return f"attachments/{new_name}"

    def save_image_from_data(self, image_data: bytes, format_hint: str = "PNG") -> str:
        """从二进制数据保存图片

        Args:
            image_data: 图片二进制数据
            format_hint: 格式提示

        Returns:
            保存后的相对路径
        """
        # 确定扩展名
        ext_map = {"PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg", "GIF": ".gif", "BMP": ".bmp"}
        ext = ext_map.get(format_hint.upper(), ".png")

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"image-{timestamp}{ext}"

        # 如果冲突，添加 UUID
        if (self.attachments_path / filename).exists():
            filename = f"image-{timestamp}-{uuid.uuid4().hex[:8]}{ext}"

        # 保存文件
        dest_path = self.attachments_path / filename
        dest_path.write_bytes(image_data)

        return f"attachments/{filename}"

    def save_image_from_qimage(self, image: QImage) -> str:
        """从 QImage 保存图片

        Args:
            image: QImage 对象

        Returns:
            保存后的相对路径
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"pasted-{timestamp}.png"

        if (self.attachments_path / filename).exists():
            filename = f"pasted-{timestamp}-{uuid.uuid4().hex[:8]}.png"

        dest_path = self.attachments_path / filename
        image.save(str(dest_path), "PNG")

        return f"attachments/{filename}"

    def handle_clipboard_image(self, mime_data: QMimeData) -> str | None:
        """处理剪贴板图片

        Args:
            mime_data: 剪贴板 MIME 数据

        Returns:
            保存后的相对路径，失败返回 None
        """
        # 检查是否有图片数据
        if mime_data.hasImage():
            image = mime_data.imageData()
            if isinstance(image, QImage):
                return self.save_image_from_qimage(image)

        # 检查是否有文件 URL
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                url = urls[0]
                if url.isLocalFile():
                    file_path = Path(url.toLocalFile())
                    if self.is_image(file_path.name):
                        return self.archive_file(file_path)

        return None

    def handle_dropped_files(self, urls: list[QUrl]) -> list[str]:
        """处理拖拽的文件

        Args:
            urls: 文件 URL 列表

        Returns:
            成功归档的文件相对路径列表
        """
        archived_paths = []

        for url in urls:
            if url.isLocalFile():
                file_path = Path(url.toLocalFile())

                if self.is_supported(file_path.name):
                    relative_path = self.archive_file(file_path)
                    archived_paths.append(relative_path)

        return archived_paths

    def update_markdown_links(
        self,
        content: str,
        old_attachments_path: str = "",
    ) -> str:
        """更新 Markdown 中的附件链接

        Args:
            content: Markdown 内容
            old_attachments_path: 旧的附件路径前缀

        Returns:
            更新后的内容
        """
        # 匹配图片链接 ![alt](path)
        def replace_image_link(match: re.Match) -> str:
            alt = match.group(1)
            path = match.group(2)

            # 如果是本地文件且不在 attachments 目录
            if not path.startswith("attachments/") and not path.startswith("http"):
                # 检查文件是否存在
                source = Path(path)
                if source.exists() and self.is_supported(path):
                    # 归档文件
                    new_path = self.archive_file(source, source.name)
                    return f"![{alt}]({new_path})"

            return match.group(0)

        # 匹配普通链接 [text](path)
        def replace_link(match: re.Match) -> str:
            text = match.group(1)
            path = match.group(2)

            # 跳过图片链接（已处理）和外部链接
            if path.startswith("attachments/") or path.startswith("http"):
                return match.group(0)

            # 检查是否为支持的附件
            source = Path(path)
            if source.exists() and self.is_supported(path):
                new_path = self.archive_file(source, source.name)
                return f"[{text}]({new_path})"

            return match.group(0)

        # 先处理图片链接
        content = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_image_link, content)

        return content

    def generate_markdown_image(self, relative_path: str, alt_text: str = "") -> str:
        """生成 Markdown 图片链接

        Args:
            relative_path: 相对路径
            alt_text: 替代文本

        Returns:
            Markdown 图片语法
        """
        return f"![{alt_text}]({relative_path})"

    def generate_markdown_link(self, relative_path: str, text: str = "") -> str:
        """生成 Markdown 链接

        Args:
            relative_path: 相对路径
            text: 链接文本

        Returns:
            Markdown 链接语法
        """
        if not text:
            text = Path(relative_path).stem
        return f"[{text}]({relative_path})"

    def list_attachments(self) -> list[dict[str, Any]]:
        """列出所有附件

        Returns:
            附件信息列表
        """
        attachments = []

        if not self.attachments_path.exists():
            return attachments

        for file_path in self.attachments_path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                attachments.append({
                    "name": file_path.name,
                    "path": f"attachments/{file_path.name}",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "is_image": self.is_image(file_path.name),
                })

        # 按修改时间倒序
        attachments.sort(key=lambda x: x["modified"], reverse=True)

        return attachments

    def delete_attachment(self, filename: str) -> bool:
        """删除附件

        Args:
            filename: 文件名

        Returns:
            是否成功
        """
        file_path = self.attachments_path / filename

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True

        return False

    def get_attachment_path(self, relative_path: str) -> Path:
        """获取附件的完整路径

        Args:
            relative_path: 相对路径（如 attachments/image.png）

        Returns:
            完整路径
        """
        # 移除 attachments/ 前缀
        if relative_path.startswith("attachments/"):
            relative_path = relative_path[len("attachments/"):]

        return self.attachments_path / relative_path


def create_attachment_handler_for_note(note_id: str, notebook_path: Path | None = None) -> AttachmentHandler:
    """为指定笔记创建附件处理器

    Args:
        note_id: 笔记 ID
        notebook_path: 笔记本路径

    Returns:
        附件处理器实例
    """
    if notebook_path is None:
        notebook_path = Path(__file__).parent.parent.parent / "notebook"

    attachments_path = notebook_path / "skills" / note_id / "attachments"
    return AttachmentHandler(attachments_path)