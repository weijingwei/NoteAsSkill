"""NoteAsSkill 全面自动化测试套件

测试覆盖：
1. 设计模式测试（单例、工厂、策略、观察者、命令模式）
2. 核心功能测试（笔记管理、文件夹管理、SKILL 生成）
3. 边界条件测试（空值、超长输入、特殊字符）
4. 异常处理测试（错误输入、网络异常）
5. 集成测试（模块间协作）
6. 性能测试（大量数据处理）

运行方式：
    python tests/test_comprehensive.py
"""

import sys
import tempfile
import shutil
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestReport:
    """测试报告生成器"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        self.screenshots = []
    
    def start(self):
        self.start_time = datetime.now()
        print("=" * 60)
        print("NoteAsSkill 全面自动化测试")
        print("=" * 60)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def add(self, category: str, name: str, passed: bool, message: str = "", duration: float = 0):
        status = "PASS" if passed else "FAIL"
        self.results.append({
            "category": category,
            "name": name,
            "status": status,
            "message": message,
            "duration": duration
        })
        icon = "✓" if passed else "✗"
        print(f"  [{icon}] {name}: {message} ({duration:.2f}s)")
    
    def end(self):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = passed + failed
        
        print()
        print("=" * 60)
        print("测试报告汇总")
        print("=" * 60)
        
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0}
            if r["status"] == "PASS":
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        for cat, stats in categories.items():
            cat_total = stats["passed"] + stats["failed"]
            cat_rate = stats["passed"] / cat_total * 100 if cat_total > 0 else 0
            print(f"  {cat}: {stats['passed']}/{cat_total} ({cat_rate:.1f}%)")
        
        print()
        print(f"总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
        print(f"总耗时: {duration:.2f}s")
        print(f"结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if failed > 0:
            print()
            print("失败用例详情:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  [FAIL] {r['category']} - {r['name']}: {r['message']}")
        
        return failed == 0


report = TestReport()


def test_singleton_pattern():
    """测试单例模式"""
    print("\n=== 测试单例模式 ===")
    from app.core.singleton import SingletonMeta, SingletonMixin
    
    class TestSingleton(metaclass=SingletonMeta):
        def __init__(self):
            self.value = 0
    
    start = time.time()
    
    instance1 = TestSingleton()
    instance1.value = 100
    instance2 = TestSingleton()
    
    report.add("单例模式", "同一实例", instance1 is instance2, f"id相同={id(instance1) == id(instance2)}", time.time() - start)
    report.add("单例模式", "状态共享", instance2.value == 100, f"value={instance2.value}", time.time() - start)
    
    start = time.time()
    SingletonMeta.clear_instance(TestSingleton)
    instance3 = TestSingleton()
    report.add("单例模式", "清除后重新创建", instance3.value == 0, f"新实例value={instance3.value}", time.time() - start)
    
    SingletonMeta.clear_instance(TestSingleton)


def test_factory_pattern():
    """测试工厂模式"""
    print("\n=== 测试工厂模式 ===")
    from app.ai.factory import AIClientFactory
    
    start = time.time()
    providers = AIClientFactory.get_supported_providers()
    report.add("工厂模式", "获取支持的提供商", len(providers) >= 3, f"providers={providers}")
    
    report.add("工厂模式", "OpenAI 已注册", "openai" in providers, f"包含openai")
    report.add("工厂模式", "Anthropic 已注册", "anthropic" in providers, f"包含anthropic")
    report.add("工厂模式", "Ollama 已注册", "ollama" in providers, f"包含ollama")
    
    start = time.time()
    is_supported = AIClientFactory.is_provider_supported("openai")
    report.add("工厂模式", "检查提供商支持", is_supported, f"openai supported={is_supported}", time.time() - start)
    
    start = time.time()
    is_unsupported = AIClientFactory.is_provider_supported("unknown_provider")
    report.add("工厂模式", "检查不支持的提供商", not is_unsupported, f"unknown supported={is_unsupported}", time.time() - start)
    
    start = time.time()
    try:
        client = AIClientFactory.create("openai", {"api_key": "test-key", "model": "gpt-4"})
        report.add("工厂模式", "创建 OpenAI 客户端", client is not None, f"client created", time.time() - start)
    except Exception as e:
        report.add("工厂模式", "创建 OpenAI 客户端", False, f"error: {str(e)[:30]}", time.time() - start)
    
    start = time.time()
    try:
        client = AIClientFactory.create("unknown", {})
        report.add("工厂模式", "创建未知提供商失败", False, "应该抛出异常", time.time() - start)
    except ValueError as e:
        report.add("工厂模式", "创建未知提供商失败", True, f"正确抛出异常", time.time() - start)


def test_strategy_pattern():
    """测试策略模式"""
    print("\n=== 测试策略模式 ===")
    from app.core.folder_skill_strategies import (
        FolderSkillStrategyFactory,
        SimpleStrategy,
        AIStrategy,
        HybridStrategy,
        NoteSummary,
        FolderSummary,
    )
    
    start = time.time()
    strategies = FolderSkillStrategyFactory.get_available_strategies()
    report.add("策略模式", "获取可用策略", len(strategies) >= 3, f"strategies={strategies}", time.time() - start)
    
    report.add("策略模式", "simple 策略可用", "simple" in strategies, "")
    report.add("策略模式", "ai 策略可用", "ai" in strategies, "")
    report.add("策略模式", "hybrid 策略可用", "hybrid" in strategies, "")
    
    start = time.time()
    strategy = FolderSkillStrategyFactory.get("simple")
    report.add("策略模式", "获取 simple 策略", strategy is not None and strategy.name == "simple", f"name={strategy.name}", time.time() - start)
    
    note_summaries = [NoteSummary(id="note1", title="测试笔记", description="测试描述")]
    folder_summaries = [FolderSummary(name="子文件夹", description="子文件夹描述")]
    
    start = time.time()
    content = strategy.generate("测试文件夹", note_summaries, folder_summaries)
    report.add("策略模式", "simple 策略生成", len(content) > 0 and "---" in content, f"length={len(content)}", time.time() - start)
    
    report.add("策略模式", "生成内容包含 YAML", content.startswith("---"), "")
    report.add("策略模式", "生成内容包含笔记标题", "测试笔记" in content, "")
    report.add("策略模式", "生成内容包含文件夹名", "子文件夹" in content, "")
    
    start = time.time()
    try:
        strategy = FolderSkillStrategyFactory.get("unknown")
        report.add("策略模式", "获取未知策略失败", False, "应该抛出异常", time.time() - start)
    except ValueError:
        report.add("策略模式", "获取未知策略失败", True, "正确抛出异常", time.time() - start)


def test_event_bus():
    """测试事件总线"""
    print("\n=== 测试事件总线 ===")
    from app.core.event_bus import EventBus, EventType, Event, get_event_bus
    
    start = time.time()
    bus1 = get_event_bus()
    bus2 = get_event_bus()
    report.add("事件总线", "单例模式", bus1 is bus2, f"同一实例", time.time() - start)
    
    received_events = []
    
    def on_note_created(event: Event):
        received_events.append(event)
    
    start = time.time()
    bus1.subscribe(EventType.NOTE_CREATED, on_note_created)
    report.add("事件总线", "订阅事件", True, "订阅成功", time.time() - start)
    
    start = time.time()
    test_event = Event(EventType.NOTE_CREATED, data={"id": "test-note"}, source="test")
    bus1.publish(test_event)
    
    import time as t
    t.sleep(0.1)
    
    report.add("事件总线", "发布事件", len(received_events) == 1, f"received={len(received_events)}", time.time() - start)
    
    if received_events:
        report.add("事件总线", "事件数据正确", received_events[0].data["id"] == "test-note", f"id={received_events[0].data.get('id')}")
    
    start = time.time()
    bus1.unsubscribe(EventType.NOTE_CREATED, on_note_created)
    bus1.publish(Event(EventType.NOTE_CREATED, data={"id": "test2"}))
    t.sleep(0.1)
    report.add("事件总线", "取消订阅", len(received_events) == 1, f"仍为1个事件", time.time() - start)
    
    bus1.clear_subscribers()


def test_command_pattern():
    """测试命令模式"""
    print("\n=== 测试命令模式 ===")
    from app.core.commands import Command, CommandResult, CommandQueue, CommandType
    
    start = time.time()
    queue = CommandQueue(max_size=10)
    report.add("命令模式", "创建命令队列", queue is not None, "", time.time() - start)
    
    report.add("命令模式", "初始队列为空", queue.pending_count == 0, f"count={queue.pending_count}")
    report.add("命令模式", "无待处理命令", not queue.has_pending, "")
    
    from app.core.commands import UpdateFolderSkillCommand
    
    start = time.time()
    cmd = UpdateFolderSkillCommand("test-folder")
    report.add("命令模式", "创建更新命令", cmd is not None and cmd.type == CommandType.UPDATE_FOLDER_SKILL, f"type={cmd.type}", time.time() - start)
    
    report.add("命令模式", "命令初始未执行", not cmd.executed, f"executed={cmd.executed}")
    
    start = time.time()
    queue.add(cmd)
    report.add("命令模式", "添加命令到队列", queue.pending_count == 1, f"count={queue.pending_count}", time.time() - start)
    
    queue.clear()
    report.add("命令模式", "清空队列", queue.pending_count == 0, f"count={queue.pending_count}")


def test_config_management():
    """测试配置管理"""
    print("\n=== 测试配置管理 ===")
    temp_dir = tempfile.mkdtemp()
    
    try:
        from app.core.config import Config, get_config
        from app.core.singleton import SingletonMeta
        
        SingletonMeta.clear_instance(Config)
        
        config_path = Path(temp_dir) / ".config.yaml"
        config = Config(config_path)
        
        start = time.time()
        report.add("配置管理", "创建配置实例", config is not None, "", time.time() - start)
        
        start = time.time()
        config.set("test.key", "test_value")
        value = config.get("test.key")
        report.add("配置管理", "设置和获取配置", value == "test_value", f"value={value}", time.time() - start)
        
        start = time.time()
        default_value = config.get("nonexistent.key", "default")
        report.add("配置管理", "获取不存在的配置返回默认值", default_value == "default", f"value={default_value}", time.time() - start)
        
        start = time.time()
        config.ai_provider = "anthropic"
        report.add("配置管理", "设置 AI 提供商", config.ai_provider == "anthropic", f"provider={config.ai_provider}", time.time() - start)
        
        start = time.time()
        ai_config = config.get_ai_config("openai")
        report.add("配置管理", "获取指定提供商配置", "base_url" in ai_config, f"keys={list(ai_config.keys())}", time.time() - start)
        
        start = time.time()
        config.save()
        report.add("配置管理", "保存配置", config_path.exists(), f"path exists", time.time() - start)
        
    finally:
        shutil.rmtree(temp_dir)
        SingletonMeta.clear_instance(Config)


def test_note_manager_comprehensive():
    """全面测试笔记管理器"""
    print("\n=== 全面测试笔记管理器 ===")
    temp_dir = tempfile.mkdtemp()
    
    try:
        from app.core.note_manager import NoteManager, Note, Folder
        from app.core.singleton import SingletonMeta
        
        SingletonMeta.clear_instance(NoteManager)
        
        notebook_path = Path(temp_dir) / "notebook"
        manager = NoteManager(notebook_path)
        
        start = time.time()
        report.add("笔记管理", "创建管理器", manager is not None, "", time.time() - start)
        
        start = time.time()
        note = manager.create_note("测试笔记", "# 内容", tags=["tag1", "tag2"])
        report.add("笔记管理", "创建笔记", note is not None and note.id == "测试笔记", f"id={note.id}", time.time() - start)
        
        start = time.time()
        content = manager.get_note_content("测试笔记")
        report.add("笔记管理", "获取笔记内容", "内容" in content, f"length={len(content)}", time.time() - start)
        
        start = time.time()
        updated = manager.update_note("测试笔记", content="# 新内容", tags=["new-tag"])
        report.add("笔记管理", "更新笔记", updated is not None, f"title={updated.title}", time.time() - start)
        
        start = time.time()
        tags = manager.list_tags()
        report.add("笔记管理", "列出标签", "new-tag" in tags, f"tags={tags}", time.time() - start)
        
        start = time.time()
        notes = manager.search_notes("新内容")
        report.add("笔记管理", "搜索笔记", len(notes) > 0, f"found={len(notes)}", time.time() - start)
        
        start = time.time()
        folder = manager.create_folder("测试文件夹")
        report.add("笔记管理", "创建文件夹", folder is not None and folder.name == "测试文件夹", f"name={folder.name}", time.time() - start)
        
        start = time.time()
        sub_folder = manager.create_folder("子文件夹", parent="测试文件夹")
        report.add("笔记管理", "创建子文件夹", sub_folder.parent == "测试文件夹", f"parent={sub_folder.parent}", time.time() - start)
        
        start = time.time()
        renamed = manager.rename_folder("测试文件夹", "重命名文件夹")
        report.add("笔记管理", "重命名文件夹", renamed and "重命名文件夹" in manager._folders, f"renamed={renamed}", time.time() - start)
        
        start = time.time()
        deleted = manager.delete_note("测试笔记")
        report.add("笔记管理", "删除笔记", deleted and "测试笔记" not in manager._notes, f"deleted={deleted}", time.time() - start)
        
    finally:
        shutil.rmtree(temp_dir)
        SingletonMeta.clear_instance(NoteManager)


def test_skill_generation_comprehensive():
    """全面测试 SKILL 生成"""
    print("\n=== 全面测试 SKILL 生成 ===")
    from app.core.skill_generator import SkillGenerator, get_skill_generator
    from app.core.singleton import SingletonMeta
    
    start = time.time()
    generator = get_skill_generator()
    report.add("SKILL生成", "获取生成器实例", generator is not None, "", time.time() - start)
    
    test_content = """# Python 数据处理指南

这是一个完整的 Python 数据处理指南。

## 功能特点

- CSV 文件读取
- 数据清洗
- 数据导出

## 示例代码

```python
import pandas as pd
df = pd.read_csv('data.csv')
```
"""
    
    start = time.time()
    skill_content = generator.generate_skill_md(test_content, use_ai=False)
    report.add("SKILL生成", "简单生成 SKILL.md", len(skill_content) > 0, f"length={len(skill_content)}", time.time() - start)
    
    report.add("SKILL生成", "包含 YAML front matter", skill_content.startswith("---"), "")
    report.add("SKILL生成", "包含标题", "Python" in skill_content, "")
    
    temp_dir = tempfile.mkdtemp()
    try:
        skill_path = Path(temp_dir) / "test-note" / "SKILL.md"
        
        start = time.time()
        success = generator.generate_and_save("test-note", test_content, skill_path, use_ai=False)
        report.add("SKILL生成", "保存 SKILL.md", success and skill_path.exists(), f"success={success}", time.time() - start)
        
    finally:
        shutil.rmtree(temp_dir)


def test_folder_skill_generation():
    """测试文件夹 SKILL 生成"""
    print("\n=== 测试文件夹 SKILL 生成 ===")
    temp_dir = tempfile.mkdtemp()
    
    try:
        from app.core.note_manager import NoteManager, Folder
        from app.core.folder_skill_generator import FolderSkillGenerator
        from app.core.singleton import SingletonMeta
        
        SingletonMeta.clear_instance(NoteManager)
        
        notebook_path = Path(temp_dir) / "notebook"
        manager = NoteManager(notebook_path)
        
        folder = manager.create_folder("测试文件夹")
        note = manager.create_note("子笔记", "# 内容", folder="测试文件夹")
        
        generator = FolderSkillGenerator()
        
        start = time.time()
        content = generator.generate_folder_skill(folder)
        report.add("文件夹SKILL", "生成文件夹 SKILL", len(content) > 0, f"length={len(content)}", time.time() - start)
        
        report.add("文件夹SKILL", "包含 YAML", content.startswith("---"), "")
        report.add("文件夹SKILL", "包含文件夹名", "测试文件夹" in content or "folder-测试文件夹" in content, "")
        
        start = time.time()
        skill_hash = generator.save_folder_skill(folder, content)
        report.add("文件夹SKILL", "保存 SKILL", len(skill_hash) > 0, f"hash={skill_hash}", time.time() - start)
        
    finally:
        shutil.rmtree(temp_dir)
        SingletonMeta.clear_instance(NoteManager)


def test_change_detector():
    """测试变化检测器"""
    print("\n=== 测试变化检测器 ===")
    temp_dir = tempfile.mkdtemp()
    
    try:
        from app.core.note_manager import NoteManager, Folder
        from app.core.change_detector import ChangeDetector, get_change_detector
        from app.core.singleton import SingletonMeta
        
        SingletonMeta.clear_instance(NoteManager)
        
        notebook_path = Path(temp_dir) / "notebook"
        manager = NoteManager(notebook_path)
        
        folder = manager.create_folder("测试文件夹")
        
        detector = ChangeDetector()
        
        start = time.time()
        hash1 = detector.compute_children_hash(folder)
        report.add("变化检测", "计算初始 hash", len(hash1) > 0, f"hash={hash1}", time.time() - start)
        
        note = manager.create_note("新笔记", "# 内容", folder="测试文件夹")
        
        start = time.time()
        hash2 = detector.compute_children_hash(folder)
        report.add("变化检测", "添加笔记后 hash 变化", hash1 != hash2, f"hash changed", time.time() - start)
        
        start = time.time()
        has_changes = detector.has_changes(folder)
        report.add("变化检测", "检测到变化", has_changes, f"has_changes={has_changes}", time.time() - start)
        
    finally:
        shutil.rmtree(temp_dir)
        SingletonMeta.clear_instance(NoteManager)


def test_boundary_conditions():
    """测试边界条件"""
    print("\n=== 测试边界条件 ===")
    temp_dir = tempfile.mkdtemp()
    
    try:
        from app.core.note_manager import NoteManager
        from app.core.singleton import SingletonMeta
        
        SingletonMeta.clear_instance(NoteManager)
        
        notebook_path = Path(temp_dir) / "notebook"
        manager = NoteManager(notebook_path)
        
        start = time.time()
        note = manager.create_note("", "")
        report.add("边界条件", "空标题和内容", note is not None, f"id={note.id if note else 'None'}", time.time() - start)
        
        start = time.time()
        long_title = "a" * 100  # Windows 路径限制，使用较短标题
        note = manager.create_note(long_title, "内容")
        report.add("边界条件", "长标题", note is not None, f"id length={len(note.id) if note else 0}", time.time() - start)
        
        start = time.time()
        special_title = "测试/特殊\\字符:*?\"<>|"
        note = manager.create_note(special_title, "内容")
        report.add("边界条件", "特殊字符标题", note is not None, f"id={note.id if note else 'None'}", time.time() - start)
        
        start = time.time()
        chinese_title = "中文标题测试"
        note = manager.create_note(chinese_title, "中文内容")
        report.add("边界条件", "中文标题", note is not None and note.id == chinese_title, f"id={note.id if note else 'None'}", time.time() - start)
        
        start = time.time()
        emoji_title = "测试🎉标题"
        note = manager.create_note(emoji_title, "内容")
        report.add("边界条件", "Emoji 标题", note is not None, f"id={note.id if note else 'None'}", time.time() - start)
        
        start = time.time()
        note = manager.get_note("nonexistent-note")
        report.add("边界条件", "获取不存在的笔记", note is None, f"note={note}", time.time() - start)
        
        start = time.time()
        content = manager.get_note_content("nonexistent-note")
        report.add("边界条件", "获取不存在笔记的内容", content == "", f"content='{content}'", time.time() - start)
        
        start = time.time()
        result = manager.delete_note("nonexistent-note")
        report.add("边界条件", "删除不存在的笔记", result == False, f"result={result}", time.time() - start)
        
    finally:
        shutil.rmtree(temp_dir)
        SingletonMeta.clear_instance(NoteManager)


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    start = time.time()
    try:
        from app.ai.factory import AIClientFactory
        client = AIClientFactory.create("invalid_provider", {})
        report.add("错误处理", "无效提供商抛出异常", False, "应该抛出异常", time.time() - start)
    except ValueError as e:
        report.add("错误处理", "无效提供商抛出异常", True, f"正确抛出 ValueError", time.time() - start)
    
    start = time.time()
    try:
        from app.core.folder_skill_strategies import FolderSkillStrategyFactory
        strategy = FolderSkillStrategyFactory.get("invalid_strategy")
        report.add("错误处理", "无效策略抛出异常", False, "应该抛出异常", time.time() - start)
    except ValueError as e:
        report.add("错误处理", "无效策略抛出异常", True, f"正确抛出 ValueError", time.time() - start)
    
    start = time.time()
    try:
        from app.mcp.client import parse_mcp_config
        is_valid, servers, error = parse_mcp_config("{invalid json}")
        report.add("错误处理", "无效 JSON 解析", not is_valid, f"error={error[:30] if error else 'None'}", time.time() - start)
    except Exception as e:
        report.add("错误处理", "无效 JSON 解析", True, f"捕获异常: {str(e)[:30]}", time.time() - start)


def test_mcp_config():
    """测试 MCP 配置解析"""
    print("\n=== 测试 MCP 配置解析 ===")
    from app.mcp.client import parse_mcp_config, validate_mcp_server_config
    
    format1 = '''{"server1": {"command": "npx", "args": ["-y", "test"]}}'''
    start = time.time()
    is_valid, servers, error = parse_mcp_config(format1)
    report.add("MCP配置", "格式1解析", is_valid and "server1" in servers, f"servers={list(servers.keys()) if servers else []}", time.time() - start)
    
    format2 = '''{"mcpServers": {"server2": {"command": "node", "args": ["app.js"]}}}'''
    start = time.time()
    is_valid, servers, error = parse_mcp_config(format2)
    report.add("MCP配置", "格式2解析", is_valid and "server2" in servers, f"servers={list(servers.keys()) if servers else []}", time.time() - start)
    
    start = time.time()
    valid_config = {"command": "npx", "args": ["-y", "test"]}
    is_valid, error = validate_mcp_server_config(valid_config)
    report.add("MCP配置", "有效配置验证", is_valid, f"valid={is_valid}", time.time() - start)
    
    start = time.time()
    invalid_config = {"args": []}
    is_valid, error = validate_mcp_server_config(invalid_config)
    report.add("MCP配置", "无效配置检测", not is_valid, f"error={error}", time.time() - start)


def test_performance():
    """测试性能"""
    print("\n=== 测试性能 ===")
    temp_dir = tempfile.mkdtemp()
    
    try:
        from app.core.note_manager import NoteManager
        from app.core.singleton import SingletonMeta
        
        SingletonMeta.clear_instance(NoteManager)
        
        notebook_path = Path(temp_dir) / "notebook"
        manager = NoteManager(notebook_path)
        
        start = time.time()
        for i in range(100):
            manager.create_note(f"性能测试笔记{i}", f"# 内容{i}")
        duration = time.time() - start
        report.add("性能测试", "创建100个笔记", duration < 5.0, f"duration={duration:.2f}s", duration)
        
        start = time.time()
        notes = manager.list_notes()
        duration = time.time() - start
        report.add("性能测试", "列出100个笔记", len(notes) == 100 and duration < 1.0, f"count={len(notes)}, duration={duration:.2f}s", duration)
        
        start = time.time()
        results = manager.search_notes("性能测试")
        duration = time.time() - start
        report.add("性能测试", "搜索100个笔记", len(results) == 100 and duration < 1.0, f"found={len(results)}, duration={duration:.2f}s", duration)
        
    finally:
        shutil.rmtree(temp_dir)
        SingletonMeta.clear_instance(NoteManager)


def test_ui_components():
    """测试 UI 组件"""
    print("\n=== 测试 UI 组件 ===")
    
    components = [
        ("app.widgets.sidebar", "Sidebar"),
        ("app.widgets.editor", "Editor"),
        ("app.widgets.chat_panel", "ChatPanel"),
        ("app.widgets.notification_bar", "NotificationBar"),
        ("app.widgets.settings_dialog", "SettingsDialog"),
    ]
    
    for module_name, class_name in components:
        start = time.time()
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            report.add("UI组件", f"{class_name} 组件", cls is not None, "defined", time.time() - start)
        except Exception as e:
            report.add("UI组件", f"{class_name} 组件", False, f"error: {str(e)[:30]}", time.time() - start)


def test_version():
    """测试版本管理"""
    print("\n=== 测试版本管理 ===")
    from app.core.config import get_version
    
    start = time.time()
    version = get_version()
    report.add("版本管理", "获取版本号", version.startswith("v"), f"version={version}", time.time() - start)
    
    import re
    is_valid_format = bool(re.match(r'^v\d+\.\d+\.\d+$', version))
    report.add("版本管理", "版本格式正确", is_valid_format, f"format: v0.0.0", time.time() - start)


def run_all_tests():
    """运行所有测试"""
    report.start()
    
    test_singleton_pattern()
    test_factory_pattern()
    test_strategy_pattern()
    test_event_bus()
    test_command_pattern()
    test_config_management()
    test_note_manager_comprehensive()
    test_skill_generation_comprehensive()
    test_folder_skill_generation()
    test_change_detector()
    test_boundary_conditions()
    test_error_handling()
    test_mcp_config()
    test_performance()
    test_ui_components()
    test_version()
    
    return report.end()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
