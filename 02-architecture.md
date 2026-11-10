# T630 服务架构、资源和故障域

更新：2026-11-10。用户已明确恢复Nexus合并并移除独立artifact-service，覆盖11月8日暂缓范围。本次已完成源停服/关机、PVE冷备校验、220正常停机与6CPU8GiB/原盘/alias31移交，目标已启动；最终数据、身份、监控及220受控重启核验通过，221已退役，详见[本次交付](completion/20261110-nexus-merge/README.md)。

## 服务结构

```text
T630 / PVE21.22：虚拟化、store存储、管理、二层桥；无宿主NAT/L3转发
├─ VM190：WAN21.23 / LAN19.1，路由、DNS、DHCP、防火墙
├─ LXC100 CF19.5：Cloudflare Tunnel
├─ VM200 MySQL19.10 ＋ VM201 Nacos/Redis/Rabbit19.11：正式数据基础
├─ VM210 四组件19.20：测试数据
├─ VM220 publish-service 6CPU8GiB
│  ├─ primary19.30：管理、构建、受限发布工具、导航9080、exporter9100
│  ├─ loopback127.0.0.1:18765：Puyu dev-only MCP，真实部署关闭
│  ├─ /srv/dell-build：原100GiB构建盘
│  └─ alias19.31:8081：Nexus，独立原100GiB盘/srv/nexus
├─ VM23019.40 / VM24019.45：正式/测试Java运行基础，无业务程序
├─ VM250 Penpot19.50：定制frontend/backend/worker/import/MCP/DB/素材
├─ VM260 NAS19.60：OMV/Samba/Jellyfin
├─ VM270 Ops19.70：Prometheus/Grafana/Alertmanager/服务器内部Lark
└─ VM280资源19.80：NFS-only，230/240共用/mnt/resources
```

合并完成后只有220一个发布/制品VM，31兼容原NexusURL，不是独立节点。当前12来宾、3停止模板，45vCPU87GiB；硬件28物理核/56线程，保守125GiB预算余38GiB（含宿主/缓存预留）。220由4/4加221原2/4成为6/8，总预算不变。vCPU是调度配置，不是物理核承诺；并发构建/仓库/媒体/数据库性能SLO未验。

## 模板、VM和Docker

模板创建OS实例，Docker维护选定VM内应用，两者互补。保留Linux9010、Docker9001、Java验收9011；模板无业务源码/数据/DeployKey。数据四组件、Nexus、Penpot、Jellyfin和Ops使用固定镜像/受控配置，数据不放容器可写层。网关/发布工具/导航与采集使用native/systemd。Docker模板overlayfs/live-restore和角色专用classic-overlay2各按已验合同，不能批量换profile。

## 数据、配置和发布

正式200/201与测试210独立。正式业务schema空；测试已按明确授权导入Nacos36配置及Puyu两库51表1291快照行，源保留、无持续同步/应用连接切换。测试凭据按用户指定原Compose合同保持，真实值不入文档。Nacos配置原样导入不等于所有端点已适配或业务可运行。

发布工具来自bkcode/deploy-public main/213f1f4，CLI prod/main、dev/dev；MCP仅dev，真实发布关闭。六后端/公共库仍main且远端dev全缺，预检按设计拒绝；prod身份留空，不代建业务分支、不fallback main。230/240只收后续批准的制品，不配置Git私钥，现有forced-chain仍fenced。任何环境均不启动Java业务；Nacos/Nexus自身使用JVM不属业务上线。

Penpot实际main/8a9b961定制前端，首次引导关闭、11healthy；Puyu设计已导入，服务器MCP默认Puyu。NAS仍官方Jellyfin，不因记录用户fork就自动部署电视客户端或自定义服务端。资源280只保留NFS，FileBrowser已退役，原state/秘密保护保留；不接业务图片HTTP、不迁旧文件、不扩备份。

## 网络与身份

OpenWrt21.1静态路由19/24→21.23；PVE21.22只管理和二层桥，vmbr19无宿主IP，IPv4/IPv6 forwarding全0、无应用DNAT。190和来宾无SNAT，出口OW NAT。LAN21/24与WG10.66.66/24受信访问19网有效IPv4服务，应用身份继续校验；NFS仍精确双客户端。WireGuard每客户端peer/32保持。

19网同子网直连流量由bridge精确MAC/IP+角色矩阵隔离，不能仅依赖网关。31唯一归220同NIC，管理host key属于220，默认发布源30。旧dell-vm221别名不再用于31。旧10.63/DNAT不恢复；OpenClash完整规则只留本地。

## 监控、备份和共享故障域

合并后只抓220的30:9100，移除221 node，包含资源280的10node＋5Ops共15targets。220保留原4项并加Docker/Nexus/MCP为7单元，NexusHTTP仅本机alias31，MCP认证接口不当HTTP探针。Lark原接收方/秘密保持，不发送测试消息。Mac外部探针不需要。

自动备份仅正式MySQL/Nacos白名单，本次Nexus冷备是一次性PVE本机回退点，不新增自动任务；220发布私钥只留220，禁止wholebackup/快照导出，CF档也只PVE。独立DR、完整业务恢复/RPO/RTO未签。

所有VM共享T630的电源、内存、存储与网络故障域，多VM不提供跨物理机HA。同机Ops无法承诺整机断电通知，RAID不是独立备份。内存处理来自用户诊断报告，boot零计数不是长期稳定性证明。完整操作、证据与限制见[本次Nexus交付](completion/20261110-nexus-merge/README.md)和[人工手册](19-manual-operations.md)。

历史资源初建13来宾/16UP、清理前双机220/221、旧49GAV234主件均保留在原证据，不拿旧数量覆盖新鲜基线12repos/7hosted/50components/1347assets。
