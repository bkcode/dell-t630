# deploy-public CLI标准双环境与MCP dev-only

2026-11-10，Asia/Shanghai。**模式配置与保护行为验收通过，真实dev业务源码仍未就绪。** 源码main/213f1f42924f18e0d7b5848c2c1141a6230c1f5a已推送并VM220同步clean，Mac/Linux各65测试通过。CLI prod/main、dev/dev；MCP仍仅dev，真实发布关闭。

[4项验收](acceptance.json)、[源码交付](Git-delivery.json)、[VM配置更新](publisher-update.json)、[实际协议和源码保持](protocol-and-sources.json)、[最终后检](final-postcheck.json)、[本地回归](local-verification.json)、[操作说明](usage-manual.md)。

[上游只读审计](branch-audit-before.json)在VM220检查6个后端/公共库，main均存在、dev均缺失，工作树仍main/clean且HEAD保持。新MCP dev预检实际failed，原因origin/dev not prepared，这是保护行为符合设计，不是业务发布通过。prod覆盖与真实发布任务在执行前被拒绝；prod目标身份仍空。

先前[五服务成功](../deploy-public-publisher-20261110/mcp-protocol-and-preflight.json)属于初始dev→main阶段，保留历史，不证明新dev分支就绪。source_ready是目录身份，target_branch_available只代表本地origin引用；列出与预检不fetch，显式sync才获取，真实分支缺失不回退main。未创建/push/切换业务分支，未执行Go/Java构建、运行机SSH或业务上线。

MCP保持active/loopback18765，PID30260/NRestarts0；导航PID18640保持。私有配置ub600、Gitignored，原APIkey/路径/测试目标保持，构建挂载门禁通过。备份、Nexus、原发布私钥和旧链fenced范围不变。
