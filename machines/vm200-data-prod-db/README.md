> 2026-11-08恢复：本机已完成基础存活/地址/服务检查，详见[恢复记录](../../recovery/20261108/README.md)；本轮不迁移、不升级应用，不需要Mac外部探针。下列旧验收/暂停描述按原时点解释，配置与最新检查见config.json。

# VM200 · data-prod-db

**配置合同与最后验收资料，非当前在线声明。** 最后综合验收：2026-11-07 02:35:01 +08:00；服务器现因UEFI0058内存错误停留在硬件处理阶段，历史SEL指向DIMM_B1。用户已暂停服务器操作，本轮仅本地整理；未连接、部署、克隆或运行QA。

## 职责、身份与资源

正式 MySQL 与正式 Nacos 外部元数据库，正式业务 schema 保持为空。

| 项目 | plan角色合同 |
| --- | --- |
| VMID / hostname | 200 / `data-prod-db` |
| 主IP / bridge | `192.168.19.10/24` / `vmbr19` |
| 网关 / DNS | `192.168.19.1` / `192.168.19.1` |
| vCPU / 内存 | 6 / 16GiB |
| 环境 | `prod` |
| PVE系统盘存储 | `local-lvm` |
| 启动顺序 / 等待 / 关机超时 | 10 / 60s / 120s |

唯一资源/IP来源为[plan.json](../../plan.json)；[config.json](config.json)是本目录的非秘密角色摘要，不替代plan。来源与SHA见[config-sources.json](config-sources.json)，均指向已存在的仓库公开文件。

## 存储与应用监督

系统盘放在 `local-lvm`；独立数据盘 **80GiB / local-lvm**，ext4 UUID `d61c0e22-941e-447a-9e9a-1e9e50deb02f`，精确挂载点 `/srv/dell-data`，本角色数据根 `/srv/dell-data/prod-db`。不得按sda/sdb猜盘，不得无盘时在根盘创建同名目录冒充恢复。

安装位置 `/opt/dell/data/prod-db`，统一由 `dell-data-prod-db.service` 管理 Compose 的完整服务集合：`mysql`。容器自身 `restart=no`；unit先验证精确挂载/UUID、禁止路径逃逸，再起整组服务并监督完整集合，缺服务不能算健康。故障恢复可能重启整个角色，修复缺盘后需人工核查；不裸起Compose、不执行down -v、不初始化已有数据。

版本为mysql:8.4.5，固定AMD64 digest记录在[config.json](config.json)。这里只索引公开参数化Compose；实际渲染包含秘密，不复制进机器目录。恢复后须对现役安装文件与19网参数做fresh核对，不能照旧10.63 README重新prepare覆盖。

## 依赖与环境边界

正式 MySQL 与正式 Nacos 外部元数据库，正式业务 schema 保持为空。

VM201使用本机正式Nacos元库；正式业务schema仍为空，不导入Mac业务行。

TCP服务端口为 `3306`，仅在指定本机19地址按原配置监听；已批准的bridge ACL和应用认证共同约束访问，不因可达就放宽账号权限。Nacos、Rabbit管理端口不得自动经CF公开。

## SSH、Shell与网络

恢复并获准操作后，用 `ub` 和客户端 `~/.ssh/yang_local_rsa`，严格核对 `dell-vm200` 既有host key；私钥只在客户端，不进入VM配置目录或Git。更换IP不等于重新信任任意主机，不关闭known_hosts校验，不拷贝别台机器host key。

fish已安装（包版本4.0.2-1）；root/ub默认仍为Bash，没有自动chsh。19网经VM190/19.1路由到OW，PVE21.22只做管理和二层桥、host forwarding=0、无宿主NAT。已授权WireGuard源10.66.66.0/24访问服务器服务；应用认证与原角色ACL继续生效。

基础exporter端点 `192.168.19.10:9100` 由Ops按既有规则采集，collector只输出本机状态，不输出凭据。最后验收为历史通过，硬件恢复后仍须核真实监听/单元/指标新鲜度。

## 人工操作与恢复门禁

先读[人工手册](../../19-manual-operations.md)、[当前交接](../../11-live-handoff.md)、[硬件事件](../../cleanup/hardware/DIMM_B1-incident.json)。硬件稳定且用户明确恢复后，由主AI安排fresh严格SSH、容量、磁盘/UUID、身份、完整服务集合与日志检查。不要以一次开机或F1跳过代替内存修复；本目录没有一键重部署入口。

所有秘密配置、数据库备份和凭据只在受保护的原位置；本目录不保存.env、渲染秘密、业务数据或SSH密钥。这里没有复制运行配置快照：旧阶段文档/模板只作带限制的来源索引，不能把10.63或旧DNAT重新当现役入口。

## 配置与证据索引

- [plan.json](../../plan.json) — `current-contract`：唯一角色/IP/资源/存储合同；状态字符串不等于实时在线。
- [19-manual-operations.md](../../19-manual-operations.md) — `current-contract`：硬件恢复、日常检查、受控启停与备份人工门禁。
- [11-live-handoff.md](../../11-live-handoff.md) — `current-contract`：用户暂停、无 Java 业务、发布冻结和恢复顺序。
- [migration-plan.json](../../network19/migration-plan.json) — `historical-evidence`：原19网迁移合同含已退役角色，现役地址与角色以plan.json为准，不能重跑迁移器。
- [final-live-check.json](../../cleanup/final-live-check.json) — `historical-evidence`：2026-11-07 02:35综合验收，含本机hostname/IP/fish/默认Bash；不能代表当前在线。
- [DIMM_B1-incident.json](../../cleanup/hardware/DIMM_B1-incident.json) — `historical-evidence`：UEFI0058与历史DIMM_B1事件，当前硬件暂停原因。
- [guest200.json](../../cleanup/fish/evidence/guest200.json) — `historical-evidence`：本来宾fish安装与默认登录shell未更改证据。
- [execution-status.json](../../cleanup/monitoring/ten-role/execution-status.json) — `historical-evidence`：清理后10来宾监控合同部署回执，旧数量不得作为实时UP。
- [guest-targets.json](../../cleanup/monitoring/ten-role/candidates/vm200/guest-targets.json) — `historical-evidence`：已审19网监控目标输入；全角色列表属于当时10节点，非直接重部署入口。
- [compose.prod-db.yaml](../../infra/data/compose.prod-db.yaml) — `current-contract`：公开参数化Compose结构与资源上限；不是含现役IP/秘密的完整rendered配置。
- [images.lock.json](../../infra/data/images.lock.json) — `current-contract`：固定linux/amd64镜像版本与digest。
- [manage.py](../../infra/data/scripts/manage.py) — `current-contract`：来宾挂载/完整服务集合/认证监督器源码；部署需重新审查实际目标和配置，不在暂停期运行。
- [README.md](../../infra/data/README.md) — `historical-evidence`：组件设计/监督/秘密边界；原10.63地址与原阶段210待部署文字已过时，仅技术记录。
- [role200-commit-start-evidence.json](../../network19/services-core/role200-commit-start-evidence.json) — `historical-evidence`：组件迁移19网后的受控commit/start回执，不作为当前健康证明。
- [data-deploy-vm200.json](../../evidence/implementation/data-deploy-vm200.json) — `historical-evidence`：最初部署认证和专用fixture验收，地址可能属于旧网。
- [data-prod-final-inventory.json](../../evidence/implementation/data-prod-final-inventory.json) — `historical-evidence`：正式组件版本及空业务库检查原始证据。
