# Penpot首次登录引导：已推送、拉取并上线

2026-11-10，Asia/Shanghai。**交付通过**。最终bkcode/penpot main与VM250干净源码为`8a9b96154d9dd81dcc373155ae30dba094127cc8`；frontend image `sha256:6cbd1f7f3b90b77b3dcd4f6a65fa9c117861d2de0781df22bd8bad40f19c61bc`，11healthy。全新浏览器原预填登录直接进入项目列表，欢迎/调研/团队引导不显示，Puyu项目可见。

[使用手册](usage-manual.md)、[五项验收](acceptance.json)、[v2构建/非root读检](v2-prepare-status.json)、[实际应用](v2-applied.json)、[真实浏览器](browser-acceptance.json)、[最终原生后检](final-postcheck.json)。用户[明确推送授权](push-approved-and-verified.json)解除初次AGENTS冲突；首轮ec已推但启动失败，后续8a权限修正并非全栈升级。

首次0600诊断、恢复原ff11healthy、仅重置unit失败计数等原始证据保留。source-state-before-approval为最初未授权阶段；prepare-status-first/apply-status*/startup-diagnostic-first为ec失败阶段；old-service-restored为实际恢复证明；v2-*及final-postcheck才是当前成功交付。独立rollback receipt缺失不伪造，不将历史pending/失败回执覆盖成成功。

只变更VM250，其他10镜像、身份/秘密/资产聚合/DB对象数保持；Puyu3页58240图形19组件仍可读。原文件未逐像素重验。完整设计、密码及其hash、归档和截图不进入Git。
