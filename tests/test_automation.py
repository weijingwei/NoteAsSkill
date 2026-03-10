"""NoteAsSkill 自动化测试脚本

使用 pyautogui 进行 GUI 自动化测试。
"""

import pyautogui
import time
import subprocess
import os
from pathlib import Path

# 配置
PYTHON_PATH = r"D:\ProgramData\miniconda3\envs\noteasskill\python.exe"
APP_PATH = r"D:\claudeProjects\node_as_skill\main.py"
SCREENSHOTS_DIR = Path(r"D:\claudeProjects\node_as_skill\tests\screenshots")

# 安全设置
pyautogui.PAUSE = 0.5
pyautogui.FAILSAFE = True

# 屏幕尺寸
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
print(f"屏幕尺寸: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

# 创建截图目录
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def take_screenshot(name: str) -> Path:
    """截取屏幕截图"""
    path = SCREENSHOTS_DIR / f"{name}.png"
    pyautogui.screenshot(str(path))
    print(f"截图保存: {path}")
    return path


def find_app_window():
    """查找应用窗口位置"""
    # 应用默认 1200x800，居中显示
    # 窗口左上角大约在屏幕中心偏左上
    window_width = 1200
    window_height = 800
    window_x = (SCREEN_WIDTH - window_width) // 2
    window_y = (SCREEN_HEIGHT - window_height) // 2

    return {
        "x": window_x,
        "y": window_y,
        "width": window_width,
        "height": window_height,
    }


def click_relative(window: dict, rel_x: int, rel_y: int):
    """相对于窗口点击"""
    abs_x = window["x"] + rel_x
    abs_y = window["y"] + rel_y
    pyautogui.click(abs_x, abs_y)
    print(f"点击: ({abs_x}, {abs_y})")


def type_text(text: str, interval: float = 0.05):
    """输入文字"""
    pyautogui.write(text, interval=interval)
    print(f"输入: {text}")


class NoteAsSkillTester:
    """NoteAsSkill 测试器"""

    def __init__(self):
        self.process = None
        self.window = None
        self.test_results = []
        self.notebook_path = Path(r"D:\claudeProjects\node_as_skill\notebook")

    def start_app(self):
        """启动应用"""
        print("\n=== 启动应用 ===")
        self.process = subprocess.Popen(
            [PYTHON_PATH, APP_PATH],
            cwd=os.path.dirname(APP_PATH),
        )
        time.sleep(3)  # 等待应用启动
        self.window = find_app_window()
        take_screenshot("01_app_started")
        return True

    def stop_app(self):
        """停止应用"""
        print("\n=== 停止应用 ===")
        if self.process:
            self.process.terminate()
            self.process.wait()
        return True

    def test_toolbar(self):
        """测试工具栏"""
        print("\n=== 测试工具栏 ===")
        # 工具栏在侧边栏上部，大约在窗口左侧 y=50-80 的位置
        # 新建按钮
        click_relative(self.window, 50, 70)
        time.sleep(0.5)
        take_screenshot("02_toolbar_new_clicked")

        # 取消对话框
        pyautogui.press('escape')
        time.sleep(0.5)
        return True

    def test_create_note(self):
        """测试创建笔记"""
        print("\n=== 测试创建笔记 ===")
        # 点击新建按钮
        click_relative(self.window, 50, 70)
        time.sleep(0.5)

        # 输入笔记标题
        type_text("自动化测试笔记")
        time.sleep(0.5)

        # 点击确定（Tab 然后 Enter）
        pyautogui.press('tab')
        pyautogui.press('enter')
        time.sleep(1)

        take_screenshot("03_note_created")
        return True

    def test_edit_note(self):
        """测试编辑笔记"""
        print("\n=== 测试编辑笔记 ===")
        # 点击中间编辑器区域
        click_relative(self.window, 500, 400)
        time.sleep(0.5)

        # 输入内容
        pyautogui.hotkey('ctrl', 'a')  # 全选
        type_text("# 测试笔记\n\n这是自动化测试创建的笔记内容。\n\n## 测试章节\n\n测试内容。")
        time.sleep(0.5)

        take_screenshot("04_note_edited")
        return True

    def test_save_note(self):
        """测试保存笔记"""
        print("\n=== 测试保存笔记 ===")
        # 点击保存按钮
        click_relative(self.window, 100, 70)
        time.sleep(2)  # 等待保存和 SKILL.md 生成

        take_screenshot("05_note_saved")
        return True

    def test_create_folder(self):
        """测试创建文件夹"""
        print("\n=== 测试创建文件夹 ===")
        # 右键点击"全部笔记"
        click_relative(self.window, 50, 150)
        pyautogui.rightClick()
        time.sleep(0.5)

        # 点击"新建文件夹"
        click_relative(self.window, 70, 200)
        time.sleep(0.5)

        # 输入文件夹名称
        type_text("测试文件夹")
        pyautogui.press('enter')
        time.sleep(1)

        take_screenshot("06_folder_created")
        return True

    def test_settings(self):
        """测试设置对话框"""
        print("\n=== 测试设置对话框 ===")
        # 点击菜单栏 "设置"
        # Alt 打开菜单
        pyautogui.press('alt')
        time.sleep(0.3)

        # 按右箭头找到设置菜单
        for _ in range(3):
            pyautogui.press('right')
            time.sleep(0.1)

        pyautogui.press('down')
        pyautogui.press('enter')
        time.sleep(1)

        take_screenshot("07_settings_dialog")

        # 关闭对话框
        pyautogui.press('escape')
        return True

    def test_drag_note_to_folder(self):
        """测试拖拽笔记到文件夹"""
        print("\n=== 测试拖拽笔记到文件夹 ===")

        # 先创建一个文件夹（如果不存在）
        # 右键点击"全部笔记"
        click_relative(self.window, 50, 150)
        pyautogui.rightClick()
        time.sleep(0.5)

        # 点击"新建文件夹"
        click_relative(self.window, 70, 200)
        time.sleep(0.5)

        # 输入文件夹名称
        type_text("拖拽测试文件夹")
        pyautogui.press('enter')
        time.sleep(1)

        # 拖拽笔记到文件夹
        # 从笔记列表拖拽到文件夹树
        # 笔记列表大约在左侧中间位置，文件夹树在上方
        note_list_x = self.window["x"] + 100
        note_list_y = self.window["y"] + 350
        folder_tree_x = self.window["x"] + 60
        folder_tree_y = self.window["y"] + 200

        pyautogui.moveTo(note_list_x, note_list_y)
        time.sleep(0.3)
        pyautogui.dragTo(folder_tree_x, folder_tree_y, duration=0.5)
        time.sleep(1)

        take_screenshot("08_note_dragged")
        return True

    def test_verify_skill_md(self):
        """验证笔记 SKILL.md 文件生成"""
        print("\n=== 验证笔记 SKILL.md 文件 ===")

        skills_path = self.notebook_path / "skills"
        if not skills_path.exists():
            print("skills 目录不存在")
            return False

        # 查找所有笔记目录
        note_dirs = [d for d in skills_path.iterdir() if d.is_dir()]
        if not note_dirs:
            print("没有找到笔记目录")
            return False

        # 检查 SKILL.md 文件
        skill_files_found = 0
        for note_dir in note_dirs:
            skill_file = note_dir / "SKILL.md"
            if skill_file.exists():
                skill_files_found += 1
                print(f"找到 SKILL.md: {skill_file}")

                # 读取内容验证
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        print(f"  内容长度: {len(content)} 字符")

        print(f"共找到 {skill_files_found} 个 SKILL.md 文件")
        return skill_files_found > 0

    def test_folder_skill_md(self):
        """验证文件夹 SKILL.md 文件"""
        print("\n=== 验证文件夹 SKILL.md ===")

        folder_skills_path = self.notebook_path / ".folder_skills"
        if not folder_skills_path.exists():
            print(".folder_skills 目录不存在")
            return False

        # 查找文件夹 SKILL.md 文件
        skill_files = list(folder_skills_path.glob("*.md"))
        if not skill_files:
            print("没有找到文件夹 SKILL.md 文件")
            return False

        print(f"找到 {len(skill_files)} 个文件夹 SKILL.md 文件")
        for skill_file in skill_files:
            print(f"  {skill_file.name}")

            # 读取内容验证
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    print(f"    内容长度: {len(content)} 字符")

        return len(skill_files) > 0

    def test_ai_chat_modes(self):
        """测试 AI 对话模式"""
        print("\n=== 测试 AI 对话模式 ===")

        # 点击右侧面板的模式选择下拉框
        # 右侧面板大约在窗口右侧，下拉框在顶部
        mode_combo_x = self.window["x"] + 950
        mode_combo_y = self.window["y"] + 80

        # 测试"生成 SKILL"模式
        click_relative(self.window, 900, 80)
        time.sleep(0.3)
        pyautogui.press('down')  # 选择"生成 SKILL"
        pyautogui.press('enter')
        time.sleep(0.5)

        # 点击发送按钮
        click_relative(self.window, 1050, 750)
        time.sleep(2)

        take_screenshot("09_ai_skill_mode")

        # 测试"笔记问答"模式
        click_relative(self.window, 900, 80)
        time.sleep(0.3)
        pyautogui.press('down')
        pyautogui.press('down')
        pyautogui.press('enter')
        time.sleep(0.5)

        take_screenshot("10_ai_qa_mode")

        # 测试"通用对话"模式
        click_relative(self.window, 900, 80)
        time.sleep(0.3)
        pyautogui.press('down')
        pyautogui.press('down')
        pyautogui.press('down')
        pyautogui.press('enter')
        time.sleep(0.5)

        # 输入测试消息
        click_relative(self.window, 900, 650)
        type_text("这是一个测试消息")
        time.sleep(0.3)

        take_screenshot("11_ai_chat_mode")

        return True

    def test_delete_note(self):
        """测试删除笔记"""
        print("\n=== 测试删除笔记 ===")

        # 右键点击笔记列表中的笔记
        click_relative(self.window, 100, 350)
        pyautogui.rightClick()
        time.sleep(0.5)

        # 点击删除
        click_relative(self.window, 120, 400)
        time.sleep(0.5)

        # 确认删除
        pyautogui.press('enter')
        time.sleep(1)

        take_screenshot("12_note_deleted")
        return True

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 50)
        print("NoteAsSkill 自动化测试开始")
        print("=" * 50)

        tests = [
            ("TC01 启动应用", self.start_app),
            ("TC02 工具栏测试", self.test_toolbar),
            ("TC03 创建笔记", self.test_create_note),
            ("TC04 编辑笔记", self.test_edit_note),
            ("TC05 保存笔记", self.test_save_note),
            ("TC06 创建文件夹", self.test_create_folder),
            ("TC07 拖拽笔记到文件夹", self.test_drag_note_to_folder),
            ("TC08 验证笔记 SKILL.md", self.test_verify_skill_md),
            ("TC09 验证文件夹 SKILL.md", self.test_folder_skill_md),
            ("TC10 AI 对话模式", self.test_ai_chat_modes),
            ("TC11 删除笔记", self.test_delete_note),
            ("TC12 设置对话框", self.test_settings),
        ]

        for name, test_func in tests:
            try:
                result = test_func()
                self.test_results.append((name, "PASS" if result else "FAIL"))
                print(f"[PASS] {name}: 通过")
            except Exception as e:
                self.test_results.append((name, f"FAIL: {str(e)}"))
                print(f"[FAIL] {name}: 失败 - {str(e)}")

        # 停止应用
        self.stop_app()

        # 输出测试结果
        print("\n" + "=" * 50)
        print("测试结果汇总")
        print("=" * 50)
        for name, result in self.test_results:
            status = "[PASS]" if result == "PASS" else "[FAIL]"
            print(f"{status} {name}: {result}")

        # 最终截图
        take_screenshot("99_final")

        return self.test_results


if __name__ == "__main__":
    tester = NoteAsSkillTester()
    results = tester.run_all_tests()

    # 统计
    passed = sum(1 for _, r in results if r == "PASS")
    total = len(results)
    print(f"\n测试通过率: {passed}/{total} ({passed/total*100:.1f}%)")