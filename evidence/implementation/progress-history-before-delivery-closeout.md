# 实施进展

更新：2026-11-06。**全套实施进行中，尚未最终签收。** 当前事实以本页、[plan.json](../../plan.json)、[验收索引](../../06-acceptance.md)及各执行证据为准。授权前过程已保存在[历史记录](../../evidence/implementation/progress-history-before-application-activation.md)，其中“待网络授权”“RAID重建中”不是当前状态。

## 已完成并有运行证据

- RAID已恢复：SSD RAID1、容量RAID5均Optl，五盘Onln、BBU Optimal；保留槽32:3历史故障待持续观察。见[恢复证据](../../evidence/implementation/raid-recovered.json)。
- 两个Debian13 AMD64核心模板：9010 Linux、9001 Docker；各两台完整克隆验证身份唯一、Cloud-Init和时间同步，无backing依赖。原101～106保留。
- 用户已明确批准四桥/转发/nft/LAN端口方案；主AI已应用。12台目标VM均运行于最终10.63私网，严格SSH主机密钥、ub、角色和IP已核对。见[网络应用](../../evidence/implementation/network-applied.json)、[独立网络检查](../../evidence/implementation/network-independent-verification.json)。
- 正式VM200 MySQL、VM201 Redis/RabbitMQ/Nacos，以及独立测试VM210四组件均健康，真实账号、最小权限、namespace越权拒绝和受控重启持久化通过；专属验收对象已清理。正式未导入本机业务行。见[正式数据](../../evidence/implementation/data-deployment-acceptance.json)、[测试数据](../../evidence/implementation/test-data-deployment.json)。
- VM240五服务最新JAR已核对并stage。测试18张结构表及合成管理员初始化完成；六份Nacos配置发布及完整摘要核对通过；首次激活发现Gateway redisTemplate定义冲突，失败已保留；隔离副本显式Import修复通过真实类红/绿回归，主AI复核162嵌入库未变。新release20261106T113449五服务已全部UP，正在业务验收。见[stage](../../evidence/implementation/java-test-stage.json)、[初始化](../../evidence/implementation/java-test-init.json)、[Nacos](../../evidence/implementation/java-test-nacos.json)。
- Ops270四组件已真实健康、Grafana新管理员认证和专属dashboard重启持久化通过。Prometheus实际抓取12台来宾；PVE只读采集通过现有QGA推送，无宿主新监听端口；RAID指标、采集时间及12条告警规则实际加载通过。见[监控](../../evidence/implementation/ops-health.json)、[持久化](../../evidence/implementation/ops-persistence-test.json)、[宿主指标查询](../../evidence/implementation/ops-pve-metrics-live-query.json)。
- 发布机220工具链已就绪：Java21、Git、rsync、Python、Node22、两版pnpm和MCP SDK。发布账户/受限发布链与回滚还要单独验收。
- NAS260 OMV8安装、强管理员密码、原ub密钥与网络接管通过；主AI验证QGA往返成功。共享、媒体盘和Jellyfin仍由子AI完成，不据此宣称播放通过。

## 正在推进

1. VM240五服务真实启动已通过，继续登录、角色/权限、验证码及合成文件持久化。
2. Penpot按用户最新选择从改造过的Git精确版本部署，数据采用应用导出/导入，目标使用全新身份；Nexus采用独立新实例和仓库制品导入。Mac源保持。
3. OMV专用空2TiB虚拟盘、家庭共享账号、Jellyfin-only和样本完整性。
4. 应用一致性备份、隔离恢复、发布链及联合验收；不能以OS恢复或容器healthy替代。
5. Nexus新独立实例、账号/仓库及健康监督已运行、重启后角色保留；用户已明确同意EULA，root已API接受并确认；220专用Maven发布/读取/SHA、匿名拒绝、reader写403和publisher删除403均通过。源hosted资产迁入进行中。

## 仍待确定或人工验证

- 用户已明确本期正式Java仅交付集群运行环境；业务应用先在测试验收，正式不启动业务。交易/资金/券商/通知服务仍不外发。
- 用户暂无域名/Cloudflare新入口，先LAN交付；现有CF进程/配置保持。CF备份按用户决定**仅PVE本机**，禁止导出Mac。
- 普通独立备份暂存Mac私有目录；还没有正式RPO/RTO和长期独立恢复硬件承诺。
- 电视/播放器/游戏文件工具的实际设备验收、业务SLO及家庭负载影响仍需真实样本与基线，未执行不得标passed。
- 监控本地规则已启用，外部通知接收人/通道尚未配置，无Slack/邮件/短信发送。

## 备份与回退边界

OS基线已备份到Mac并在独立VM9020恢复验证，随后停机；这不代表应用或整台PVE灾备通过。CF受保护归档留PVE root私有目录，源cloudflared未重启。原虚拟机、模板、本机应用数据和源仓库均保留，不执行旧环境清理。所有秘密限private目录，不写文档或制品ISO。

## 备份和开机次序补充

200/201纯合成数据在network-none临时容器中逻辑恢复并比对，通过后仅将纯合成归档存Mac，源容器未停。Grafana13实际使用统一resource表，首个旧表断言失败已归档；修正后在线SQLite备份在独立Grafana容器恢复、原新管理员认证及dashboard读取通过，归档已复制Mac600并核对payload/hash。见[数据恢复](../../evidence/implementation/app-backup-fixture-validation.json)、[Grafana恢复](../../evidence/implementation/ops-online-backup-restore.json)、[Mac副本](../../evidence/implementation/ops-private-Mac-backup.json)。新正式Nacos元库、Redis RDB、Rabbit topology本地快照已创建，尚未完整隔离恢复/导出；Rabbit不含队列消息。

12新VM已登记onboot和data→Java启动/反向停止顺序，仅改配置未重启宿主；延时不能替代健康检查，整机故障恢复仍未测。见[启动次序](../../evidence/implementation/startup-order-applied.json)。原生nc/curl从Mac实测PVE22/8006、NAS445可连，OMV9080/Jellyfin8096/Penpot9001/Nexus8081均HTTP200；Python本地网络errno65为执行面差异，不修改已正确的宿主规则。见[LAN入口](../../evidence/implementation/LAN-entrypoint-cli-probes.json)。

Java真实验证码验收发现libharfbuzz.so.0缺失；240只补签名库并重启Auth，其他四服务不动。主AI同时补齐220/230/231/232同包，无JDK或已有包升级。JDK基础脚本已加入依赖和check门禁；见[jdk库补齐](../../evidence/implementation/jdk-harfbuzz-base-completion.json)、[验证码RCA](../../evidence/implementation/java-captcha-font-fix.json)。

NAS软件交付已完成：两次重启后OMV/SMB/Jellyfin/SSH/挂载与ens18接口IPv6配置保持；SMB完整拒绝矩阵及writer rename/delete通过，Jellyfin仅media RO，无games/incoming访问。OMV默认SSH密码策略已恢复key-only/root禁用，重复quota激活通过OMV配置修正后systemd running且failed=[]。真实设备仍待验。见[NAS运行状态](../../infra/nas/runtime-status.json)、[共享详细权限](../../evidence/implementation/nas002-detailed-permissions.json)。

## 服务器内Lark已生效

用户明确本期仅机内Lark、Mac外部保持停用。270已受控重建原4组件到明确相同私网IPAM/地址并增加只读本地auth secret，CPU/内存/ports/pids/数据UUID保持，4healthy/17targets/Grafana登录保持。native桥仅172.18.0.1:19093、DynamicUser/LoadCredential、96MiB/Tasks32/CPU10%，Webhook不在argv/env/普通文档日志。

真实Alertmanager验收run f20465caddac4d0db4a035da5aaf155f：firing于06:20:52Z code0后才resolved于06:21:07Z code0；currentboot双阶段proof满足后，真实告警白名单已fresh reload为active，无真实告警时不额外发送。证据[两phase](../../evidence/implementation/lark-notify-send-acceptance-pair.json)、[active](../../evidence/implementation/lark-notify-enable-live-after-maintenance.json)、[最终权限](../../evidence/implementation/lark-notify-final-audit.json)。机内监控与T630是同故障域，不代签独立外部通知。
