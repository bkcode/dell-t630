# Dell PowerEdge T630 · 服务架构与操作入口

更新：2026-11-10，Asia/Shanghai。用户已明确恢复Nexus合并并移除独立artifact-service，覆盖11月8日暂缓范围。本次已完成源停服/关机、PVE冷备校验、220正常停机与6CPU8GiB/原盘/alias31移交，目标已启动；最终数据、身份、监控及220受控重启核验通过，221已退役，详见[本次交付](completion/20261110-nexus-merge/README.md)。

## 服务和地址

PVE只负责虚拟化、存储、管理与二层桥，管理地址`192.168.21.22`；iDRAC为`192.168.21.21`。OpenWrt21.1将19.0/24路由至网关VM190的21.23，来宾经19.1统一路由，无PVE应用NAT。

| VMID | 名称 | 地址 | 作用 |
| --- | --- | --- | --- |
| 100 | cf-tunnel | 19.5 | Cloudflare Tunnel；仅PVE保留凭据备份 |
| 190 | network-gateway | 21.23 / 19.1 | 路由、DNS、DHCP与防火墙 |
| 200 | data-prod-db | 19.10 | 正式MySQL与Nacos元库；正式业务schema仍空 |
| 201 | data-prod-infra | 19.11 | 正式Nacos、Redis、RabbitMQ |
| 210 | data-test | 19.20 | 测试四组件、已授权导入的36份Nacos配置和两份Puyu库 |
| 220 | publish-service | 19.30 / alias19.31 | 发布工具、只读导航9080；Nexus8081承接原221 |
| 230 | java-prod-01 | 19.40 | 正式Java运行基础，不启业务 |
| 240 | java-test-01 | 19.45 | 测试Java运行基础，不启业务 |
| 250 | penpot-service | 19.50 | 定制Penpot、设计及服务器MCP |
| 260 | nas-media | 19.60 | OMV/Samba/Jellyfin，家庭影院与文件库 |
| 270 | ops-service | 19.70 | Prometheus/Grafana/Alertmanager和服务器内Lark |
| 280 | resource-service | 19.80 | 正式/测试共用NFS，客户端/mnt/resources |

地址前缀均为`192.168.`。上表是已验证的合并后合同，221已移出当前清单；禁止将旧221与新220同时作为31所有者。当前12来宾（11VM＋1LXC）、3份停止模板、45vCPU/87GiB、10node＋5Ops＝15targets。220原build100GiB和Nexus100GiB卷独立，总额度不因合并再减4GiB。模板保留9010 Linux、9001 Docker、9011 Java验收。

## 常用入口

| 服务 | 地址 / 文档 |
| --- | --- |
| 服务导航 | [HTTP19.30:9080](http://192.168.19.30:9080/)；匿名只读、13入口、无顶部栏、全宽，不做部署/SSO/健康探测 |
| Nexus | [HTTP19.31:8081](http://192.168.19.31:8081/)；原URL/账号/EULA/仓库身份保持 |
| Penpot | [HTTP19.50:9001](http://192.168.19.50:9001/)；原表单预填按明确受信范围，未改密码 |
| 测试Nacos | [HTTP19.20:8848/nacos](http://192.168.19.20:8848/nacos/) |
| Grafana | [HTTP19.70:3000](http://192.168.19.70:3000/login) |
| NFS资源 | 19.80:/，230/240共用/mnt/resources；[当前NFS手册](completion/20261110-nfs-only/usage-manual.md)，FileBrowser已停用 |

自建内部应用默认HTTP；PVE/iDRAC内置HTTPS保留。受信LAN192.168.21/24、WG10.66.66/24获准访问19网有效IPv4服务，应用认证不变；NFS仍仅精确双客户端。秘密、密码和私钥不在Git，新电脑clone不能直接获得凭据或管理信任。

## 发布工具与应用边界

独立[bkcode/deploy-public](https://github.com/bkcode/deploy-public)已由VM220 Git拉取main/213f1f4，Mac/Linux65测试通过。CLI prod→main、dev→dev；MCP仅dev/127.0.0.1:18765。六个业务/公共库仓库仍main、远端dev全缺，新dev预检应拒绝；不创建/推送业务分支、不fallback main。prod SSH目标未配置，真实deploy关闭，原受限链fenced，**任何环境不构建或启动Java业务**。旧五服务dev/main成功只是初装历史。[模式验收](evidence/deploy-public-modes-20261110/README.md)。

Penpot已从bkcode/penpot main取8a9b961部署定制前端，11容器健康，首次调研/团队欢迎关闭；Puyu3页/58240图形/19组件导入完成，原7文件保持。服务器常驻MCP默认Puyu，Mac使用SSH stdio，不导出服务器token。[源码更新](evidence/penpot-onboarding-20261110/README.md)、[设计导入](evidence/penpot-puyu-import-20261110/README.md)、[MCP连接](evidence/penpot-client-mcp-20261110/README.md)。

导航来自原bkcode/deploy独立模块，本次已由专属任务修改公开清单并部署13入口release，两份源文件仍未提交/推送，不捎带原main用户提交。Nexus同机合并不更换导航程序实现、不重生成deploy-public私有key。Jellyfin fork尚未替换现役官方镜像，不等于电视客户端已改造。

## 备份和限制

自动备份仅正式MySQL/Nacos白名单，当前nacos_prod；03:30/GFS最近3＋每日7＋每周4，PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups`。新增未列库拒绝告警。其余VM/测试/Redis/MQ/Nexus/Penpot/NAS/Ops不新增自动备份。

本次221迁移冷备2,400,054,202字节，经SHA/zstd/VMA校验，仅PVE保护保存，不导出Mac。发布私钥只220，禁止wholebackup/snapshot220或读取导出私钥；CF备份只PVE。旧归档和失败记录保留，不按旧policy重启整机job。仅3301B Nacos小档在隔离临时MySQL完成恢复；完整业务恢复、RPO/RTO、独立DR和同机故障下外部告警未签。Mac外部探针不需要，保持停用。

历史DIMM_B1/UEFI0058故障由用户报告已重插/更换并诊断通过；恢复boot EDAC0/RAIDOptimal仅当时证据，不代替长期观察。不得远程powercycle或清日志掩盖故障。

## 文档与机器合同

- [当前交接](11-live-handoff.md)、[状态与历史](01-current-state.md)、[整体架构](02-architecture.md)、[发布/Nexus架构](17-publish-artifact-consolidation.md)。
- [逐机入口](machines/README.md)、[Git来源总表](machines/GIT-REPOSITORIES.md)、[机器可读计划](plan.json)、[任务](tasks.json)。
- [访问入口](12-service-access-and-operations.md)、[人工手册](19-manual-operations.md)、[本次Nexus维护手册](completion/20261110-nexus-merge/usage-manual.md)、[Git交接](20-git-and-handoff.md)。
- [网络](15-network19-delivery.md)、[WireGuard](16-wireguard-access.md)、[模板](03-templates-and-access.md)、[原清理](18-cleanup-and-consolidation.md)、[验收范围](06-acceptance.md)。

旧10.63/DNAT/旧双机221/早期49GAV234主件与13来宾16UP均为对应阶段历史，不能重放为现役配置。旧221逐机资料归档时保留必要历史，不作为第二个31部署入口。完整OpenClash规则只留本地，不推Git。


当前FileBrowser已按后续明确授权从现役安装路径移除（不再只是masked停用），专属闲置账号删除，NFS及资源文件保持；旧说明仅阶段历史。详见[移除后NFS使用说明](completion/20261110-filebrowser-remove/README.md)。


2026-11-11已完成[Puyu专用空制品仓库与发布机配置接入](completion/20261111-puyu-nexus/README.md)：新仓库仍0组件/0资产，限定reader/publisher，工具main2d8f541与Mac/Linux75测试通过。没有迁旧制品或改Go/Java业务，实际构建/发布仍关闭；操作见[本次手册](completion/20261111-puyu-nexus/usage-manual.md)。


2026-11-11最新[Nexus本机配置对齐](completion/20261111-nexus-local-parity/README.md)已按用户安全选择完成：共有9库定义对齐，额外7保留，服务器16库；发布机mainbba3542/Linux75通过，读取maven-public、dev/prod发布imnull-*，原密码/MCPkey保持。原50组件/1347资产保留、DELETE0、不迁数据不启业务，代理cache miss未签验。先前独立Puyu映射仅旧阶段，不覆盖本次实际映射。
