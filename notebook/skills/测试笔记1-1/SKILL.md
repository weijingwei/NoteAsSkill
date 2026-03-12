---
name: aliyun-coding-plan-guide
description: |
  阿里云百炼 Coding Plan 的配置与使用指南。
  涵盖套餐详情、模型选择、专属 API Key 配置以及使用规范，旨在帮助用户在 AI 编程工具（如 Claude Code）中低成本接入顶级大模型。
  适用于已订阅或计划订阅 Coding Plan 的开发者进行环境配置与问题排查。
allowed-tools: [Read, Write, Bash]
parameters:
  - name: subscription_tier
    type: string
    description: 订阅套餐类型
    default: "Lite"
  - name: target_tool
    type: string
    description: 目标 AI 编程工具名称（如 Claude Code）
    required: true
returns:
  type: object
  description: 配置指导信息、用量限制说明及合规警告
---

## 概述

Coding Plan 是阿里云百炼推出的 AI 编程订阅服务，整合了千问、GLM、Kimi、MiniMax、DeepSeek 等顶级模型。通过固定月费模式，用户可以以远低于常规 API 的成本在主流 AI 编程工具中使用这些模型，同时规避按量付费的欠费风险。

本技能文档提供了 Coding Plan 的核心配置信息、套餐详情及关键的合规使用须知。

## 使用场景

-   **配置 AI 编程工具**：需要将 Claude Code 或 OpenClaw 等工具接入 Coding Plan 服务。
-   **模型选型**：根据任务需求（如图片理解）选择合适的模型。
-   **额度管理**：监控请求次数，避免超出套餐限制。
-   **排查扣费异常**：解决订阅后仍显示欠费或被额外扣费的问题。

## 详细步骤

### 1. 获取凭证与配置

要使用 Coding Plan，必须配置**专属 API Key** 和 **Base URL**，不可使用百炼通用凭证。

1.  **访问控制台**：前往 [Coding Plan 页面](https://bailian.console.aliyun.com/cn-beijing/?tab=model#/efm/coding_plan) 订阅套餐并获取凭证。
2.  **识别凭证特征**：
    *   **API Key**：必须以 `sk-sp-` 开头。
    *   **Base URL**：必须包含 `coding.dashscope.aliyuncs.com`。
3.  **配置示例（环境变量）**：
    ```bash
    # 示例配置，请替换为实际的 Key
    export DASHSCOPE_API_KEY="sk-sp-xxxxxxxxxxxxxx"
    export DASHSCOPE_BASE_URL="https://coding.dashscope.aliyuncs.com"
    ```

### 2. 模型选择建议

Coding Plan 支持多种顶级模型，推荐使用以下模型以获得最佳体验：

-   **qwen3.5-plus**：支持图片理解，综合能力强。
-   **kimi-k2.5**：支持图片理解，长上下文表现出色。
-   **deepseek-v3.2**：代码生成能力强。
-   **其他模型**：glm-5, MiniMax-M2.5, qwen3-max, qwen3-coder-plus 等。

### 3. 套餐额度管理

请根据订阅的套餐注意请求频率限制，避免触发限流。

| 套餐类型 | 价格 | 5小时限制 | 周限制 | 月限制 |
| :--- | :--- | :--- | :--- | :--- |
| **Lite 基础套餐** | ¥ 40/月 | 1,200 次 | 9,000 次 | 18,000 次 |
| **Pro 高级套餐** | ¥ 200/月 | 6,000 次 | 45,000 次 | 90,000 次 |

> **消耗说明**：单次提问按“模型调用次数”扣除额度。简单任务约 5-10 次，复杂任务约 10-30+ 次。

## 注意事项

### ⚠️ 严禁违规使用

Coding Plan **仅限在编程工具中交互式使用**，违规将导致封禁：

-   ✅ **允许**：Claude Code、OpenClaw 等 AI 编程辅助工具。
-   ❌ **禁止**：自动化脚本、自定义应用程序后端、非交互式批量调用、API 直接集成。

### ⚠️ 扣费异常排查

如果订阅后仍显示欠费或被扣费，通常是因为配置错误：
1.  检查是否误用了百炼通用 API Key（非 `sk-sp-` 开头）。
2.  检查 Base URL 是否正确（必须包含 `coding.dashscope.aliyuncs.com`）。

### ⚠️ 数据与账号规范

-   **数据授权**：使用期间，输入与生成内容将用于阿里云服务改进与模型优化。
-   **账号安全**：套餐仅限订阅人专享，禁止共享账号。
-   **退款政策**：服务不支持退款，订阅前请务必确认需求。