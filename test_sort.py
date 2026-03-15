#!/usr/bin/env python3
"""测试笔记排序功能"""

import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent))

from app.core.note_manager import Note, NoteManager

def test_note_creation():
    """测试创建笔记时是否设置sort_order"""
    print("测试1：创建新笔记是否设置sort_order")

    # 创建临时测试目录
    test_dir = Path(__file__).parent / "test_notebook"
    test_dir.mkdir(exist_ok=True)

    # 创建笔记管理器
    manager = NoteManager(test_dir)

    # 创建笔记
    note = manager.create_note("测试排序笔记", "内容")
    print(f"  新建笔记: {note.title}")
    print(f"  sort_order值: {note.sort_order}")

    # 从索引中重新加载验证
    manager2 = NoteManager(test_dir)
    loaded_note = manager2.get_note(note.id)
    print(f"  重新加载后sort_order值: {loaded_note.sort_order if loaded_note else 'None'}")

    return note.sort_order

def test_existing_notes():
    """测试现有笔记的sort_order处理"""
    print("\n测试2：现有笔记的sort_order处理")

    # 使用真实笔记本路径
    notebook_path = Path(__file__).parent / "notebook"
    manager = NoteManager(notebook_path)

    # 检查现有笔记
    notes = manager.list_notes()
    print(f"  现有笔记数量: {len(notes)}")

    for note in notes[:3]:  # 只显示前3个
        print(f"  - {note.title}: sort_order={note.sort_order}, created_at={note.created_at}")

    # 测试不同排序方式
    print("\n测试3：不同排序方式")

    sort_modes = ["created_at", "updated_at", "title", "manual"]
    for mode in sort_modes:
        sorted_notes = manager.list_notes(sort_by=mode)
        print(f"  {mode}排序:")
        for note in sorted_notes[:2]:  # 只显示前2个
            print(f"    - {note.title} (sort_order={note.sort_order})")

def test_update_sort_order():
    """测试更新排序权重"""
    print("\n测试4：更新排序权重")

    notebook_path = Path(__file__).parent / "notebook"
    manager = NoteManager(notebook_path)

    # 获取现有笔记
    notes = manager.list_notes(folder="测试文件夹2-1")
    print(f"  '测试文件夹2-1'文件夹中的笔记:")
    for note in notes:
        print(f"    - {note.title} (当前sort_order={note.sort_order})")

    if len(notes) >= 2:
        # 批量更新排序
        note_ids = [notes[1].id, notes[0].id]  # 反转顺序
        print(f"  批量更新排序顺序: {note_ids}")

        manager.update_notes_sort_order(note_ids)

        # 重新加载验证
        manager2 = NoteManager(notebook_path)
        updated_notes = manager2.list_notes(folder="测试文件夹2-1", sort_by="manual")
        print(f"  手动排序后:")
        for note in updated_notes:
            print(f"    - {note.title} (sort_order={note.sort_order})")

def test_index_migration():
    """测试索引数据迁移"""
    print("\n测试5：索引数据迁移检查")

    # 读取原始索引文件
    index_path = Path(__file__).parent / "notebook" / ".index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 检查所有笔记是否有sort_order字段
    notes_without_sort = []
    for note in data.get("notes", []):
        if "sort_order" not in note:
            notes_without_sort.append(note["id"])

    if notes_without_sort:
        print(f"  需要迁移的笔记: {len(notes_without_sort)}个")
        print(f"  列表: {notes_without_sort}")

        # 显示原始JSON结构
        print(f"\n  第一个笔记的原始结构:")
        print(f"  {json.dumps(data['notes'][0], indent=2, ensure_ascii=False)}")
    else:
        print("  所有笔记都已包含sort_order字段")

def test_sort_algorithm():
    """测试排序算法"""
    print("\n测试6：排序算法验证")

    notebook_path = Path(__file__).parent / "notebook"
    manager = NoteManager(notebook_path)

    # 手动排序测试
    notes = manager.list_notes(sort_by="manual")
    print(f"  手动排序结果 (共{len(notes)}个):")

    for note in notes:
        key = (-note.sort_order, -note.created_at.timestamp(), note.title)
        print(f"  - {note.title}: sort_order={note.sort_order}, key={key}")

if __name__ == "__main__":
    print("=== 笔记排序功能测试 ===\n")

    # 创建测试目录并运行测试
    try:
        test_note_creation()
    except Exception as e:
        print(f"  测试1失败: {e}")

    test_existing_notes()
    test_update_sort_order()
    test_index_migration()
    test_sort_algorithm()

    print("\n=== 测试完成 ===")