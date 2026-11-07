# 实施进展

用户已授权执行全套方案，当前为实施阶段；历史文档基线与验收凭证保留。

## 已完成

- Dell 官方 PERCCLI 包下载及 SHA256 核对，临时解包读取控制器，无 RAID 参数变更。
- 确认 SSD RAID1 正常；容量 RAID5 降级、槽32:3正在自动重建。详见 [硬件发现](../../08-hardware-findings.md)。
- 在健康 SSD 上从原模板102完整克隆 VM9000（dell-template-inspect），2 vCPU/2 GiB，使用现有LAN DHCP，未修改宿主网络。
- 通过可信 QGA 取得SSH主机公钥后，以指定私钥验证 ub 登录成功；系统 Ubuntu24.04、Guest Agent active、Docker29.1.3。Cloud-Init仍需完成及处理弃用项。
- 数据三角色、Penpot/Nexus和NAS/Jellyfin的部署准备包已生成，源环境保持运行。

## 当前门槛

- **宿主网络明确授权待回复**：自动审批拒绝持久路由/防火墙变更，要求告知具体网段、端口和影响后由用户明确批准。已向用户提问；不得绕过拒绝执行。脚本已完成原子规则更新与回退审查，尚未应用。
- **容量阵列重建中**：暂停store的大写入、NAS数据盘格式化和生产数据验收；不得以估计时间代替Optl/Onln实际证据。
- Finger正式数据初始化来源、正式域名/Cloudflare配置与独立备份目的地仍待用户补充。

## 证据

- [控制器证据](../../evidence/implementation/raid-controller.json)
- [验证机登录](../../evidence/implementation/guest-9000-initial.json)
- [任务状态](../../tasks.json)

来宾VM9000为验证用途，不计入最终13个常驻角色；资源分批使用，尚未同时启动全部目标。没有改动源模板、源业务数据或真实外部交易。

## 2026-11-06 后续推进

- 官方 Debian13 AMD64 镜像已下载并按官方SHA512核对，已传到PVE健康SSD再次核对。较慢的原下载最后checksum不一致，未使用该文件；实际导入使用独立命名的verified镜像。
- 干净Debian13 VM9001：ub登录、Cloud-Init done且无错误、Guest Agent active、NTP同步通过；Docker Engine29.9.3/Compose v5.7.0安装完成。
- Linux基础制作机VM9010独立创建并完成首次配置；两台正在进行身份清理和模板定稿，克隆身份验证尚未通过。
- 数据准备包通过13项离线安全回归，Penpot/Nexus通过8项，NAS采集器通过6项；这些只证明脚本逻辑，不替代目标服务验收。
- 基础组件缺容器误判、挂载缺失写根盘、路径逃逸、恢复卷半预检、错误Docker daemon和源版本漂移门禁已修复。
- Java现有boot JAR含同名同版本但摘要不同的内部依赖，System缺boot JAR；独立offline构建准备中，不直接拼装旧制品。
- 外部制品仓库带凭据探测被自动审批拒绝，未执行；不通过代理绕过。详见 [审批边界](../../evidence/implementation/approval-boundaries.json)。

源环境未停写/导出/搬迁，宿主内部桥/路由/nft/NAT未应用，等待用户对具体网络规则的明确答复。

## 2026-11-06 05点后

- 控制器复采确认 RAID5 恢复 Optl、全部盘Onln、错误计数0、BBU Optimal；历史失败与恢复证据分别保留。
- 新模板：9010 tpl-linux-base、9001 tpl-docker-base。各自两台完整克隆验证通过，Cloud-Init/NTP正常，machine-id/主机名/SSH指纹均唯一，无LVM backing依赖。
- Docker模板首个试验克隆发现时间客户端不匹配（安装chrony后仍引用timesyncd），已修正Cloud-Init profile，并用新双克隆重验通过；旧失败试验9003保留关机。
- 12台目标VM均已创建，另保留现有CF LXC100；目标VM均关机等待宿主网络明确授权，无业务服务上线。
- 200/201曾以断开网卡启动准备，但Guest Agent未就绪，因此已停机；在严格核对新空专用LV后仅格式化它们的80/24GiB数据盘，UUID已写入Cloud-Init及私有部署包，来宾挂载尚未验收。PVE系统盘、物理盘和store未格式化。
- 14个公共AMD64镜像已缓存并导出，源容器/标签未变；自定义Penpot构建与五服务离线构建继续推进。

宿主网络规则仍只做语法检查（nft -c），未应用；10.63地址只是目标配置，不代表当前可访问。

## 2026-11-06 来宾准备与独立验证

- 12台来宾全部通过临时LAN管理身份核验；7块业务/构建数据盘按虚拟盘标识、容量、空签名和UUID完成创建/实际挂载。NAS媒体盘未格式化。
- 5台Java/发布节点OpenJDK21.0.13与验证码字体已验证；发布机Node22.23.4、pnpm8.15.9/10.33.2、Python3.13.5、Git2.47.3、MCP SDK1.26.0准备完成，未安装Git凭据/启动发布服务。
- 五服务JAR重新构建并由主AI独立复核摘要和实际com/sargia/finger内部依赖，无同名冲突；Auth有仅作用于隔离副本的外部issuer/客户端配置补丁与5项纯单元验证。
- Docker29默认containerd与源classic离线归档的镜像身份语义不同；保留首次失败，测试来宾使用支持的classic overlay2后4个ConfigID全部匹配，固定官方digest的MySQL名称关联3秒完成、无层下载。角色预载采用该空状态runtime profile，不对有业务状态节点切换。
- 只读制品ISO已生成并校验，包含审核过的软件归档和Java JAR，无运行配置/秘密；目标正在离线预载，容器数保持0。
- 无业务数据的OS验证机已备份、独立复制到Mac私有目录并恢复到9020验证ub/Cloud-Init/Guest Agent；这是OS基线，不代表数据库/Penpot/Nexus或RPO/RTO通过。
- CF备份导出Mac被自动审批拒绝，未导出。仅在PVE同机root私有目录备份成功、原进程未变；本地失败的临时目录权限原因已修正。

12来宾处于临时管理阶段；完成准备后将恢复10.63私网配置并关机，等待用户明确批准宿主隔离网络。宿主新桥/转发/nft/NAT未执行，业务服务未启动。

## 2026-11-06 验证补充

- 12台Node Exporter1.9.0基线真实安装完成且全部masked，无9100监听、无collector/timer；仅停放，待私网形成后激活。
- OS基线备份380,475,872字节已复制Mac并校验，恢复9020后ub/Cloud-Init/Guest Agent通过，9020随后正常关机；原空闲232恢复准备。Cloud-Init外部片段作为私有sidecar备份；不代表完整替换PVE或应用数据恢复通过。
- CF同机保护备份244,256,662字节成功，源进程不变；含凭据归档始终留PVE root私有目录，未导出Mac，等待单独明确授权。
- 软件只读ISO约13.5GB完成，运行配置与秘密不在ISO内。测试来宾验证UDF挂载、归档大小与SHA，镜像仍仅预载无容器。
- 发布机npm首次安装因两个配置均指向/dev/null报错，修正为两个独立空配置后成功；失败记录保留，未引入仓库凭据。
- 五JAR主AI首次复核筛选误含第三方-api类库，按实际com/sargia/finger包路径修正后摘要与内部依赖清单完全匹配；这是验证器错误，未误报为源码问题。

主机内部桥/转发/nft/NAT仍未执行。CF敏感备份跨机导出同样未执行。

## 2026-11-06 软件与日志验证收尾

- 6个Docker角色（含测试数据pilot）的预载完成；5个批量角色33次ConfigID/AMD64核对全部通过、容器始终0。5角色30个公共固定digest引用已补关联，2.48～3.27秒/次，未观察到层下载；私有仓库未访问。
- PEN250实际Docker数据根位于100GiB盘/srv/penpot/docker，镜像/overlay2/volumes与指定UUID一致，约93.50GiB空闲。
- 12来宾监控基线真实安装并验证全部masked、9100不监听、collector/timer停放，原policy-rc.d对象恢复。
- 目标Penpot frontend原配置的MCP access/error日志确实会带查询token；目标runtime只读模板补丁已通过dummy-token测试，200代理和502错误语义均保持，12项回归通过。没有真实token入测试，原镜像/源17容器未改。

这些仍是基础和制品层验证。目标MySQL/Nacos/Redis/RabbitMQ/Nexus/Penpot/OMV/Jellyfin/Java/监控业务未启动，真实网络隔离、应用恢复、业务链和设备验收未通过。

## 当前停放终态

12台新目标VM已全部正常关机，保留MAC、恢复plan中的10.63私网配置和DNS，自启动关闭。宿主检查确认IPv4 forwarding仍0，vmbr10/20/30/40不存在，dell_filter/dell_nat未应用；原CF CT100仍运行。具体见 [停放证据](../../evidence/implementation/guests-parked-awaiting-network.json)。

临时192.168.21.*来宾地址仅保留为历史验证，不作为当前访问地址。目标应用/容器均未启动，源17个本机容器和原有模板未更改。等待用户明确宿主网络授权后，按 [恢复入口](../../10-resume-after-approval.md) 继续；CF敏感备份导出为独立确认，未授权时只能保留PVE本机。

## 2026-11-06 用户确认后继续

用户明确授权原审核的宿主四桥/转发/nft/LAN-only端口变更，决定正式空库、本机数据仅测试；暂无域名先LAN、普通备份暂存Mac；CF归档仅PVE本机不导出。已应用审核脚本并核验管理SSH保留、forward=1、四桥地址与专用表存在；12台固定私网SSH/Cloud-Init/QGA验证通过。

数据层、Nexus/Penpot准备和NAS安装已分派，Ops真实部署开始，12节点9100已仅绑定私网激活；全部实际业务健康、跨区拒绝及数据恢复按结果更新，不能用本段作为已完成业务验收。
