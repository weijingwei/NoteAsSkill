"""文件夹 SKILL 生成策略模块

使用策略模式实现不同的 SKILL 生成方式。
支持运行时切换生成策略，易于扩展新的生成模式。

设计模式：策略模式 (Strategy Pattern)
- 将算法封装在独立的策略类中
- 客户端可以动态选择策略
- 新增策略无需修改现有代码

优势：
- 开闭原则：新增生成模式只需添加新策略类
- 单一职责：每个策略类只负责一种生成方式
- 运行时切换：可根据配置动态选择策略

使用方式：
    # 获取策略
    strategy = FolderSkillStrategyFactory.get("hybrid")
    
    # 使用策略生成内容
    content = strategy.generate(folder, note_summaries, folder_summaries, ai_client)
    
    # 注册新策略
    FolderSkillStrategyFactory.register(CustomStrategy())
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class NoteSummary:
    """笔记摘要数据类
    
    用于存储从笔记 SKILL.md 中提取的摘要信息。
    """
    id: str
    title: str
    description: str = ""


@dataclass
class FolderSummary:
    """文件夹摘要数据类
    
    用于存储从子文件夹 SKILL.md 中提取的摘要信息。
    """
    name: str
    description: str = ""
    skill_hash: str = ""


class FolderSkillStrategy(ABC):
    """文件夹 SKILL 生成策略基类
    
    定义了所有生成策略的公共接口。
    子类必须实现 generate() 方法和 name 属性。
    
    设计模式：策略模式中的抽象策略 (Strategy) 角色
    """
    
    @abstractmethod
    def generate(
        self,
        folder_name: str,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
        ai_client: Any = None
    ) -> str:
        """生成 SKILL.md 内容
        
        Args:
            folder_name: 文件夹名称
            note_summaries: 子笔记摘要列表
            folder_summaries: 子文件夹摘要列表
            ai_client: AI 客户端（可选，某些策略需要）
            
        Returns:
            SKILL.md 内容字符串
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称
        
        用于在工厂中注册和获取策略。
        """
        pass
    
    def _build_front_matter(
        self,
        folder_name: str,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
        description: str = ""
    ) -> dict:
        """构建 YAML front matter
        
        Args:
            folder_name: 文件夹名称
            note_summaries: 子笔记摘要列表
            folder_summaries: 子文件夹摘要列表
            description: 描述文本
            
        Returns:
            front matter 字典
        """
        front_matter = {
            "name": f"folder-{folder_name}",
            "type": "folder",
            "children": {
                "notes": [
                    {"id": s.id, "title": s.title, "summary": s.description}
                    for s in note_summaries
                ],
                "folders": [
                    {"name": s.name, "summary": s.description}
                    for s in folder_summaries
                ],
            },
        }
        if description:
            front_matter["description"] = description
        return front_matter
    
    def _format_content(
        self,
        front_matter: dict,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
        overview: str = ""
    ) -> str:
        """格式化最终内容
        
        Args:
            front_matter: YAML front matter 字典
            note_summaries: 子笔记摘要列表
            folder_summaries: 子文件夹摘要列表
            overview: 概述文本
            
        Returns:
            完整的 SKILL.md 内容
        """
        content = "---\n"
        content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
        content += "---\n\n"
        
        if overview:
            content += f"## 概述\n\n{overview}\n\n"
        
        if note_summaries:
            content += "## 子笔记\n"
            for s in note_summaries:
                content += f"- [{s.title}](../skills/{s.id}/)"
                if s.description:
                    content += f" - {s.description}"
                content += "\n"
            content += "\n"
        
        if folder_summaries:
            content += "## 子文件夹\n"
            for s in folder_summaries:
                content += f"- [{s.name}](./{s.name}/)"
                if s.description:
                    content += f" - {s.description}"
                content += "\n"
        
        return content


class SimpleStrategy(FolderSkillStrategy):
    """简单策略：纯规则聚合，不使用 AI
    
    特点：
    - 速度快，无网络请求
    - 输出结构化，可预测
    - 适合离线环境或大量处理
    """
    
    @property
    def name(self) -> str:
        return "simple"
    
    def generate(
        self,
        folder_name: str,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
        ai_client: Any = None
    ) -> str:
        front_matter = self._build_front_matter(
            folder_name, note_summaries, folder_summaries
        )
        return self._format_content(front_matter, note_summaries, folder_summaries)


class AIStrategy(FolderSkillStrategy):
    """AI 策略：完全由 AI 生成描述
    
    特点：
    - 生成的描述更自然、更有洞察力
    - 需要网络请求和 API 调用
    - 适合需要高质量描述的场景
    """
    
    @property
    def name(self) -> str:
        return "ai"
    
    def generate(
        self,
        folder_name: str,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
        ai_client: Any = None
    ) -> str:
        if not ai_client or (not note_summaries and not folder_summaries):
            return SimpleStrategy().generate(
                folder_name, note_summaries, folder_summaries, ai_client
            )
        
        prompt = self._build_prompt(folder_name, note_summaries, folder_summaries)
        
        try:
            ai_description = ai_client.chat([{"role": "user", "content": prompt}])
            ai_description = ai_description.strip()
        except Exception:
            return SimpleStrategy().generate(
                folder_name, note_summaries, folder_summaries, ai_client
            )
        
        front_matter = self._build_front_matter(
            folder_name, note_summaries, folder_summaries, ai_description
        )
        return self._format_content(
            front_matter, note_summaries, folder_summaries, ai_description
        )
    
    def _build_prompt(
        self,
        folder_name: str,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary]
    ) -> str:
        """构建 AI 提示词"""
        prompt = f"这是一个名为「{folder_name}」的文件夹，包含以下内容：\n\n"
        
        if note_summaries:
            prompt += "笔记：\n"
            for s in note_summaries:
                prompt += f"- {s.title}"
                if s.description:
                    prompt += f"：{s.description}"
                prompt += "\n"
            prompt += "\n"
        
        if folder_summaries:
            prompt += "子文件夹：\n"
            for s in folder_summaries:
                prompt += f"- {s.name}"
                if s.description:
                    prompt += f"：{s.description}"
                prompt += "\n"
        
        prompt += "\n请生成一段 100-200 字的概要描述，说明这个文件夹的主题和内容组织。只返回描述文字，不要其他内容。"
        return prompt


class HybridStrategy(AIStrategy):
    """混合策略：规则生成结构，AI 生成描述
    
    特点：
    - 结合了简单策略的速度和 AI 策略的质量
    - 结构化输出，描述自然
    - 推荐的默认策略
    """
    
    @property
    def name(self) -> str:
        return "hybrid"


class FolderSkillStrategyFactory:
    """文件夹 SKILL 策略工厂
    
    管理和创建不同的生成策略。
    使用注册机制，支持运行时扩展。
    
    设计模式：工厂模式 (Factory Pattern)
    - 封装策略创建逻辑
    - 支持动态注册新策略
    """
    
    _strategies: dict[str, FolderSkillStrategy] = {}
    
    @classmethod
    def register(cls, strategy: FolderSkillStrategy) -> None:
        """注册策略
        
        Args:
            strategy: 策略实例
        """
        cls._strategies[strategy.name] = strategy
    
    @classmethod
    def get(cls, name: str) -> FolderSkillStrategy:
        """获取策略实例
        
        Args:
            name: 策略名称
            
        Returns:
            策略实例
            
        Raises:
            ValueError: 未知的策略名称
        """
        if name not in cls._strategies:
            raise ValueError(
                f"Unknown strategy: {name}. "
                f"Available strategies: {list(cls._strategies.keys())}"
            )
        return cls._strategies[name]
    
    @classmethod
    def get_available_strategies(cls) -> list[str]:
        """获取可用策略列表
        
        Returns:
            策略名称列表
        """
        return list(cls._strategies.keys())
    
    @classmethod
    def is_strategy_available(cls, name: str) -> bool:
        """检查策略是否可用
        
        Args:
            name: 策略名称
            
        Returns:
            是否已注册
        """
        return name in cls._strategies


FolderSkillStrategyFactory.register(SimpleStrategy())
FolderSkillStrategyFactory.register(AIStrategy())
FolderSkillStrategyFactory.register(HybridStrategy())
