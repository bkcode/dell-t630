# Penpot浏览器记忆方案：已撤回历史

更新：2026-11-10（Asia/Shanghai）。用户随后明确要求保持原登录UI、不新增逻辑。此前可选checkbox/forget/localStorage方案已撤回，不再作为现役功能或使用指引。

[16:05恢复回执](restored-original.json)确认：原overlay与deployment lock已恢复，新增控件、localStorage逻辑、额外JS及两个挂载已撤回，11容器healthy；Penpot核心`main/ff1783e`、clean及镜像保持。恢复时原密码JSON尚未启用，未向公开证据输出实际密码。

## 历史阶段与最新授权

[prepared.json](prepared.json)、[review.md](review.md)、[change-started.json](change-started.json)与[applied.json](applied.json)只记录此前浏览器记忆候选的准备、代码审查及短暂应用阶段。代码/Node通过和11健康不代表该方案仍现役；它的真实浏览器完整验收未完成。不要据这些回执重放worker、要求用户勾选，或称用户浏览器已保存。

最早服务器共享密码预填曾因缺少明确暴露范围授权被自动审批拒绝；其旧prepared也不能直接回放。用户其后已[明确授权](../penpot-login-prefill-20261110/explicit-approval.json)原账户密码向指定未登录内网来源默认填入。当前方案恢复原ff helper与表单结构，仅配置原JSON的运行secret和来源ACL，不新增UI或保存逻辑；原UI默认填入已通过应用、原生后检与LAN浏览器验收，最新证据统一见[原UI默认填入](../penpot-login-prefill-20261110/README.md)。这次新授权不把先前未获授权的候选追认为已启用。

本目录保留历史证据，不含实际密码或秘密内容。owner/MCP/原设计不改，Git源码更新仍等待用户推既有两条改造的独立任务。
