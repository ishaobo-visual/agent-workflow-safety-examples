# 来源与贡献边界

## 本包来源

8个案例抽象自多业务本地工作流维护中观察到的失败模式。公开内容全部重新构造为合成对象；没有复制工作区的业务数据、原始日志、内部状态文件或历史作品。本参考实现为本包重新编写，并非从外部项目移植代码。

## 概念相关项目（非依赖、非背书）

- n8n人工介入：工具执行前审批、暂停与决定边界。https://github.com/n8n-io/n8n-docs/blob/main/docs/build/integrate-ai/ai-examples/human-in-the-loop-for-tools.md
- Cloudflare Agents动作机制：持久动作状态、幂等标识、未知状态不盲目重试。https://github.com/cloudflare/agents/blob/main/docs/think/actions.md
- Temporal：持久工作流与去重模式。https://github.com/temporalio/temporal
- Promptfoo：场景、断言、回归案例组织方式。https://github.com/promptfoo/promptfoo
- Hypothesis：围绕不变量组织边界测试。本包使用确定性标准库测试，未使用该库或声称完成属性随机测试。https://github.com/HypothesisWorks/hypothesis

相关概念已有先例，本包不主张这些机制为首创；贡献点是紧凑、可离线复现的业务场景与证据边界。引用网页会演进，不构成锁定依赖。未复制外部源码，未包含第三方包或其许可文本。

## 署名与许可

项目作者及维护署名：shaoboooo。内容整理与参考实现使用了 AI 辅助；不据此声称所有机制原创或首创。

本包原创代码和文档采用 MIT 许可，见 LICENSE。外部项目仅用于概念出处说明，不构成依赖、代码移植或背书。发布者应只提交有权公开的贡献；后续引入第三方代码时须另行记录来源和适用许可。

## 视觉实践与原生派发补充的来源

三篇视觉文章根据作者的实际制作反馈重新整理为匿名文字，未附原图、内部版本ID、人物资料或原始请求。局部返修文章中的任务表是虚构示例。历史服务名称仅标识试验条件，不构成对其当前能力的验证或背书。

Native Dispatch Guard从本地原生应用控制器的锁、持久尝试与完成凭据模式中独立提炼，仅依赖Python标准库。测试使用合成字节和临时目录，没有复制第三方实现或真实生产回执。新增代码/文档沿本仓库shaoboooo署名和MIT许可。
