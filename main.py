#!/usr/bin/env python3
"""NoteAsSkill - 笔记即技能

一个将笔记自动转换为 Claude Code Skill 的桌面应用。
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """应用主入口"""
    from PySide6.QtWidgets import QApplication

    from app.widgets.main_window import run_app

    run_app()


if __name__ == "__main__":
    main()