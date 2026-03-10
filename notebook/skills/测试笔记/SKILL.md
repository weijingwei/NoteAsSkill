---
name: noteasskill
description: |
  创建一个名为 NoteAsSkill 的 Python 笔记应用，核心设计遵循 Claude Code Skill 目录结构。
  用户只需专注于编辑笔记内容，系统自动处理 SKILL.md 生成和目录结构管理。
  实现用户无感知的笔记到技能自动转换功能。
allowed-tools: [Read, Write, Bash]
parameters:
  - name: app_name
    type: string
    description: 应用名称，默认为 NoteAsSkill
    default: NoteAsSkill
  - name: conda_env
    type: string
    description: conda 环境名称
    default: noteasskill
  - name: python_version
    type: string
    description: Python 版本要求
    default: "3.10"
  - name: dependencies
    type: array
    description: 项目依赖列表
    default: ["markdown"]
returns:
  type: object
  description: 生成的应用文件结构
  properties:
    main_py: string
    config_yaml: string
    default_template: string
---

## 概述

NoteAsSkill 是一个创新性的 Python 笔记应用，它将每篇笔记自动转换为 Claude Code 可识别的技能。核心设计理念是"用户无感知"——用户只需专注于编辑 note.md 内容，所有 SKILL.md 生成、附件归档、目录结构管理等操作都在后台自动完成。

## 使用场景

- 需要创建一个笔记应用来管理知识库
- 希望笔记能够直接被 AI 助手作为技能使用
- 需要自动化的目录结构和元数据管理
- 构建个人或团队的知识技能库
- 实现"笔记即技能"的无缝转换

## 详细步骤

### 1. 环境准备

```bash
# 创建 conda 环境 (必须使用此环境)
conda create -n noteasskill python=3.10 -y
conda activate noteasskill
pip install markdown
```

### 2. 目录结构设计

系统自动维护以下目录结构（用户不可见）：

```
notebook/
├── .config.yaml           # 应用配置文件
├── skills/
│   └── note-title/        # 自动创建 (基于笔记标题)
│       ├── SKILL.md       # 自动更新 (用户不可见)
│       ├── note.md        # 用户编辑内容
│       └── attachments/   # 自动归档附件
└── templates/
    └── default.md         # 新笔记模板
```

### 3. 核心功能实现

**SKILL.md 自动生成逻辑**:
- 当用户保存 `note.md` 时自动触发
- 提取前 100 字作为 description
- 从代码块/参数列表自动提取 parameters
- 从返回描述自动提取 returns
- 生成结构化 SKILL.md

**附件自动归档逻辑**:
- 检测图片链接格式 `![alt](image.png)`
- 自动移动文件到 `attachments/` 目录
- 自动更新链接为 `![alt](attachments/image.png)`

**新笔记创建流程**:
- 用户点击"新建笔记"
- 基于 `templates/default.md` 生成初始内容
- 自动创建 `skills/note-title/` 目录
- 自动创建 `note.md` 和空 `SKILL.md`

### 4. 生成文件列表

1. **main.py** - 应用主入口，包含所有后台自动处理逻辑
2. **notebook/.config.yaml** - 应用配置文件
3. **notebook/templates/default.md** - 新笔记默认模板

## 示例

### 用户视角：编辑 note.md

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

### 系统自动处理

- 创建 `skills/python-data-cleaning/` 目录
- 自动生成 `SKILL.md` (完全在后台)
- 如有图片附件，自动归档到 `attachments/`

### 自动生成的 SKILL.md 示例

```yaml
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
```

## 注意事项

1. **用户无感知原则**: 所有 SKILL.md 生成和附件处理必须在后台自动完成，用户界面只显示 `note.md` 编辑器和预览区

2. **自动保存机制**: 编辑 `note.md` 时自动触发 SKILL.md 更新，无需用户手动操作

3. **错误处理**: 包含完整的文件路径检查和错误提示，确保文件操作安全

4. **环境要求**: 必须使用 `noteasskill` conda 环境，Python 版本 3.10+

5. **依赖管理**: 仅需 `markdown` 库，安装命令: `pip install markdown`

6. **关键点**: 用户在使用中**永远不会看到 SKILL.md 或目录结构**，所有处理在后台自动完成