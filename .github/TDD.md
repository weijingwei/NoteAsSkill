# TDD 开发流程

## 原则

1. **先写测试，再写实现** — Red → Green → Refactor
2. **Bug 修复先写复现测试** — 确保不回归
3. **每次提交前测试全绿** — 本地运行 `pytest tests/ -v` 通过后再提交

## 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行指定模块
python -m pytest tests/test_core/ -v
python -m pytest tests/test_ai/ -v
python -m pytest tests/test_integration/ -v

# 运行指定文件
python -m pytest tests/test_core/test_singleton.py -v

# 运行单个测试
python -m pytest tests/test_core/test_singleton.py::TestSingletonMeta::test_same_instance -v

# 带覆盖率
python -m pytest tests/ -v --cov=app --cov-report=html

# 只运行非 GUI 测试（快速）
python -m pytest tests/ -v -m "not slow"
```

## 环境

```bash
conda activate noteasskill
```

Python 路径: `conda env: noteasskill` (Python 3.12)

## 测试分层

| 层级 | 目录 | 目标 |
|------|------|------|
| Unit | `tests/test_core/`, `tests/test_ai/`, `tests/test_mcp/` | 90%+ 覆盖率 |
| Integration | `tests/test_integration/` | 关键流程端到端 |
| Component | `tests/test_widgets/` | pytest-qt 组件测试 |
| E2E | `tests/test_automation.py` | GUI 自动化（pyautogui） |

## Fixtures

全局 fixtures 定义在 `tests/conftest.py`:

- `clean_singletons` — autouse，自动清理单例状态
- `temp_notebook` — 隔离的 notebook 目录
- `config_with_temp` — 指向临时目录的 Config
- `ai_client_mock` — mock AI 客户端
- `mock_ai_chat_response` — 固定 AI 响应

## 新功能开发流程

```
1. 明确需求：功能要做什么？
2. 写测试：测试文件 tests/test_xxx.py
3. 运行测试：确认失败（Red）
4. 写实现：最小代码让测试通过（Green）
5. 运行测试：确认全绿
6. 重构：改善代码结构，保持测试绿
7. 提交：git commit
```

## Bug 修复流程

```
1. 写复现测试：模拟 bug 场景
2. 运行测试：确认失败
3. 修复代码
4. 运行测试：确认修复且全绿
5. 提交
```

## CI 门禁

每次 push/PR 必须通过 CI 中的 pytest 测试。CI 配置见 `.github/workflows/build.yml`。
