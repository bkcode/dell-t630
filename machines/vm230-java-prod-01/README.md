> 更新：2026-11-10（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM230 · java-prod-01

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

## 本轮只读状态与备份归属

14:42:56–14:43:40分项采样：hostname/19.40/GW与DNS19.1正确，NTP同步、JDK21.0.13可执行、finger存在、Java进程0；旧五业务unit not-found/inactive/非enabled，exporter/timer正常。没有启动业务或重跑非root烟测。 证据：[本机分项审计](../../completion/20261109/core-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

**配置合同与带时点基础审计，非完整运行配置导出。** 11月7日UEFI0058/B1事故与当日02:35旧基线保留历史；用户11月8日确认内存处理/诊断通过，11月9日已按下列证据重新核验基础状态。本页文档同步没有远程变更，也不把健康状态扩写为业务数据/权限或完整恢复通过。

## 职责、身份与资源

正式 Java 运行基础，仅 JDK21、非 root 运行身份与基础监控；不部署或启动业务程序。

| 项目 | plan角色合同 |
| --- | --- |
| VMID / hostname | 230 / `java-prod-01` |
| 主IP / bridge | `192.168.19.40/24` / `vmbr19` |
| 网关 / DNS | `192.168.19.1` / `192.168.19.1` |
| vCPU / 内存 | 6 / 16GiB |
| 环境 | `prod` |
| PVE系统盘存储 | `store` |
| 启动顺序 / 等待 / 关机超时 | 40 / 15s / 120s |

唯一资源/IP来源为[plan.json](../../plan.json)；[config.json](config.json)是本目录的非秘密角色摘要，不替代plan。来源与SHA见[config-sources.json](config-sources.json)，均指向已存在的仓库公开文件。

## 存储与运行基础

系统盘位于 `store`。plan未为本角色声明独立应用数据盘、数据UUID或业务挂载点，本目录不补造这些值；不得为了复制其它节点做法而格式化盘或新增挂载。历史 `/opt/finger` release/配置不能视为待自启业务。

运行基础为JDK21，普通业务运行身份 `finger`，Java路径 `/opt/finger/java/bin/java`；管理登录使用 `ub`。不使用root私有mise路径。保留基础监控，**没有应启动的Java业务systemd单元，也没有业务Compose栈**。

## 业务与依赖边界

正式 Java 运行基础，仅 JDK21、非 root 运行身份与基础监控；不部署或启动业务程序。

VM230与VM240各只保留一个运行基础；已退休231/232不重新创建。VM190提供网关/DNS，VM270只采基础节点指标；旧业务对MySQL/Nacos/Redis/Rabbit的配置不作为本阶段运行依赖。现役健康契约不包含五个业务HTTP检查，不以启动业务换取绿色验收。

正式节点从未因此获准部署交易、资金、券商或其它业务。恢复后只检查JDK/非root可读/无业务进程和基础监控，不复制旧测试release到正式节点。

## SSH、Shell与网络

日常按已批准维护范围，用 `ub` 和客户端 `~/.ssh/yang_local_rsa`，严格核对 `dell-vm230` 既有host key；私钥只在客户端，不进入VM配置目录或Git。更换IP不等于重新信任任意主机，不关闭known_hosts校验，不拷贝别台机器host key。

fish已安装（包版本4.0.2-1）；root/ub默认仍为Bash，没有自动chsh。19网经VM190/19.1路由到OW，PVE21.22只做管理和二层桥、host forwarding=0、无宿主NAT。已授权WireGuard源10.66.66.0/24访问服务器服务；应用认证与原角色ACL继续生效。

基础exporter端点 `192.168.19.40:9100` 由Ops按既有规则采集，collector只输出本机状态，不输出凭据。本轮已按下方审计核基础状态；历史功能通过不代替本轮未重做的认证/内容检查。后续维护时仍核真实监听、单元与指标新鲜度。

## 人工操作与恢复门禁

先读[人工手册](../../19-manual-operations.md)、[当前交接](../../11-live-handoff.md)、[硬件事件](../../cleanup/hardware/DIMM_B1-incident.json)。11月9日已核严格SSH与分项基础状态；后续每次维护仍由主AI按准确范围核容量、挂载/UUID、身份与完整服务集合。不要以一次开机或F1跳过代替内存修复；本目录没有一键重部署入口。

所有秘密配置、数据库备份和凭据只在受保护的原位置；本目录不保存.env、渲染秘密、业务数据或SSH密钥。这里没有复制运行配置快照：旧阶段文档/模板只作带限制的来源索引，不能把10.63或旧DNAT重新当现役入口。

## 配置与证据索引

- [plan.json](../../plan.json) — `current-contract`：唯一角色/IP/资源/存储合同；状态字符串不等于实时在线。
- [19-manual-operations.md](../../19-manual-operations.md) — `current-contract`：硬件恢复、日常检查、受控启停与备份人工门禁。
- [11-live-handoff.md](../../11-live-handoff.md) — `current-contract`：当前补齐范围、无Java业务、发布冻结与维护顺序。
- [migration-plan.json](../../network19/migration-plan.json) — `historical-evidence`：原19网迁移合同含已退役角色，现役地址与角色以plan.json为准，不能重跑迁移器。
- [final-live-check.json](../../cleanup/final-live-check.json) — `historical-evidence`：2026-11-07 02:35综合验收，含本机hostname/IP/fish/默认Bash；不能代表当前在线。
- [DIMM_B1-incident.json](../../cleanup/hardware/DIMM_B1-incident.json) — `historical-evidence`：UEFI0058与DIMM_B1历史事故，现已恢复并完成本轮基础核验。
- [guest230.json](../../cleanup/fish/evidence/guest230.json) — `historical-evidence`：本来宾fish安装与默认登录shell未更改证据。
- [execution-status.json](../../cleanup/monitoring/ten-role/execution-status.json) — `historical-evidence`：清理后10来宾监控合同部署回执，旧数量不得作为实时UP。
- [guest-targets.json](../../cleanup/monitoring/ten-role/candidates/vm230/guest-targets.json) — `historical-evidence`：已审19网监控目标输入；全角色列表属于当时10节点，非直接重部署入口。
- [03-templates-and-access.md](../../03-templates-and-access.md) — `current-contract`：单一Java验收模板9011与克隆身份/运行基础边界。
- [java240-foundation-only-readback.json](../../network19/services-core/java240-foundation-only-readback.json) — `historical-evidence`：VM240 19网阶段基础可读/JDK/无业务/发布冻结证据；不把结果推作230实测。
- [README.md](../../infra/java/runtime/README.md) — `historical-evidence`：早期五业务发布实现；旧10.63和LAN DNAT已退休，不是现役启动手册。
- [README.md](../../infra/publisher/README.md) — `historical-evidence`：旧受限发布链机制与演练记录；当前fenced，不重新发布。
- [production-runtime-base-verification.json](../../evidence/implementation/production-runtime-base-verification.json) — `historical-evidence`：原正式JDK21与非root基础烟测，含已退休231/232和旧地址，只取230历史基础事实。

## 统一资源目录（新增280）

本机作为已批准NFS客户端，目标`192.168.19.80:/ → /mnt/resources`，与另一台running使用同一目录，不区分prod/test。server 100GiB数据盘与NFS启动见[server回执](../../completion/20261109-resources/server-installed.json)，本机真NFS/guard与双机非rootfixture已由[独立native验收](../../completion/20261109-resources/native-acceptance.json)通过；[仅280重启](../../completion/20261109-resources/reboot-exercise.json)后两client挂载/guard恢复、fsync共享canary保留，未重启本机OS。finger保UID999/GID989，仅追加resources附属GID2980，server root_squash/2770/defaultACL；客户端hard、nfs4.1、TCP2049、nodev/nosuid/noexec与automount。

共享是网络挂载，不是给本机格式化新数据盘。仅安装NFS基础不启动Java、不启HTTP、不迁文件、不把共享内容纳入当前正式DB/Nacos自动备份；未来业务挂载依赖drop-in仍未安装。模板预置disabled挂载只是建议，本次未改三模板。[详细使用与故障手册](../../completion/20261109-resources/usage-manual.md)、[280机器合同](../vm280-resource-service/README.md)。

[00:20最终后检](../../completion/20261109-resources/final-postcheck.json)确认13来宾/3模板、16/16监控targetsUP、PVE全部forward0。合法挂载stack是systemd-1 autofs＋唯一`192.168.19.80:/` nfs4，可用`findmnt -t nfs4 --mountpoint /mnt/resources`区分；仅autofs仍不算真NFS。fixture提前用umask0002，文件实际660/组2980；首轮失败与清理保留，未改服务来追过。

应用接入仍未执行：Finger `file.upload.path=/mnt/resources`仅建议值，未改Nacos/profile或启动Java；HTTPdomain/公开图片URL未搭。Puyu images仍在MySQL，经权限下载接口访问，NFS不自动迁出。新资源不改变现行仅正式DB/Nacos备份范围。
