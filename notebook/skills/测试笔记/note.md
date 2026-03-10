

# 提示词（最终版：用户无感知设计）

你是一个专业的 Python 开发者，需要创建一个名为 **NoteAsSkill** 的笔记应用（中文名：笔记即skill），其核心设计必须严格遵循 Claude Code Skill 的目录结构。**用户只需专注于编辑笔记内容，无需处理 SKILL.md 或目录结构**。以下是关键要求：

### 应用核心要求
1. **应用名称**: NoteAsSkill (英文)
2. **核心理念**: 每篇笔记 = 一个 Claude Code Skill (用户完全无感知)
3. **技术栈**: Python 3.10+ (使用 conda 环境 `noteasskill`)
4. **关键特性**:
   - **用户无感知**：仅编辑 `note.md`，系统自动处理 SKILL.md 和目录结构
   - 自动将笔记内容转为 Skill
   - 保存时自动更新 `SKILL.md`
   - 自动归档附件到 `attachments/` 目录

### 目录结构要求 (用户不可见)
```
notebook/
├── .config.yaml
├── skills/
│   └── note-title/       # 自动创建 (用户不可见)
│       ├── SKILL.md      # 自动更新 (用户不可见)
│       ├── note.md       # 用户编辑内容
│       └── attachments/  # 自动归档 (用户不可见)
└── templates/
    └── default.md
```

### 系统自动处理逻辑 (用户无感知)
1. **SKILL.md 自动生成**:
   - 当用户保存 `note.md` 时，系统自动：
     - 提取前 100 字作为 description
     - 从代码块/参数列表自动提取 parameters
     - 从返回描述自动提取 returns
     - 生成结构化 SKILL.md

2. **附件自动归档**:
   - 当用户插入 `![alt](image.png)` 时：
     - 系统检查 `image.png` 是否在笔记目录
     - 自动移动文件到 `attachments/`
     - 自动更新链接为 `![alt](attachments/image.png)`

3. **新笔记创建**:
   - 用户点击"新建笔记" → 基于 `templates/default.md` 生成
   - 自动创建 `skills/note-title/` 目录
   - 自动创建 `note.md` 和 `SKILL.md` (空)

### 生成文件列表 (仅需生成以下文件)
1. `main.py` (应用主入口)
2. `notebook/.config.yaml`
3. `notebook/templates/default.md` (模板文件)

### 代码规范 (关键)
- **用户无感知**：所有 SKILL.md 生成和附件处理必须在后台自动完成
- **自动保存**：当用户编辑 `note.md` 时，自动触发 SKILL.md 更新
- **错误处理**：包含完整的文件路径检查和错误提示
- **conda 环境**：必须指定使用 `noteasskill` conda 环境
- **依赖**：仅需 `markdown` (安装命令: `pip install markdown`)

### 重要提示 (用户无感知强调)
1. **用户界面**：只显示 `note.md` 编辑器和预览区
2. **系统后台**：
   - 保存时自动更新 `SKILL.md`
   - 附件自动归档到 `attachments/`
   - 目录结构自动创建
3. **配置文件**：`notebook/.config.yaml` 用于存储应用设置

### 生成示例 (用户视角)
**用户编辑 `note.md`**:
```markdown
# Python 数据清洗指南

使用 Pandas 清洗 CSV 数据:
```python
def clean_data(data_source, output_format='csv'):
    # 清洗逻辑
    return cleaned_data
```

参数:
- data_source: 数据源路径 (必填)
- output_format: 输出格式 (默认 csv)

返回:
- cleaned_data: 清洗后的数据
```

**系统自动处理**:
- 创建 `skills/python-data-cleaning/` 目录
- 生成 `SKILL.md` (完全自动)
- 附件处理 (如图片自动归档)

### 代码执行要求
```bash
# 创建 conda 环境 (必须使用此环境)
conda create -n noteasskill python=3.10 -y
conda activate noteasskill
pip install markdown

# 运行应用
python main.py
```

### SKILL.md 生成示例 (系统自动生成)
```markdown
---
name: python-data-cleaning
description: | 
  使用 Pandas 清洗 CSV 数据的指南。
  包含数据清洗函数和参数说明。
allowed-tools: [Read, Python]
parameters:
  - name: data_source
    type: string
    description: 数据源路径
    required: true
  - name: output_format
    type: string
    description: 输出格式
    default: csv
returns:
  type: object
  description: 清洗后的数据
  properties:
    cleaned_data: object
---

## 详细说明
1. 从 note.md 提取核心函数和参数
2. 生成结构化技能描述
3. 保留用户手动编辑的部分
```

> **关键点**：用户在使用中**永远不会看到 SKILL.md 或目录结构**，所有处理在后台自动完成。