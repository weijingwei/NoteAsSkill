"""笔记命名验证和转换模块

提供跨平台的笔记命名验证和转换功能。
支持 Windows、Linux、macOS 操作系统。
"""

import re
import unicodedata
from typing import Tuple


# Windows 保留文件名（不区分大小写）
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}

# Windows 不允许的字符
WINDOWS_INVALID_CHARS = '<>:"/\\|?*'

# 允许的最大长度（各平台保守值）
MAX_NAME_LENGTH = 200  # 留有余地，避免路径过长


def validate_note_name(name: str) -> Tuple[bool, str]:
    """验证笔记名称是否合法
    
    Args:
        name: 笔记名称
        
    Returns:
        (是否合法, 错误信息)
    """
    if not name:
        return False, "笔记名称不能为空"
    
    # 检查长度
    if len(name) > MAX_NAME_LENGTH:
        return False, f"笔记名称不能超过 {MAX_NAME_LENGTH} 个字符"
    
    # 检查是否以空格开头或结尾
    if name != name.strip():
        return False, "笔记名称不能以空格开头或结尾"
    
    # 检查 Windows 保留名称
    name_upper = name.upper()
    if name_upper in WINDOWS_RESERVED_NAMES:
        return False, f"'{name}' 是 Windows 系统保留名称，不能使用"
    
    # 检查是否包含 Windows 不允许的字符
    for char in WINDOWS_INVALID_CHARS:
        if char in name:
            return False, f"笔记名称不能包含字符 '{char}'"
    
    # 检查是否包含控制字符
    for char in name:
        if unicodedata.category(char) == 'Cc':  # 控制字符
            return False, "笔记名称不能包含控制字符"
    
    # 检查是否以点开头或结尾（Windows 问题）
    if name.startswith('.') or name.endswith('.'):
        return False, "笔记名称不能以点号开头或结尾"
    
    # 检查是否只包含空白字符
    if not name.strip():
        return False, "笔记名称不能只包含空白字符"
    
    return True, ""


def sanitize_note_name(name: str) -> str:
    """清理笔记名称，移除非法字符
    
    Args:
        name: 原始笔记名称
        
    Returns:
        清理后的笔记名称
    """
    if not name:
        return "untitled"
    
    # 移除首尾空格
    name = name.strip()
    
    # 移除 Windows 不允许的字符
    for char in WINDOWS_INVALID_CHARS:
        name = name.replace(char, '-')
    
    # 移除控制字符
    name = ''.join(char for char in name if unicodedata.category(char) != 'Cc')
    
    # 移除首尾点号
    name = name.strip('.')
    
    # 处理 Windows 保留名称
    if name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"{name}-note"
    
    # 限制长度
    if len(name) > MAX_NAME_LENGTH:
        name = name[:MAX_NAME_LENGTH].strip()
    
    # 如果为空，返回默认值
    if not name:
        return "untitled"
    
    return name


def generate_unique_name(base_name: str, existing_names: set[str]) -> str:
    """生成唯一的笔记名称
    
    Args:
        base_name: 基础名称
        existing_names: 已存在的名称集合
        
    Returns:
        唯一的笔记名称
    """
    if base_name not in existing_names:
        return base_name
    
    counter = 1
    while True:
        new_name = f"{base_name}-{counter}"
        if new_name not in existing_names:
            return new_name
        counter += 1
        # 防止无限循环
        if counter > 10000:
            import uuid
            return f"{base_name}-{uuid.uuid4().hex[:8]}"


def name_to_folder_name(name: str) -> str:
    """将笔记名称转换为文件夹名称
    
    保持名称原样，只进行必要的清理
    
    Args:
        name: 笔记名称
        
    Returns:
        文件夹名称
    """
    return sanitize_note_name(name)


def name_to_skill_name(name: str) -> str:
    """将笔记名称转换为 SKILL.md 中的 name 字段
    
    转换为 kebab-case 格式
    
    Args:
        name: 笔记名称
        
    Returns:
        skill name
    """
    # 先清理
    name = sanitize_note_name(name)
    
    # 转换为小写
    name = name.lower()
    
    # 将非字母数字字符替换为连字符
    name = re.sub(r'[^\w\u4e00-\u9fff]', '-', name)
    
    # 合并多个连字符
    name = re.sub(r'-+', '-', name)
    
    # 移除首尾连字符
    name = name.strip('-')
    
    return name or "untitled"
