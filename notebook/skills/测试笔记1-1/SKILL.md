---
您好！我注意到您提供的笔记内容是空白模板（"在此输入笔记内容..."），没有实际的技术内容。

我无法为空白笔记生成有意义的 SKILL.md 文件。

**请您提供实际的笔记内容**，例如：
- 某个技术操作流程
- API 使用说明
- 代码片段和用法
- 工具配置指南
- 问题解决方案

---

### 示例：如果您提供这样的笔记

```markdown
# Git 分支管理

创建新分支：git checkout -b feature/login
合并分支：git merge feature/login
删除已合并分支：git branch -d feature/login
```

我将生成对应的 SKILL.md：

```markdown
---
name: git-branch-management
description: |
  Git 分支管理操作指南。
  包含创建、合并、删除分支等常用命令。
  适用于日常开发中的版本控制场景。
allowed-tools: [Bash]
parameters:
  - name: branch_name
    type: string
    description: 分支名称
    required: true
  - name: action
    type: string
    description: 操作类型
    default: create
returns:
  type: string
  description: 操作结果状态
---

## 概述
Git 分支管理技能，帮助开发者高效管理代码版本。

## 使用场景
- 开发新功能时创建特性分支
- 功能完成后合并到主分支
- 清理已合并的分支

## 详细步骤
1. **创建分支**
   ```bash
   git checkout -b feature/login
   ```
2. **合并分支**
   ```bash
   git merge feature/login
   ```

## 注意事项
- 合并前确保代码已提交
- 删除分支前确认已合并
```

---

**请提供您的实际笔记内容，我将为您生成完整的 SKILL.md 文件。**