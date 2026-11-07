# 实例精简、模板清理与fish：最后验收结果

2026-11-07（Asia/Shanghai）。已完成可独立执行的实例/模板清理和fish安装。**Nexus合并仅完成准备，合并所需短时停机已获授权；助手尚未执行源221停服/关机/迁盘。** 最后验收为12个运行实例，合并验收后才变11个。当前UEFI0058内存错误阻止PVE正常启动，用户已暂停服务器工作；以下清理结果是历史事实，不代表服务当前在线。

## 当前保留对象

| VMID | 名称 | 地址 | 当前作用 |
| --- | --- | --- | --- |
| 100 | cf-tunnel | 19.5 | 原LXC隧道，排除fish |
| 190 | network-gateway | WAN21.23 / LAN19.1 | 路由/DNS/DHCP，fish已装 |
| 200 | data-prod-db | 19.10 | 正式MySQL，未导入开发业务数据 |
| 201 | data-prod-infra | 19.11 | 正式Redis/RabbitMQ/Nacos |
| 210 | data-test | 19.20 | 独立测试数据组件 |
| 220 | publish-service | 19.30 | 发布工具链；Docker/fish及Nexus待机材料已准备，发布仍fenced |
| 221 | artifact-service | 19.31 | 独立Nexus，合并未执行；当前在线未复验 |
| 230 | java-prod-01 | 19.40 | 正式运行基础，只留一台，无业务程序 |
| 240 | java-test-01 | 19.45 | 测试运行基础，只留一台，五业务已停用 |
| 250 | penpot-service | 19.50 | 定制Penpot，排除fish |
| 260 | nas-media | 19.60 | OMV/SMB/Jellyfin，fish已装 |
| 270 | ops-service | 19.70 | 监控/服务器内部Lark，排除fish |

表中19.x为192.168.19.x，21.x为192.168.21.x。按正式/测试隔离的既有要求，本次各保留230、240一台；没有删除这两台。资源配置额度由55vCPU/117GiB降为**43vCPU/85GiB**，按125GiB规划保留40GiB宿主余量；这是配置额度，不是物理内存实时占用。

模板只保留三份，均停止封存并带fish4.0.2-1：9001 tpl-docker-base、9010 tpl-linux-base、9011 tpl-java-acceptance。9011仍是唯一已验收Java模板，无业务程序/配置/凭据。Docker模板保持原overlayfs/containerd image-store、live-restore=true及daemon SHA，没有为了fish改存储后端；应用角色的classic-overlay2是单独配置。

## 清理与回退备份

已依照依赖顺序清理15个旧对象：101、104、旧模板102/103/105/106、旧QA9000/9002/9003/9004/9005/9006/9020，以及重复正式Java231/232。104先于103，已确认的qcow2必需backing关系未被倒置处理。共享artifacts ISO仍被保留VM使用，没有删除。

每个旧对象在删除前均正常停止，执行受保护VZDUMP、zstd检查、VMA全档校验和SHA校验。原三模板及三fish候选也分别保留归档，共21份、压缩约29.9GiB，位于：

`/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/`

目录root0700，归档/日志root0600，仅PVE本机。没有备份CF100，没有整机备份或快照220，发布私钥仍只在220。完整性验证不等于对所有旧实例逐台恢复启动；原模板回退档保留，fish候选则实际完成独立QA后恢复到原模板ID并核对元数据。新建的6个builder/candidate/QA对象9040–9045随后全部删除，不留额外运行机或模板。

证据：[依赖DAG](cleanup/audit/disk-dependency-dag.json)、[删除复核](cleanup/audit/delete-script-review.md)、[实际删除](cleanup/deleted-candidates.json)、[备份汇总](cleanup/backup-summary.json)、[模板换版](cleanup/fish/core-template-replacement.json)、[QA](cleanup/fish/template-QA-summary.json)、[临时机清理](cleanup/fish/temp-closeout.json)。

## fish范围与使用

已装的9台运行来宾：190、200、201、210、220、221、230、240、260；另外三份保留模板也已更新并验证。CF100、Penpot250、Ops270按要求排除；PVE宿主未安装或修改shell。

全部是**只安装fish，不切换默认登录shell**：root/ub仍Bash，publisher仍原/bin/sh；未执行chsh、未写用户fish配置、未装插件。SSH进去后输入`fish`即可使用。若要把ub设为默认fish，需用户明确选择；本次没有把未回复的偏好当成许可。

安装只新增fish/fish-common4.0.2-1及所需libpcre2-32，不升级/删除原包。运行来宾的SSH/关键服务和容器PID、启动时间/健康状态前后保持。模板通过独立candidate完整克隆检验新machine-id/host key；Docker还验证独立engine-id，Java保留java UID999/JDK21/原验收脚本与exporter masked。

证据：[9来宾安装](cleanup/fish/runtime-status.json)、[模板工具](cleanup/fish/TEMPLATE-BUILD.md)、[独立QA汇总](cleanup/fish/template-QA-summary.json)。

## DNS、网络和监控同步

PVE bridge已清理退休/临时身份并重新登记三个模板MAC，保留源MAC/IP绑定、prod/test/home隔离和WireGuard10.66.66/24受信访问；PVE21.22仍只管理/二层，forward0、无NAT。

VM190仅更新DNS静态host-record，删除批准的11条旧记录。11个保留名称的UDP/TCP查询正确，11个退休名均NXDOMAIN，artifact-service31和publish-service30保留。只DNS进程重启，非DNS服务、nft/WG、路由/MAC/forward/监听及租约权限保持。未触Nexus生命周期。

最后验收时监控从12node+5own变为**10node+5own=15/15UP**，221仍被监控；没有把31映射成220重复主机。十个guest的catalog与installer配套减为10角色，health/collector原字节、业务/Exporter/容器身份及timer状态保持，本地新版source单独最小同步。清理维护silence已在零活跃告警后解除，Lark原模式/凭据和Mac外部探针停用状态保持，没有新测试消息。

证据：[DNS](cleanup/network/dns-runtime/summary.json)、[配套监控](cleanup/monitoring/ten-role/execution-status.json)、[最终实机检查](cleanup/final-live-check.json)、[维护解除](cleanup/maintenance-ended.json)。

## Nexus合并：准备完成、已有授权、等待硬件处理

[17合并架构](17-publish-artifact-consolidation.md)统一目标：VM220 `publish-service`包含发布与Nexus职责；`artifact-service`不再作为独立目标VM，下方技术步骤仍未执行。

技术方案已具体化：220由4CPU/4GiB调为6CPU/8GiB，保持hostname publish-service、管理主IP19.30；Nexus继续用19.31:8081作为同NIC服务alias，客户端URL不改。原100GiB专用Nexus数据盘及UUID239dc45a-b1f3-408b-a8ef-7afa77b52204保持，官方跨VM move-disk不传storage，源/目标同时停止后唯一移交；不把数据盘并挂两VM。

当前220已装匹配Docker/Compose/classic-overlay2，原两镜像按实际SHA-ID离线导入。最小代码/env/marker和三现役Nexus凭据已在同ownerSSH管道送到root700/600待机目录，没有本地秘密归档，没有运行态DB复制，也没有读取或复制发布私钥。最后准备核验时source221运行，target没有Nexus容器或31地址，资源仍4CPU/4GiB；当前在线状态无法复验。

真正迁移须短时停止Nexus、221冷备关机，并重启220完成资源/盘/alias后验原账号/EULA及构件SHA；预计5–15分钟，失败可反向移盘恢复源。**自动审批拒绝了首次source停服动作，理由是此前只明确询问同机可行性，尚未批准该服务中断；CreateProcess前已拦截，未执行，也未通过替代方式停服。** 随后用户已明确回复“授权短时停机合并”，该许可缺口已满足；现在因硬件错误和用户暂停不能继续，详见[交接](11-live-handoff.md)。

用户完成硬件处理并指示恢复后，下一次维护需要新silence、重新读源/目标基线和数据、核未变凭据/镜像/发布key元数据、执行冷备移交。监控当前已是10角色新SHA，未来合并再10→9并由220接管Nexusunit/HTTP31，必须按[新基线合同](cleanup/monitoring/ten-role/future-merge-contract.json)重建候选，不能盲改旧12角色expectedSHA。source221不得先删。

具体准备：[Nexus方案](cleanup/nexus/PLAN.md)、[待机读回](cleanup/nexus/preparation-readback.json)、[审批拦截记录](cleanup/nexus/approval-block.json)。

人工执行步骤见[操作手册](19-manual-operations.md)；历史通过与当前暂停状态必须分别记录。
