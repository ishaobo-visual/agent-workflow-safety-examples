# Agent Workflow Safety Examples

作者 / Maintainer：**shaoboooo** · 版本：**0.1.0** · 许可：**MIT**

独立可运行的业务工作流安全案例集。用8个合成场景演示暂停、分流、未知结果、局部返修、清理、回执与执行前状态检查。不是通用Agent平台，也不包含真实业务接口。

## 快速运行

需要Python 3.10或更高版本，仅使用标准库，无需安装依赖或配置账号。

```sh
python -B run_tests.py
```

Windows也可使用 `py -3 -B run_tests.py`。成功时退出码为0，打印测试数量和JSON结果；失败返回非0。不指定业务路径，不接受API密钥。运行器禁止测试中的socket网络操作和子进程调用。临时合成文件在测试结束后清理；不会扫描用户目录。

## 文件

- cases.json：8个场景、预期和具体测试映射。
- safety_examples.py：小型参考机制，含本地SQLite动作记录、固定路由、回执检查、单文件修订、可恢复缓存隔离。
- test_cases.py：正反例及独立SHA核对。
- run_tests.py：统一离线入口。
- LIMITATIONS.md：适用边界与未覆盖风险。
- SOURCES.md：概念来源、代码来源及署名与许可事项。
- VALIDATION.md、SHA256SUMS.txt：本版本的独立验证说明及文件校验值。

## 如何读结果

每个B编号对应cases.json中的一个业务场景。通过说明本参考实现对该合成输入符合断言，不证明任意Agent会理解自然语言、不证明真实平台幂等性，也不证明真实图像的像素或审美质量。

请将案例适配到自己的执行器，在自己的授权边界和合成环境中验证。不要把测试里的ACTIVE状态或虚构回执复制为生产授权。详细限制见LIMITATIONS.md。

## 许可与发布状态

Copyright (c) 2026 shaoboooo。代码和随附原创文档以 MIT 许可提供，完整条款见 [LICENSE](LICENSE)。相关外部项目仍遵循各自许可，本包不包含其代码。

本版本为 v0.1.0。正式发布状态与下载附件以仓库 Releases 页面为准。发布说明见 [CHANGELOG.md](CHANGELOG.md)，公开步骤见 [RELEASING.md](RELEASING.md)，贡献约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。
