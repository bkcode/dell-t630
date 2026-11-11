# 当前交接与继续工作入口

更新：2026-11-11，Asia/Shanghai。用户已明确恢复Nexus合并并移除独立artifact-service，覆盖11月8日暂缓范围。本次已完成源停服/关机、PVE冷备校验、220正常停机与6CPU8GiB/原盘/alias31移交，目标已启动；最终数据、身份、监控及220受控重启核验通过，221已退役，详见[本次交付](completion/20261110-nexus-merge/README.md)。

## 当前重点

Nexus合并与退役以[本次交付](completion/20261110-nexus-merge/README.md)及最终原生回执为唯一现场依据。不要回放cleanup旧stage/mount/commit/start，旧11月8日“不迁移”只留历史。新220还承载导航和deploy-public，必须保留原私有YAML、APIkey、DeployKeys、受限发布私钥与build UUID守卫。

220新资源6CPU8GiB、primary30/alias31，原build与Nexus各100GiB独立；31继续Nexus8081兼容URL，管理SSH用30/220自身host key。当前12来宾、3停止模板、45CPU87GiB、10node＋5Ops＝15targets。旧221档与失败/journal保护保存，只在最终数据/身份/网络/监控通过后退役源实例。

## 不变的授权边界

- Java230/240只运行基础，不构建/启动业务，旧publisher链fenced。
- deploy-public main2d8f541已同步，Mac/Linux75测试通过；Puyu专用空制品仓库和私有artifacts YAML已接入（不迁旧制品），适配器仅CLI显式调用既有build.bash。CLI prod/main、dev/dev，MCP dev-only/loopback18765，prod SSH未配置、真实发布disabled。11月10日远端审计六库缺dev；本轮六工作树仍main/clean，未重新fetch远端、未创建分支，旧缺分支预检保持历史含义；旧dev/main成功不能当新dev就绪。
- 正式业务schema空，测试仅已精确授权的Nacos36配置与两Puyu库迁入；不持续同步、不自动适配端点或切应用连接，原测试凭据合同保持。
- PenpotDNS回收修复已上线：DNSinit:true/严格门禁，38测试＋原生140次0僵尸/数据保护通过，70分钟观察4200秒/119采样已通过，见[本次修复](completion/20261111-penpot-hourly/README.md)。Penpotmain8a/11healthy、首次引导关闭，Puyu设计已导入；服务器MCP默认Puyu，Mac通过SSH stdio，无token导出。原owner表单默认值按受信范围明确授权，不能扩到公网。
- VM280仅NFS，FileBrowser已从现役程序/配置/状态路径移除，服务not-found/8080关闭；原资料仅本机受保护归档。230/240共用同根/mnt/resources，精确exports、root_squash、UMask0002与挂载守卫保持，不迁资源文件/不启业务图片HTTP。
- 自建应用HTTP；PVE/iDRAC内置HTTPS保留。LAN21/24、WG10.66/24受信访问规则不放宽应用认证，WireGuard peer/32保持。OpenClash完整规则仅本地，不推Git。

## 备份、硬件与故障处理

自动备份仅正式MySQL/Nacos，PVE落点、03:30、GFS3-7-4，新增未列库拒绝告警。Nexus迁移冷备2,400,054,202字节仅PVE且SHA/zstd/VMA已核，不新增自动任务。220发布私钥只220，不能wholebackup/snapshot220或读取导出；CF档只PVE。

DIMM_B1/UEFI0058为保留历史，用户报告已重插/更换并诊断通过。boot EDAC0/RAIDOptimal只证明采样，不能代替长期硬件观察；不远程powercycle、不清日志。Mac外部探针不需要，服务器内部Lark按原接收方保持，不人工发测试消息。

仅Nacos小快照已隔离恢复；完整业务恢复/RPO/RTO/独立DR和物理重启全流程不签。共享T630故障域仍存在。

## 入口

[首页/服务表](README.md) · [当前计划](plan.json) · [任务](tasks.json) · [逐机目录](machines/README.md) · [Git来源](machines/GIT-REPOSITORIES.md) · [架构](02-architecture.md) · [Nexus架构](17-publish-artifact-consolidation.md) · [全局人工手册](19-manual-operations.md) · [本次维护手册](completion/20261110-nexus-merge/usage-manual.md)。

历史证据按原日期解释：[11月8日恢复](recovery/20261108/README.md)、[11月9日备份范围](completion/20261109-prod-db-scope/README.md)、[资源初建](completion/20261109-resources/README.md)、[Penpot更新](evidence/penpot-onboarding-20261110/README.md)、[发布器模式](evidence/deploy-public-modes-20261110/README.md)。旧13来宾/16UP不覆盖合并后数量，旧49GAV234主件不覆盖当前全量基线12repos/7hosted/50components/1347assets。


最新Puyu配置阶段见[交付与限制](completion/20261111-puyu-nexus/README.md)：新仓库清理测试后0组件/0资产、两专属身份与实际YAML认证通过；MCP仅dev/真实deploy关，无实际Gradle构建。私有插件/公共库、SNAPSHOT版本及业务分支准备仍是后续前置，不能按配置ready直接开启发布。


2026-11-11最新[Nexus本机配置对齐](completion/20261111-nexus-local-parity/README.md)已按用户安全选择完成：共有9库定义对齐，额外7保留，服务器16库；发布机mainbba3542/Linux75通过，读取maven-public、dev/prod发布imnull-*，原密码/MCPkey保持。原50组件/1347资产保留、DELETE0、不迁数据不启业务，代理cache miss未签验。先前独立Puyu映射仅旧阶段，不覆盖本次实际映射。
