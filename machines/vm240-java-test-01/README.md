> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM240 · java-test-01

## 本轮只读状态与备份归属

14:42:56–14:43:40分项采样：hostname/19.45/GW与DNS19.1正确，NTP同步、JDK21.0.13可执行、finger存在、Java进程0；旧五业务unit not-found/inactive/非enabled，exporter/timer正常。publisher冻结，不激活旧release或Nacos配置。 证据：[本机分项审计](../../completion/20261109/core-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；未restore/无异机DR，不迁移/合并/启Java、无Mac探针。

**配置合同与带时点基础审计，非完整运行配置导出。** 11月7日UEFI0058/B1事故与当日02:35旧基线保留历史；用户11月8日确认内存处理/诊断通过，11月9日已按下列证据重新核验基础状态。本页文档同步没有远程变更，也不把健康状态扩写为业务数据/权限或完整恢复通过。

## 职责、身份与资源

测试 Java 运行基础，历史五业务单元已停止/禁自启，publisher fenced；不重新激活旧 release。

| 项目 | plan角色合同 |
| --- | --- |
| VMID / hostname | 240 / `java-test-01` |
| 主IP / bridge | `192.168.19.45/24` / `vmbr19` |
| 网关 / DNS | `192.168.19.1` / `192.168.19.1` |
| vCPU / 内存 | 4 / 8GiB |
| 环境 | `test` |
| PVE系统盘存储 | `store` |
| 启动顺序 / 等待 / 关机超时 | 43 / 30s / 180s |

唯一资源/IP来源为[plan.json](../../plan.json)；[config.json](config.json)是本目录的非秘密角色摘要，不替代plan。来源与SHA见[config-sources.json](config-sources.json)，均指向已存在的仓库公开文件。

## 存储与运行基础

系统盘位于 `store`。plan未为本角色声明独立应用数据盘、数据UUID或业务挂载点，本目录不补造这些值；不得为了复制其它节点做法而格式化盘或新增挂载。历史 `/opt/finger` release/配置不能视为待自启业务。

运行基础为JDK21，普通业务运行身份 `finger`，Java路径 `/opt/finger/java/bin/java`；管理登录使用 `ub`。不使用root私有mise路径。保留基础监控，**没有应启动的Java业务systemd单元，也没有业务Compose栈**。

## 业务与依赖边界

测试 Java 运行基础，历史五业务单元已停止/禁自启，publisher fenced；不重新激活旧 release。

VM230与VM240各只保留一个运行基础；已退休231/232不重新创建。VM190提供网关/DNS，VM270只采基础节点指标；旧业务对MySQL/Nacos/Redis/Rabbit的配置不作为本阶段运行依赖。现役健康契约不包含五个业务HTTP检查，不以启动业务换取绿色验收。

VM240原五服务均已停止/禁自启，历史JAR/YAML/manifest只作受保护历史资料，不复制到此目录。Publisher baseline保持冻结，不执行adopt/stage/activate/rollback，也不发布新Nacos配置。

## SSH、Shell与网络

日常按已批准维护范围，用 `ub` 和客户端 `~/.ssh/yang_local_rsa`，严格核对 `dell-vm240` 既有host key；私钥只在客户端，不进入VM配置目录或Git。更换IP不等于重新信任任意主机，不关闭known_hosts校验，不拷贝别台机器host key。

fish已安装（包版本4.0.2-1）；root/ub默认仍为Bash，没有自动chsh。19网经VM190/19.1路由到OW，PVE21.22只做管理和二层桥、host forwarding=0、无宿主NAT。已授权WireGuard源10.66.66.0/24访问服务器服务；应用认证与原角色ACL继续生效。

基础exporter端点 `192.168.19.45:9100` 由Ops按既有规则采集，collector只输出本机状态，不输出凭据。本轮已按下方审计核基础状态；历史功能通过不代替本轮未重做的认证/内容检查。后续维护时仍核真实监听、单元与指标新鲜度。

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
- [guest240.json](../../cleanup/fish/evidence/guest240.json) — `historical-evidence`：本来宾fish安装与默认登录shell未更改证据。
- [execution-status.json](../../cleanup/monitoring/ten-role/execution-status.json) — `historical-evidence`：清理后10来宾监控合同部署回执，旧数量不得作为实时UP。
- [guest-targets.json](../../cleanup/monitoring/ten-role/candidates/vm240/guest-targets.json) — `historical-evidence`：已审19网监控目标输入；全角色列表属于当时10节点，非直接重部署入口。
- [03-templates-and-access.md](../../03-templates-and-access.md) — `current-contract`：单一Java验收模板9011与克隆身份/运行基础边界。
- [java240-foundation-only-readback.json](../../network19/services-core/java240-foundation-only-readback.json) — `historical-evidence`：VM240 19网阶段基础可读/JDK/无业务/发布冻结证据；不把结果推作230实测。
- [README.md](../../infra/java/runtime/README.md) — `historical-evidence`：早期五业务发布实现；旧10.63和LAN DNAT已退休，不是现役启动手册。
- [README.md](../../infra/publisher/README.md) — `historical-evidence`：旧受限发布链机制与演练记录；当前fenced，不重新发布。
- [java240-stop-disable-hold-evidence.json](../../network19/services-core/java240-stop-disable-hold-evidence.json) — `historical-evidence`：旧五业务停止/禁自启与不可变文件留存回执。
- [publisher240-fenced-readback-evidence.json](../../network19/services-core/publisher240-fenced-readback-evidence.json) — `historical-evidence`：测试发布baseline冻结与受限目标读回。
