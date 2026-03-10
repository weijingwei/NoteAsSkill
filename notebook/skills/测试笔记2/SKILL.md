---
name: ai-coding-toolchain-setup
description: |
  用于配置 AI 辅助开发环境的技能文档。
  记录并指导 Trae、Claude Code 和 cc-switch 的安装与配置流程。
  适用于快速搭建具备 AI 编程能力的开发工作站。
allowed-tools: [Bash, Read, Write]
parameters:
  - name: install_scope
    type: string
    description: 安装范围，可选 'all' 或单独工具名称（如 'claude-code'）
    required: false
    default: "all"
returns:
  type: object
  description: 包含各组件安装状态的报告对象
---

## 概述

本技能文档基于工作记录，总结了 Trae（AI IDE）、Claude Code（CLI 工具）以及 cc-switch（代理切换工具）的安装配置过程，旨在帮助用户快速复现该开发环境。

## 使用场景

- 在新机器上搭建 AI 辅助编程环境。
- 需要使用 Claude Code 进行代码生成和调试。
- 需要通过 cc-switch 管理多个 AI 模型代理。

## 详细步骤

### 1. Trae (Trea) 安装

Trae 是新一代 AI IDE。

*注意：笔记中记录为 "trea"，推测为 "Trae" 的笔误。*

```bash
# 通常通过官网下载安装包或使用包管理器
# 示例 (macOS):
# brew install --cask trae
```

### 2. Claude Code 安装

Claude Code 是 Anthropic 提供的终端 AI 助手。

```bash
# 使用 npm 全局安装
npm install -g @anthropic-ai/claude-code

# 验证安装
claude --version
```

### 3. cc-switch 安装

cc-switch 用于切换 Claude Code 的后端代理配置。

```bash
# 示例：从源码安装
git clone https://github.com/example/cc-switch.git
cd cc-switch
npm install
npm link
```

## 注意事项

- **环境依赖**：Claude Code 依赖 Node.js 环境，请确保 Node.js 版本 >= 18。
- **网络配置**：安装过程中可能需要访问国际网络，请确保代理配置正确。
- **名称辨析**：笔记中的 "trea" 已修正为 "Trae"，请在实际操作中注意区分。