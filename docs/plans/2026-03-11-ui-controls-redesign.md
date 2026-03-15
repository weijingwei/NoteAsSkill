# UI 控件重设计 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重新设计左侧栏展开/闭合按钮和右侧栏下拉框，移除黑底，使其与应用"温暖编辑风格"协调一致。

**Architecture:** 修改 `sidebar.py` 中的 `drawBranches()` 方法绘制三角形指示器；修改 `chat_panel.py` 中 `QComboBox` 的样式表实现扁平简约风格。

**Tech Stack:** PySide6/Qt, QPainter, QSS (Qt Style Sheets)

---

### Task 1: 重写展开/闭合按钮绘制方法

**Files:**
- Modify: `app/widgets/sidebar.py:74-113`

**Step 1: 修改 drawBranches 方法绘制三角形**

修改 `app/widgets/sidebar.py` 中的 `drawBranches` 方法：

```python
def drawBranches(self, painter: QPainter, rect: QRect, index) -> None:
    """自定义绘制展开/收起按钮，使用三角形指示器"""
    item = self.itemFromIndex(index)
    if item is None or item.childCount() == 0:
        return

    # 三角形参数
    size = 8  # 三角形大小
    margin = 4  # 左边距

    # 计算三角形位置
    x = rect.left() + margin
    y = rect.top() + (rect.height() - size) // 2

    # 设置绘制样式
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 三角形颜色（与文字颜色协调）
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#8B5A2B"))  # 棕色

    if item.isExpanded():
        # 展开状态：向下三角形 ▼
        points = [
            (x, y),
            (x + size, y),
            (x + size // 2, y + size)
        ]
    else:
        # 收起状态：向右三角形 ▶
        points = [
            (x, y),
            (x + size, y + size // 2),
            (x, y + size)
        ]

    from PySide6.QtGui import QPolygon
    polygon = QPolygon()
    for px, py in points:
        polygon.append((px, py))
    painter.drawPolygon(polygon)

    painter.restore()
```

**Step 2: 运行应用验证视觉效果**

Run: `D:\ProgramData\miniconda3\envs\noteasskill\python.exe main.py`

Expected: 文件夹树中的展开/闭合按钮显示为三角形，无黑底

**Step 3: 提交**

```bash
git add app/widgets/sidebar.py
git commit -m "style: 展开/闭合按钮改为三角形指示器"
```

---

### Task 2: 添加下拉框样式表

**Files:**
- Modify: `app/widgets/chat_panel.py:83-98`

**Step 1: 在 _init_ui 方法中添加 QComboBox 样式表**

在 `app/widgets/chat_panel.py` 的 `_init_ui` 方法中，找到 `self.mode_combo` 创建位置，添加样式表：

```python
# 模式选择
mode_layout = QHBoxLayout()
mode_label = QLabel("模式:")
mode_layout.addWidget(mode_label)

self.mode_combo = QComboBox()
self.mode_combo.addItems([self.MODE_SKILL, self.MODE_QA, self.MODE_CHAT])

# 扁平简约风格样式
self.mode_combo.setStyleSheet("""
    QComboBox {
        background-color: #FFFEF9;
        border: 1px solid #E8DFD5;
        border-radius: 6px;
        padding: 4px 8px;
        color: #4A3F35;
        min-width: 100px;
    }
    QComboBox:hover {
        background-color: #FDF8F0;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #8B5A2B;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFEF9;
        border: 1px solid #E8DFD5;
        border-radius: 6px;
        padding: 4px;
        selection-background-color: #FDF6ED;
        selection-color: #8B5A2B;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        padding: 4px 8px;
        min-height: 24px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #FDF8F0;
    }
""")

mode_layout.addWidget(self.mode_combo)
```

**Step 2: 运行应用验证视觉效果**

Run: `D:\ProgramData\miniconda3\envs\noteasskill\python.exe main.py`

Expected: 下拉框显示扁平简约风格，弹出列表无黑底，背景为象牙白

**Step 3: 提交**

```bash
git add app/widgets/chat_panel.py
git commit -m "style: 下拉框改为扁平简约风格"
```

---

### Task 3: 运行功能测试验证

**Files:**
- Test: `tests/test_functional.py`

**Step 1: 运行功能测试**

Run: `D:\ProgramData\miniconda3\envs\noteasskill\python.exe tests/test_functional.py`

Expected: 所有 56 个测试通过

**Step 2: 更新版本号**

修改 `version.txt`:
```
v0.2.7
```

**Step 3: 提交并推送**

```bash
git add version.txt
git commit -m "chore: 更新版本号至 v0.2.7"
git push origin main
```

---

## 验收清单

- [ ] 展开/闭合按钮显示为三角形，无黑底
- [ ] 下拉框弹出列表无黑底，背景为象牙白
- [ ] hover 状态有正确的颜色反馈
- [ ] 所有功能测试通过
- [ ] 版本号已更新