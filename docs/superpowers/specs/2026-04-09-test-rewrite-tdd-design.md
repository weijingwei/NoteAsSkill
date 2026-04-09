# 测试重写与 TDD 流程建立 — 设计文档

**日期**: 2026-04-09
**状态**: Draft

## 目标

将项目从自定义测试框架迁移到 pytest，一次性重写全部测试，同时精简项目结构，建立 TDD 开发流程。

## 当前问题

1. **测试框架非标**：使用自定义 `TestResult`/`TestReport`，非 pytest，缺乏 fixture、parametrize、覆盖率统计
2. **测试组织混乱**：159 个测试用例塞在两个文件中，难以维护
3. **文档过期**：`test_plan.md` 版本号停在 v0.2.73，与实际代码脱节
4. **临时文件入仓**：`test_notebook/`、`notebook/skills/` 下的测试数据被 git 追踪
5. **一次性产物堆积**：40+ 张 combobox 截图是 UI 验证的一次性产物
6. **无 TDD 流程**：没有"先写测试"的开发规范

## 项目结构精简

### 删除项（附影响评估）

| 路径 | 影响评估 | 理由 |
|------|----------|------|
| `docs/plans/2026-03-11-ui-controls-redesign.md` | 无影响。代码中无引用，对应改动已合并 | 已完成的实现计划，无未来引用价值 |
| `tests/test_plan.md` | 无影响。由 pytest 输出和 CI 报告替代 | 快照报告，版本号与实际脱节 |
| `tests/test_comprehensive.py` | 有影响但被替代。159 个用例将重写为 pytest | 迁移到 pytest 后不再需要 |
| `tests/test_functional.py` | 有影响但被替代。用例将重写为 pytest | 迁移到 pytest 后不再需要 |
| `tests/screenshots/`（全部） | 轻微影响。pyautogui 测试会重新生成 | 旧框架产物，新测试重新生成截图 |
| `tests/__pycache__/` | 无影响 | Python 缓存，应被 .gitignore 排除 |
| `test_notebook/` | 无影响。CI 中用临时目录替代 | 测试数据不应在仓库中 |
| `notebook/skills/测试笔记*/` | 无影响。运行时数据 | 应被 .gitignore 排除 |
| `notebook/.folder_skills/` | 无影响。运行时生成 | 应被 .gitignore 排除 |

### 保留项

| 路径 | 理由 |
|------|------|
| `scripts/create_icons.py` | 构建工具，本地开发和打包仍需 |
| `build.bat` | 本地 Windows 打包脚本 |
| `.github/workflows/build.yml` | CI/CD 三平台自动发布流程，需增加测试步骤 |

### 修改项

| 路径 | 修改内容 |
|------|----------|
| `.gitignore` | 增加 `notebook/skills/`、`notebook/.folder_skills/`、`notebook/.index.json`、`notebook/.config.yaml`、`test_notebook/`、`tests/__pycache__/`、`tests/screenshots/`。注意不忽略 `notebook/templates/`（项目资源） |
| `requirements.txt` | 新增测试依赖：`pytest`、`pytest-qt`、`pytest-cov`、`responses` |
| `.github/workflows/build.yml` | 在 build 前增加 `pytest tests/ -v` 步骤 |

## 新测试架构

```
tests/
├── conftest.py              # pytest 全局 fixtures
├── test_core/               # core/ 模块测试（13 个文件）
│   ├── test_singleton.py
│   ├── test_config.py
│   ├── test_event_bus.py
│   ├── test_commands.py
│   ├── test_note_manager.py
│   ├── test_note_naming.py
│   ├── test_skill_generator.py
│   ├── test_change_detector.py
│   ├── test_folder_skill_generator.py
│   ├── test_folder_skill_strategies.py
│   ├── test_folder_skill_updater.py
│   ├── test_attachment_handler.py
│   ├── test_static_resources.py
│   └── test_system_config.py
├── test_ai/                 # ai/ 模块测试（5 个文件）
│   ├── test_factory.py
│   ├── test_client_base.py
│   ├── test_openai_client.py
│   ├── test_anthropic_client.py
│   └── test_ollama_client.py
├── test_mcp/                # mcp/ 模块测试（2 个文件）
│   ├── test_mcp_client.py
│   └── test_mcp_manager.py
├── test_widgets/            # widgets/ 模块测试（5 个文件）
│   ├── test_sidebar.py
│   ├── test_editor.py
│   ├── test_chat_panel.py
│   ├── test_settings_dialog.py
│   └── test_notification_bar.py
├── test_integration/        # 集成测试（2 个文件）
│   ├── test_full_note_flow.py
│   └── test_ai_integration.py
└── test_automation.py       # 保留 pyautogui（12 个 UI 自动化用例）
```

## 核心 Fixtures 设计

### `temp_notebook`
为每个测试创建隔离的 notebook 目录。使用 `tmp_path` fixture，测试完自动清理。

### `clean_singletons`（autouse=True）
每个测试后自动清理所有单例。由于项目使用两种单例实现，需要分别处理：
- `SingletonMeta` 类（`Config`、`NoteManager`）：调用 `SingletonMeta.clear_instance(ClassName)`
- 自定义 `__new__` 单例（`EventBus`、`MCPManager`）：设置 `ClassName._instance = None`

### `mock_ai_response`
mock AI 客户端返回固定响应，避免真实 API 调用。

### `config_with_temp`
将 Config 指向临时 notebook 目录，避免污染用户配置。

## 测试分层与覆盖率目标

| 层级 | 范围 | 工具 | 覆盖率目标 |
|------|------|------|-----------|
| Unit | core/（单例、配置、事件、命令） | pytest 原生 | 90%+ |
| Unit | core/（笔记 CRUD、SKILL 生成） | pytest + mock | 90%+ |
| Unit | ai/（工厂、客户端） | pytest + responses | 90%+ |
| Unit | mcp/ | pytest + mock | 90%+ |
| Integration | 完整笔记流 | pytest | 80%+ |
| Component | widgets/ | pytest-qt (qtbot) | 50%+ |
| E2E | GUI 自动化 | pyautogui | 关键流程 |

## TDD 流程规范

建立 `.github/TDD.md`，规定：

1. **新功能**：先写测试 → 红 → 绿 → 重构
2. **Bug 修复**：先写复现测试 → 修复 → 确保不回归
3. **运行方式**：`pytest tests/ -v --cov=app`
4. **CI 门禁**：每次 push/PR 必须通过 pytest

## CI 修改

在 `.github/workflows/build.yml` 中，每个 build job 的 install dependencies 后增加：

```yaml
- name: Run tests
  run: pytest tests/ -v --cov=app --cov-report=xml
```

## 迁移顺序

1. 精简项目结构（删除无用文件，更新 .gitignore）
2. 创建 `pytest.ini` + `conftest.py` 基础设施
3. 按依赖顺序逐模块迁移测试（见下方顺序表）
4. 建立 `.github/TDD.md` 流程文档
5. 修改 `.github/workflows/build.yml` 增加测试步骤
6. 更新 `README.md` 中的测试运行说明

### 模块迁移顺序

| 顺序 | 模块 | 原因 |
|------|------|------|
| 1 | `singleton.py` | 最基础，无依赖 |
| 2 | `config.py` | 依赖 singleton |
| 3 | `event_bus.py` | 无外部依赖 |
| 4 | `commands.py` | 依赖 event_bus |
| 5 | `note_naming.py` | 纯函数，无依赖 |
| 6 | `note_manager.py` | 核心业务逻辑，依赖以上所有 |
| 7 | `attachment_handler.py` | 文件操作 |
| 8 | `skill_generator.py` | 需要 mock AI |
| 9 | `change_detector.py` | 文件系统监听 |
| 10 | `folder_skill_generator.py` | 聚合逻辑 |
| 11 | `folder_skill_strategies.py` | 策略模式 |
| 12 | `folder_skill_updater.py` | 防抖逻辑 |
| 13 | `static_resources.py` | 资源加载 |
| 14 | `system_config.py` | 系统配置 |
| 15 | `ai/factory.py` | 工厂模式 |
| 16 | `ai/client.py` | 抽象基类 |
| 17 | `ai/openai_client.py` | HTTP mock |
| 18 | `ai/anthropic_client.py` | HTTP mock |
| 19 | `ai/ollama_client.py` | HTTP mock |
| 20 | `mcp/client.py` | JSON 解析 |
| 21 | `mcp/manager.py` | 子进程 mock |
| 22 | `widgets/*` | pytest-qt |
| 23 | `test_integration/*` | 集成测试 |
