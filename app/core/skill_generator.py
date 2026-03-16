"""SKILL.md 生成模块

负责从笔记内容自动生成 SKILL.md 文件。
"""

import re
import sys
from pathlib import Path
from typing import Any

import yaml

from .note_naming import name_to_skill_name


class SkillGenerator:
    """SKILL.md 生成器"""

    # 生成完整 SKILL.md 的提示词
    GENERATION_PROMPT = """你是一个专业的技术文档助手，专门为 Claude Code 生成 SKILL.md 文件。

SKILL.md 是一个结构化的技能描述文件，用于让 AI 助手理解和使用这篇笔记作为知识库。

请根据以下笔记内容，生成一个完整的 SKILL.md 文件。

## 笔记内容
{content}

## SKILL.md 格式要求

SKILL.md 由两部分组成：

### 1. YAML Front Matter（必须）

```yaml
---
name: skill-name-in-kebab-case
description: |
  多行描述，详细说明这个技能的用途、适用场景和核心功能。
  至少 2-3 句话，帮助 AI 理解何时使用这个技能。
allowed-tools: [Read, Write, Bash]  # 推荐使用的工具列表
parameters:
  - name: param1
    type: string
    description: 参数描述
    required: true
  - name: param2
    type: string
    description: 参数描述
    default: "default_value"
returns:
  type: object
  description: 返回值描述
---
```

### 2. 正文内容（必须）

正文应包含：
- **概述**：简要说明这个技能的目的
- **使用场景**：什么时候应该使用这个技能
- **详细步骤**：如果有流程，按步骤说明
- **示例**：提供具体的使用示例
- **注意事项**：重要的限制或注意事项

## 输出要求

请直接输出完整的 SKILL.md 内容（包含 YAML front matter 和正文），不要包含其他解释。

## 示例输出

```markdown
---
name: python-data-cleaning
description: |
  使用 Pandas 清洗 CSV 数据的完整指南。
  包含处理缺失值、重复数据、数据类型转换等常用操作。
  适用于需要对原始数据进行预处理的场景。
allowed-tools: [Read, Write, Bash]
parameters:
  - name: data_source
    type: string
    description: 数据源路径，支持本地文件路径或 URL
    required: true
  - name: output_format
    type: string
    description: 输出格式
    default: csv
returns:
  type: DataFrame
  description: 清洗后的 Pandas DataFrame
---

## 概述

这个技能提供了一个完整的数据清洗流程，帮助你处理原始数据中的常见问题。

## 使用场景

- 数据包含缺失值需要填充或删除
- 存在重复记录需要去重
- 数据类型不一致需要转换
- 列名不规范需要重命名

## 详细步骤

1. **读取数据**
   ```python
   import pandas as pd
   df = pd.read_csv(data_source)
   ```

2. **处理缺失值**
   ```python
   df = df.dropna()  # 删除缺失值
   # 或
   df = df.fillna(0)  # 填充缺失值
   ```

3. **去除重复数据**
   ```python
   df = df.drop_duplicates()
   ```

## 注意事项

- 大文件处理时注意内存使用
- 建议先备份原始数据
```

现在请根据上面的笔记内容，生成完整的 SKILL.md：
"""

    def __init__(self, ai_client: Any = None):
        """初始化 SKILL 生成器

        Args:
            ai_client: AI 客户端实例
        """
        self.ai_client = ai_client

    def set_ai_client(self, client: Any) -> None:
        """设置 AI 客户端

        Args:
            client: AI 客户端实例
        """
        self.ai_client = client

    def generate_skill_md(self, content: str, use_ai: bool = True, note_title: str = "") -> str:
        """生成 SKILL.md 内容

        Args:
            content: 笔记内容
            use_ai: 是否使用 AI 生成
            note_title: 笔记标题（用于设置 name 字段）

        Returns:
            SKILL.md 内容
        """
        if use_ai and self.ai_client is not None:
            return self._generate_with_ai(content, note_title)
        else:
            return self._generate_simple(content, note_title)

    def _generate_with_ai(self, content: str, note_title: str = "") -> str:
        """使用 AI 生成 SKILL.md"""
        try:
            prompt = self.GENERATION_PROMPT.format(content=content)
            response = self.ai_client.chat([{"role": "user", "content": prompt}])

            # 清理响应
            response = response.strip()

            # 移除可能的 markdown 代码块标记
            if response.startswith("```markdown"):
                response = response[11:]
            elif response.startswith("```"):
                response = response[3:]

            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            # 确保以 --- 开头
            if not response.startswith("---"):
                response = "---\n" + response

            # 如果提供了笔记标题，替换 name 字段
            if note_title:
                skill_name = name_to_skill_name(note_title)
                # 尝试替换 YAML 中的 name 字段
                response = re.sub(
                    r'^name:\s*\S+',
                    f'name: {skill_name}',
                    response,
                    flags=re.MULTILINE
                )

            return response

        except Exception as e:
            try:
                print(f"AI generation failed: {e}")
            except UnicodeEncodeError:
                # Windows 控制台编码问题，使用 stderr 输出
                print(f"AI generation failed: {e}", file=sys.stderr)
            return self._generate_simple(content, note_title)

    def _generate_simple(self, content: str, note_title: str = "") -> str:
        """简单规则生成 SKILL.md"""
        # 使用笔记标题或从内容中提取标题
        if note_title:
            title = note_title
            # 使用笔记标题生成 name
            name = name_to_skill_name(note_title)
        else:
            # 提取标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else "untitled"
            # 生成 name（slug 化）
            name = title.lower()
            name = re.sub(r"[^\w\u4e00-\u9fff-]", "-", name)
            name = re.sub(r"-+", "-", name)
            name = name.strip("-") or "untitled"

        # 提取描述（前 200 字）
        text = re.sub(r"#.*?\n", "", content)
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`]+`", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"[*_~]", "", text)
        text = text.strip()

        description = text[:200].strip()
        if len(text) > 200:
            description += "..."

        # 构建简单的 SKILL.md
        skill_md = f"""---
name: {name}
description: |
  {description}
allowed-tools: [Read, Write, Bash]
---

## 概述

{title}

## 详细内容

{content}
"""
        return skill_md

    def generate_and_save(self, note_id: str, note_content: str, skill_path: Path, use_ai: bool = True, note_title: str = "") -> bool:
        """生成并保存 SKILL.md

        Args:
            note_id: 笔记 ID
            note_content: 笔记内容
            skill_path: SKILL.md 保存路径
            use_ai: 是否使用 AI 生成
            note_title: 笔记标题（用于设置 SKILL.md 中的 name 字段）

        Returns:
            是否成功
        """
        try:
            skill_content = self.generate_skill_md(note_content, use_ai=use_ai, note_title=note_title)

            skill_path.parent.mkdir(parents=True, exist_ok=True)
            with open(skill_path, "w", encoding="utf-8") as f:
                f.write(skill_content)

            return True

        except Exception as e:
            try:
                print(f"Failed to generate SKILL.md: {e}")
            except UnicodeEncodeError:
                print(f"Failed to generate SKILL.md: {e}", file=sys.stderr)
            return False


# 全局实例
_skill_generator: SkillGenerator | None = None


def get_skill_generator() -> SkillGenerator:
    """获取全局 SKILL 生成器实例"""
    global _skill_generator
    if _skill_generator is None:
        _skill_generator = SkillGenerator()
    return _skill_generator