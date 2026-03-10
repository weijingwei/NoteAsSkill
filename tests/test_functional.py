"""NoteAsSkill 功能测试脚本

测试核心功能：
1. 笔记的创建、修改、删除
2. 文件夹的创建和管理
3. SKILL.md 文件生成
4. AI 对话功能（模拟测试）
"""

import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestResult:
    """测试结果记录"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def add(self, name: str, passed: bool, message: str = ""):
        status = "PASS" if passed else "FAIL"
        self.results.append((name, status, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  [{status}] {name}: {message}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 50)
        print("测试结果汇总")
        print("=" * 50)
        for name, status, message in self.results:
            print(f"[{status}] {name}: {message}")
        print(f"\n通过率: {self.passed}/{total} ({self.passed/total*100:.1f}%)")


def test_note_manager():
    """测试笔记管理器"""
    print("\n=== 测试笔记管理器 ===")
    result = TestResult()

    # 创建临时测试目录
    temp_dir = tempfile.mkdtemp()
    notebook_path = Path(temp_dir) / "notebook"

    try:
        from app.core.note_manager import NoteManager
        manager = NoteManager(notebook_path)

        # TC01: 创建笔记
        note = manager.create_note("测试笔记1", "# 测试内容\n这是测试笔记内容。")
        result.add("创建笔记", note is not None and note.id == "测试笔记1", f"id={note.id if note else 'None'}")

        # TC02: 获取笔记内容
        content = manager.get_note_content("测试笔记1")
        result.add("获取笔记内容", "测试内容" in content, f"长度={len(content)}")

        # TC03: 更新笔记
        updated = manager.update_note("测试笔记1", content="# 更新后的内容\n新内容。")
        result.add("更新笔记", updated is not None, f"title={updated.title if updated else 'None'}")

        # TC04: 创建带标签的笔记
        tagged_note = manager.create_note("标签测试", "内容", tags=["测试", "demo"])
        result.add("创建带标签笔记", "测试" in tagged_note.tags and "demo" in tagged_note.tags, f"tags={tagged_note.tags}")

        # TC05: 列出笔记
        notes = manager.list_notes()
        result.add("列出笔记", len(notes) >= 2, f"count={len(notes)}")

        # TC06: 搜索笔记
        search_results = manager.search_notes("更新")
        result.add("搜索笔记", len(search_results) >= 1, f"found={len(search_results)}")

        # TC07: 删除笔记
        deleted = manager.delete_note("标签测试")
        result.add("删除笔记", deleted and "标签测试" not in manager._notes, f"deleted={deleted}")

    finally:
        shutil.rmtree(temp_dir)

    return result


def test_folder_manager():
    """测试文件夹管理"""
    print("\n=== 测试文件夹管理 ===")
    result = TestResult()

    temp_dir = tempfile.mkdtemp()
    notebook_path = Path(temp_dir) / "notebook"

    try:
        from app.core.note_manager import NoteManager
        manager = NoteManager(notebook_path)

        # TC01: 创建文件夹
        folder = manager.create_folder("测试文件夹1")
        result.add("创建文件夹", folder.name == "测试文件夹1", f"name={folder.name}")

        # TC02: 创建子文件夹
        sub_folder = manager.create_folder("子文件夹", parent="测试文件夹1")
        result.add("创建子文件夹", sub_folder.parent == "测试文件夹1", f"parent={sub_folder.parent}")

        # TC03: 列出文件夹
        folders = manager.list_folders()
        result.add("列出文件夹", len(folders) >= 2, f"count={len(folders)}")

        # TC04: 重命名文件夹
        renamed = manager.rename_folder("测试文件夹1", "重命名文件夹")
        result.add("重命名文件夹", renamed and "重命名文件夹" in manager._folders, f"renamed={renamed}")

        # TC05: 创建笔记并移动到文件夹
        note = manager.create_note("文件夹笔记", "内容", folder="重命名文件夹")
        result.add("创建笔记到文件夹", note.folder == "重命名文件夹", f"folder={note.folder}")

        # TC06: 移动笔记
        manager.update_note("文件夹笔记", folder="")
        moved_note = manager.get_note("文件夹笔记")
        result.add("移动笔记", moved_note.folder == "", f"folder={moved_note.folder}")

        # TC07: 删除文件夹
        deleted = manager.delete_folder("重命名文件夹")
        result.add("删除文件夹", deleted and "重命名文件夹" not in manager._folders, f"deleted={deleted}")

    finally:
        shutil.rmtree(temp_dir)

    return result


def test_skill_generation():
    """测试 SKILL.md 生成"""
    print("\n=== 测试 SKILL.md 生成 ===")
    result = TestResult()

    try:
        from app.core.skill_generator import SkillGenerator

        generator = SkillGenerator()  # 不需要参数

        # TC01: 生成 SKILL.md 内容
        test_content = "# 测试技能\n\n这是一个测试技能的描述。\n\n## 使用方法\n\n```python\ndef test():\n    pass\n```"
        skill_content = generator.generate_skill_md(test_content, use_ai=False)

        result.add("SKILL.md 生成成功", skill_content is not None and len(skill_content) > 0, f"length={len(skill_content)}")
        result.add("SKILL.md 包含 YAML", "---" in skill_content, "has front matter")
        result.add("SKILL.md 包含 name", "name:" in skill_content, "has name field")
        result.add("SKILL.md 包含 description", "description:" in skill_content, "has description field")

    except Exception as e:
        result.add("SKILL.md 生成", False, f"error: {str(e)}")

    return result


def test_existing_data():
    """测试现有数据"""
    print("\n=== 测试现有数据 ===")
    result = TestResult()

    notebook_path = Path(r"D:\claudeProjects\node_as_skill\notebook")

    if not notebook_path.exists():
        print("  跳过: notebook 目录不存在")
        return result

    from app.core.note_manager import NoteManager
    manager = NoteManager(notebook_path)

    # TC01: 加载现有笔记
    notes = manager.list_notes()
    result.add("加载现有笔记", len(notes) > 0, f"count={len(notes)}")

    # TC02: 加载现有文件夹
    folders = manager.list_folders()
    result.add("加载现有文件夹", len(folders) > 0, f"count={len(folders)}")

    # TC03: 验证 SKILL.md 文件
    skills_path = notebook_path / "skills"
    if skills_path.exists():
        skill_files = []
        for note_dir in skills_path.iterdir():
            if note_dir.is_dir():
                skill_file = note_dir / "SKILL.md"
                if skill_file.exists():
                    skill_files.append(skill_file)
        result.add("笔记 SKILL.md 文件", len(skill_files) > 0, f"count={len(skill_files)}")

        # 检查内容
        for skill_file in skill_files[:3]:  # 只检查前3个
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
            has_valid_content = "---" in content and len(content) > 50
            result.add(f"SKILL.md 有效 ({skill_file.parent.name})", has_valid_content, f"length={len(content)}")

    # TC04: 验证文件夹 SKILL.md
    folder_skills_path = notebook_path / ".folder_skills"
    if folder_skills_path.exists():
        folder_skills = list(folder_skills_path.glob("*.md"))
        result.add("文件夹 SKILL.md 文件", len(folder_skills) > 0, f"count={len(folder_skills)}")

        # TC05: 检查文件夹 SKILL 内容
        for fs_file in folder_skills:
            with open(fs_file, "r", encoding="utf-8") as f:
                content = f.read()
            has_valid_content = "---" in content and "description:" in content
            result.add(f"文件夹 SKILL 内容有效 ({fs_file.name})", has_valid_content, f"valid={has_valid_content}")

    return result


def test_chat_panel_modes():
    """测试 AI 对话模式配置"""
    print("\n=== 测试 AI 对话模式 ===")
    result = TestResult()

    try:
        # TC01: 验证模式常量
        from app.widgets.chat_panel import ChatPanel
        result.add("生成 SKILL 模式", hasattr(ChatPanel, 'MODE_SKILL'), f"mode={ChatPanel.MODE_SKILL}")
        result.add("笔记问答模式", hasattr(ChatPanel, 'MODE_QA'), f"mode={ChatPanel.MODE_QA}")
        result.add("通用对话模式", hasattr(ChatPanel, 'MODE_CHAT'), f"mode={ChatPanel.MODE_CHAT}")

        # TC02: 验证 AI 客户端接口
        from app.ai.client import AIClient, create_client
        result.add("AI 客户端基类", AIClient is not None, "AIClient defined")
        result.add("创建客户端函数", create_client is not None, "create_client defined")

        # TC03: 验证流式输出支持
        from app.widgets.chat_panel import StreamChatWorker
        result.add("流式输出 Worker", StreamChatWorker is not None, "StreamChatWorker defined")

    except Exception as e:
        result.add("AI 对话模式测试", False, f"error: {str(e)}")

    return result


def test_config_management():
    """测试配置管理"""
    print("\n=== 测试配置管理 ===")
    result = TestResult()

    try:
        from app.core.config import get_config, Config

        config = get_config()

        # TC01: 配置加载
        result.add("配置加载成功", config is not None, "config loaded")

        # TC02: AI 配置
        result.add("AI Provider", hasattr(config, 'ai_provider'), f"provider={config.ai_provider}")

        # TC03: 文件夹 SKILL 配置
        result.add("文件夹 SKILL 启用", hasattr(config, 'folder_skill_enabled'), f"enabled={config.folder_skill_enabled}")
        result.add("文件夹 SKILL 自动更新", hasattr(config, 'folder_skill_auto_update'), f"auto={config.folder_skill_auto_update}")
        result.add("文件夹 SKILL 更新延迟", hasattr(config, 'folder_skill_update_delay'), f"delay={config.folder_skill_update_delay}s")

    except Exception as e:
        result.add("配置管理测试", False, f"error: {str(e)}")

    return result


def main():
    """运行所有测试"""
    print("=" * 50)
    print("NoteAsSkill 功能测试")
    print("=" * 50)

    all_results = []

    all_results.append(test_note_manager())
    all_results.append(test_folder_manager())
    all_results.append(test_skill_generation())
    all_results.append(test_existing_data())
    all_results.append(test_chat_panel_modes())
    all_results.append(test_config_management())

    # 总汇总
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total = total_passed + total_failed

    print("\n" + "=" * 50)
    print("总体测试结果")
    print("=" * 50)
    print(f"总计: {total_passed}/{total} 通过 ({total_passed/total*100:.1f}%)")

    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)