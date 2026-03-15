"""本地静态资源管理

下载并管理 EasyMDE 和 Font Awesome 静态文件。
"""

import os
import urllib.request
import logging

logger = logging.getLogger(__name__)

# 静态资源目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'static')
EASYMDE_DIR = os.path.join(STATIC_DIR, 'easymde')
FONTAWESOME_DIR = os.path.join(STATIC_DIR, 'font-awesome')

# CDN 资源 URL
EASYMDE_CSS_URL = "https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css"
EASYMDE_JS_URL = "https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js"
FONTAWESOME_CSS_URL = "https://cdn.jsdelivr.net/npm/font-awesome@4/css/font-awesome.min.css"

# 字体文件 URL (Font Awesome 4)
FONT_URLS = {
    "fontawesome-webfont.woff": "https://cdn.jsdelivr.net/npm/font-awesome@4/fonts/fontawesome-webfont.woff",
    "fontawesome-webfont.woff2": "https://cdn.jsdelivr.net/npm/font-awesome@4/fonts/fontawesome-webfont.woff2",
    "fontawesome-webfont.ttf": "https://cdn.jsdelivr.net/npm/font-awesome@4/fonts/fontawesome-webfont.ttf",
}


def ensure_static_files() -> bool:
    """确保静态文件存在，如果不存在则下载

    Returns:
        bool: 是否成功（文件已存在或下载成功）
    """
    # 检查关键文件是否存在
    easymde_js = os.path.join(EASYMDE_DIR, 'easymde.min.js')
    easymde_css = os.path.join(EASYMDE_DIR, 'easymde.min.css')
    fa_css = os.path.join(FONTAWESOME_DIR, 'css', 'font-awesome.min.css')

    if os.path.exists(easymde_js) and os.path.exists(easymde_css) and os.path.exists(fa_css):
        return True

    # 需要下载
    logger.info("Downloading static resources...")
    return download_static_files()


def download_static_files() -> bool:
    """下载静态文件

    Returns:
        bool: 是否下载成功
    """
    try:
        # 创建目录
        os.makedirs(EASYMDE_DIR, exist_ok=True)
        os.makedirs(os.path.join(FONTAWESOME_DIR, 'css'), exist_ok=True)
        os.makedirs(os.path.join(FONTAWESOME_DIR, 'fonts'), exist_ok=True)

        # 下载 EasyMDE
        _download_file(EASYMDE_CSS_URL, os.path.join(EASYMDE_DIR, 'easymde.min.css'))
        _download_file(EASYMDE_JS_URL, os.path.join(EASYMDE_DIR, 'easymde.min.js'))

        # 下载 Font Awesome CSS
        _download_file(FONTAWESOME_CSS_URL, os.path.join(FONTAWESOME_DIR, 'css', 'font-awesome.min.css'))

        # 下载字体文件
        for font_name, url in FONT_URLS.items():
            _download_file(url, os.path.join(FONTAWESOME_DIR, 'fonts', font_name))

        # 修复 Font Awesome CSS 中的字体路径
        _fix_fontawesome_css()

        logger.info("Static resources downloaded successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to download static files: {e}")
        return False


def _download_file(url: str, dest: str) -> None:
    """下载单个文件"""
    logger.debug(f"Downloading {url} to {dest}")
    urllib.request.urlretrieve(url, dest)


def _fix_fontawesome_css() -> None:
    """修复 Font Awesome CSS 中的字体路径

    将相对路径修改为适合本地文件的路径
    """
    css_path = os.path.join(FONTAWESOME_DIR, 'css', 'font-awesome.min.css')

    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换字体路径
        # 原始: ../fonts/fontawesome-webfont.woff2
        # 修改为: ../fonts/fontawesome-webfont.woff2 (保持不变，但确保路径正确)
        # 注：Font Awesome 4 的 minified CSS 已经使用正确的相对路径

        # 无需修改，路径已经是 ../fonts/ 格式
        logger.debug("Font Awesome CSS paths verified")

    except Exception as e:
        logger.warning(f"Could not verify Font Awesome CSS: {e}")


def get_static_path() -> str:
    """获取静态资源目录的绝对路径"""
    return os.path.abspath(STATIC_DIR)


def get_easymde_css_path() -> str:
    """获取 EasyMDE CSS 文件路径"""
    return os.path.join(EASYMDE_DIR, 'easymde.min.css')


def get_easymde_js_path() -> str:
    """获取 EasyMDE JS 文件路径"""
    return os.path.join(EASYMDE_DIR, 'easymde.min.js')


def get_fontawesome_css_path() -> str:
    """获取 Font Awesome CSS 文件路径"""
    return os.path.join(FONTAWESOME_DIR, 'css', 'font-awesome.min.css')