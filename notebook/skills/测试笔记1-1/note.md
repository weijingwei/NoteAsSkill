Coding Plan 整合了千问、GLM、Kimi 、MiniMax、DeepSeek 顶级模型，并兼容主流AI编程工具。其折算成本远低于常规 API 调用，且通过固定月费模式有效防范了欠费风险。

## **快速开始**

访问[Coding Plan 页面](https://bailian.console.aliyun.com/cn-beijing/?tab=model#/efm/coding_plan)即可订阅并获取Coding Plan**专属API Key**，详情使用方法请参考[快速开始](https://help.aliyun.com/zh/model-studio/coding-plan-quickstart)。

## **套餐详情**

|     | **Lite 基础套餐** | **Pro 高级套餐** |
| --- | --- | --- |
| 支持的模型 | 推荐模型：**qwen3.5-plus**（支持图片理解）、**kimi-k2.5**（支持图片理解）、**glm-5**、**MiniMax-M2.5、deepseek-v3.2** 更多模型：qwen3-max-2026-01-23、qwen3-coder-next、qwen3-coder-plus、glm-4.7 |   |
| 价格  | **¥ 40**/月 | **¥ 200**/月 |
| 用量限制 | - 每 5 小时**1,200** 次请求 - 每周**9,000** 次请求 - 每月**18,000** 次请求 | - 每 5 小时**6,000** 次请求 - 每周**45,000** 次请求 - 每月**90,000** 次请求 |

-   **优惠活动：**最新活动详情，请以[活动页面](https://www.aliyun.com/benefit/scene/codingplan)信息为准。
    
-   **额度消耗：**单次提问将按实际“模型调用次数”扣除额度。简单任务约消耗 5-10 次，复杂任务约 10-30+ 次，实际消耗受任务难度、上下文及工具使用影响。在[Coding Plan 页面](https://bailian.console.aliyun.com/cn-beijing/?tab=model#/efm/coding_plan)可以查看用量。
    

## **订阅前须知**

Coding Plan 服务**不支持退款**。因此在订阅前请知悉以下重要内容：

1.  **严禁 API 调用**：仅限在编程工具（如 Claude Code、OpenClaw 等）中使用，禁止以 API 调用的形式用于自动化脚本、自定义应用程序后端或任何非交互式批量调用场景。**将套餐 API Key 用于允许范围之外的调用将被视为违规或滥用，可能会导致订阅被暂停或 API Key 被封禁。**
    
2.  **数据使用授权**：使用 Coding Plan 期间，模型输入以及模型生成的内容将用于服务改进与模型优化。停止使用 Coding Plan 服务可终止后续数据授权，但终止授权的范围不涵盖已授权使用的 Coding Plan 数据。详细条款请参见[阿里云百炼服务协议](https://terms.alicdn.com/legal-agreement/terms/common_platform_service/20230728213935489/20230728213935489.html?spm=5176.28197581.0.0.16e829a4HTC9FE)第 5.2 条。
    
3.  **账号使用规范**：套餐为订阅人专享使用，禁止共享。账号共享可能导致订阅权益受限。
    

## 常见问题

### 已购买 Coding Plan，为何仍显示欠费/被扣费？

误用了百炼通用 API Key 和 Base URL，系统会识别为按量付费，导致额外扣费。请改用 Coding Plan 专属 API Key（以`sk-sp-`开头）和专属 Base URL（含`coding.dashscope.aliyuncs.com`），配置方法请参见[获取套餐专属 API Key 和 Base URL](https://help.aliyun.com/zh/model-studio/coding-plan-quickstart#2782cf93b1w8h)。

更多问题请参考[常见问题](https://help.aliyun.com/zh/model-studio/coding-plan-faq)。