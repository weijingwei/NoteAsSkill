---
name: dev-tools-installation
description: |
  记录并指导开发环境核心工具的安装流程，涵盖 trea、claude code 和 cc-switch。
  适用于新环境初始化、开发工具配置或工作记录归档的场景。
  该技能确保关键开发工具能够正确部署并投入使用。
allowed-tools: [Read, Write, Bash]
parameters:
  - name: tools_list
    type: array
    description: 需要安装的工具列表，默认包含笔记中记录的三个工具
    required: false
    default: ["trea", "claude code", "cc-switch"]
  - name: log_output
    type: string
    description: 安装日志的输出路径
    default: "./install.log"
returns:
  type: object
  description: 包含安装状态、版本信息和错误日志的报告对象
---

## 概述

本技能基于工作记录，提供了 trea、claude code 和 cc-switch 三个开发工具的安装指南。它旨在帮助快速复现开发环境配置，确保工作流的连续性。

## 使用场景

- 新工作站或服务器的环境初始化
- 重新配置或修复损坏的开发工具链
- 记录和归档环境配置步骤

## 详细步骤

根据工作记录，安装流程如下：

1. **安装 trea**
   执行 trea 的安装程序或包管理命令。
   ```bash
   # 示例命令，具体视 trea 官方文档而定
   brew install trea 
   ```

2. **安装 claude code**
   部署 Claude Code CLI 工具，确保环境变量配置正确。
   ```bash
   # 示例安装脚本
   npm install -g @anthropic/claude-code
   ```

3. **安装 cc-switch**
   配置 cc-switch 工具用于环境切换或配置管理。
   ```bash
   # 示例安装流程
   git clone [cc-switch-repo]
   cd cc-switch && ./install.sh
   ```

## 示例

以下是一次完整的安装验证流程：

```bash
# 检查工具是否安装成功
trea --version
claude-code --version
cc-switch --status

echo "所有工具安装完成"
```

## 注意事项

- 请确保网络连接稳定，部分工具可能需要访问海外资源。
- 建议在安装前更新系统的包管理器（如 brew, apt, npm）。
- 如果安装过程中断，请检查依赖项是否满足要求。