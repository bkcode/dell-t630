# Penpot源码与更新

更新：2026-11-10（Asia/Shanghai）。VM250已从指定`bkcode/penpot/main`取固定提交并完成去首次引导部署，当前HEAD为`8a9b96154d9dd81dcc373155ae30dba094127cc8`、worktree clean。原“等待用户推两条提交”已由后续明确授权、推送与本次交付解除，不能继续作为当前阻塞。

## 来源与运行合同

| 项目 | 当前约定 |
| --- | --- |
| 应用仓库/分支 | [bkcode/penpot](https://github.com/bkcode/penpot)，显式main，不跟随默认分支 |
| 来宾origin/取码 | `https://github.com/bkcode/penpot.git`，公开HTTPS，无Git私钥/Token分发或agent forwarding |
| 来宾源码目录 | `/opt/dell/penpot/source`，真实目录，部署适配在源码外 |
| 部署commit | `8a9b96154d9dd81dcc373155ae30dba094127cc8`，保留37da782/ff1783e原登录改造 |
| frontend | `dell-penpot-frontend:2.18.5-8a9b96154d9d-amd64`；ID `sha256:6cbd1f7f3b90b77b3dcd4f6a65fa9c117861d2de0781df22bd8bad40f19c61bc` |
| 运行版本范围 | 固定官方2.18.5 base的selfhost wrapper新建；其它10镜像保持，不是完整2.19编译/全栈升级 |
| 实例 | VM250/192.168.19.50，入口 [http://192.168.19.50:9001/](http://192.168.19.50:9001/) |
| 监督 | 原`dell-penpot.service` notify监督，source/公开文件/11镜像/mount/资源锁持续保留 |

## 首次登录引导已关闭：当前main/8a9b9615

当前部署提交为`8a9b96154d9dd81dcc373155ae30dba094127cc8`，main工作树clean；frontend为`sha256:6cbd1f7f3b90b77b3dcd4f6a65fa9c117861d2de0781df22bd8bad40f19c61bc`（`dell-penpot-frontend:2.18.5-8a9b96154d9d-amd64`）。只重建固定官方2.18.5 base上的selfhost wrapper，其余10个镜像不变；没有编译完整2.19套件或迁移数据库。Git-owned入口追加官方`disable-onboarding`再exec原官方入口/CMD，关闭首次调研、首次团队设置及自动版本说明，保留手动创建团队与原登录表单/默认填入。

[17:41应用](../../evidence/penpot-onboarding-20261110/v2-applied.json)确认新source与frontend切换、11healthy、其它10镜像及受保护私有文件/素材/对象计数保持；[17:44真实浏览器](../../evidence/penpot-onboarding-20261110/browser-acceptance.json)从原表单预填登录进入dashboard，`disable-onboarding`为true、引导元素0、欢迎及首次团队设置均未出现、Puyu项目可见、无Internal Error。截图仅private且已人工视觉复核，测试cookies/localStorage已清、session关闭，没有修改profile或设计。

[17:46最终后检](../../evidence/penpot-onboarding-20261110/final-postcheck.json)再次确认HEAD/clean、11healthy且镜像match lock、unit active与监督check通过、原生flags启用、Puyu仍3页/58,240图形/19组件；未授权Docker伪造头请求403。应用回执中的browser pending仅是17:41阶段状态，已由随后浏览器证据补齐，不改写历史回执。

## 首轮失败与恢复历史

用户在风险说明后明确“进行推送”，[授权/非force推送复核](../../evidence/penpot-onboarding-20261110/push-approved-and-verified.json)记录main由9aed先到ec6f，保留37da/ff两条原登录改造。ec6f首次prepare通过后实际启动失败：[诊断](../../evidence/penpot-onboarding-20261110/startup-diagnostic-first.json)显示umask077产生0600公开文件，Docker COPY保留该权限，penpot UID无法读取wrapper；不能将该候选称为成功上线。

[旧服务恢复实证](../../evidence/penpot-onboarding-20261110/old-service-restored.json)随后确认ff与11healthy，专门rollback receipt缺失如实保留；[失败速率计数复位](../../evidence/penpot-onboarding-20261110/recovery-rate-limit-reset.json)没有删除日志或关闭guard。修复commit8a为四项COPY显式加`--chmod=0644`，[v2准备](../../evidence/penpot-onboarding-20261110/v2-prepare-status.json)增加UID1001对wrapper/JS/CSS/conf的可读检查，通过后才切换。旧ff/9aed证据、首次失败及恢复证据仍保留，不冒称首次部署即成功。

## 历史版本与凭据

[13:18管理Mac专属Deploy Key读取](../../evidence/git-repositories-20261110/penpot-deploy-key-verification.json)当时main为9aedbb011cd803eb615225ca21f7f47cb8c2fa09；[13:20来宾只读](../../evidence/git-repositories-20261110/penpot-runtime-readonly.json)为ff1783e7865af7aae571c985f03e057631b7af63、clean、无origin、11healthy。此二者与[原部署等待](../../evidence/git-repositories-20261110/penpot-deployment-state.json)、[批准前source-state](../../evidence/penpot-onboarding-20261110/source-state-before-approval.json)均保留时间意义，不能把9aed当回退目标、把当时noorigin当现况。初装[Git事实](../../infra/penpot/git-source-facts.json)与[混合运行来源](../../infra/penpot/application/git-runtime-provenance.json)仍解释旧bundle/worker/import的归因。

管理Mac仓库专属`penpot_ed25519`/.pub位于`~/.ssh/deploy-keys/bkcode/`，此前只验证SSH读取；本次按用户明确授权推送，来宾部署使用公开HTTPS。私钥/Token不入源码、build context、URL、普通文档或Git，不复制服务器其他身份。未来仍只部署审核后可从指定main取得的固定commit，不把当前授权扩为自动pull/upgrade或其它仓库push。

## 默认填入与设计数据保持

16:06[明确授权](../../evidence/penpot-login-prefill-20261110/explicit-approval.json)允许LAN21/24、WG10.66.66/24、self19.50/loopback未登录访客读取原owner账号密码并默认填入。原helper/表单保持，guest0600私有JSON、来源ACL/no-store与query-safe日志均随此次部署保留；CF19.5/其它来源拒绝，17:46Docker伪造头负测仍403。实际密码/MCP身份不改、不输出值或hash。此前remember控件/localStorage方案已[撤回](../../evidence/penpot-browser-remember-20261110/README.md)，不作为现役；当前WG/CF端到端未签。16:13–16:19预填任务“ff/镜像不变”仅限当时阶段，不否定后续8a前端更新。

Puyu独立导入已完成：owner工作区新增puyu项目/文件后共8文件，旧7文件保持，3页/58,240图形/19组件。见[导入验收](../../evidence/penpot-puyu-import-20261110/acceptance.json)与[手册](../../evidence/penpot-puyu-import-20261110/usage-manual.md)。17:41部署核受保护私有文件、素材及对象计数保持，17:46核Puyu统计；不把这扩签逐像素、全部原型、MCP写入或完整恢复。原3设计/971媒体/973资产数是初装基线，不删除合法新增内容凑数。

## 后续维护

后续先fresh核HEAD/clean、origin/main、数据UUID、有效19网公开文件及11镜像锁，再在独立候选取固定commit。仅变化的构建context重建，公开静态文件显式0644并以运行UID验证可读；变更锁与源码必须停原监督unit后精确CAS切换，不绕过guard。失败保新证据，恢复相容的旧软件和公开配置，不回写旧DB/素材覆盖现有数据。不得重跑fresh-init、旧source.env/身份复制或PG全库覆盖，不能将历史bootstrap当更新器。

资源与数据盘见[config.json](config.json)，机器可读源码合同见[git-source.json](git-source.json)，本次更新分析/历史见[PLAN](../../infra/penpot/source-update/PLAN.md)。其它机运行、Nexus合并、Java部署与自动备份范围不因本次改变。
