> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；本期测试Nacos配置迁移已获准；不迁业务数据库、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM210 · data-test

## 本轮只读状态与备份归属

14:42:56–14:43:40分项采样：hostname/19.20/GW与DNS19.1正确，原数据UUID/ext4/rw、监督active、4容器running/healthy/RestartCount0，NTP同步、基础监控正常、failed units空。测试隔离合同保持，该14:42审计未读现役schema/配置或发消息；后续只把小快照导入独立临时实例，没有导入本机现役测试库。 证据：[本机分项审计](../../completion/20261109/core-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

**配置合同与带时点基础审计，非完整运行配置导出。** 11月7日UEFI0058/B1事故与当日02:35旧基线保留历史；用户11月8日确认内存处理/诊断通过，11月9日已按下列证据重新核验基础状态。本页文档同步没有远程变更，也不把健康状态扩写为业务数据/权限或完整恢复通过。

## 职责、身份与资源

独立测试 MySQL、Nacos、Redis、RabbitMQ，保留最小 auth/system/coms 测试 schema；不共享正式账号和持久化目录。

| 项目 | plan角色合同 |
| --- | --- |
| VMID / hostname | 210 / `data-test` |
| 主IP / bridge | `192.168.19.20/24` / `vmbr19` |
| 网关 / DNS | `192.168.19.1` / `192.168.19.1` |
| vCPU / 内存 | 2 / 4GiB |
| 环境 | `test` |
| PVE系统盘存储 | `store` |
| 启动顺序 / 等待 / 关机超时 | 12 / 90s / 120s |

唯一资源/IP来源为[plan.json](../../plan.json)；[config.json](config.json)是本目录的非秘密角色摘要，不替代plan。来源与SHA见[config-sources.json](config-sources.json)，均指向已存在的仓库公开文件。

## 存储与应用监督

系统盘放在 `store`；独立数据盘 **40GiB / store**，ext4 UUID `dd1773f9-aa48-4401-a9c8-caf0f66845f3`，精确挂载点 `/srv/dell-data`，本角色数据根 `/srv/dell-data/test-data`。不得按sda/sdb猜盘，不得无盘时在根盘创建同名目录冒充恢复。

安装位置 `/opt/dell/data/test-data`，统一由 `dell-data-test-data.service` 管理 Compose 的完整服务集合：`mysql, nacos, redis, rabbitmq`。容器自身 `restart=no`；unit先验证精确挂载/UUID、禁止路径逃逸，再起整组服务并监督完整集合，缺服务不能算健康。故障恢复可能重启整个角色，修复缺盘后需人工核查；不裸起Compose、不执行down -v、不初始化已有数据。

版本为mysql:8.4.5; nacos/nacos-server:v2.4.3; redis:7.4.4; rabbitmq:3.13.7-management，固定AMD64 digest记录在[config.json](config.json)。这里只索引公开参数化Compose；实际渲染包含秘密，不复制进机器目录。恢复后须对现役安装文件与19网参数做fresh核对，不能照旧10.63 README重新prepare覆盖。

## 测试Nacos配置现状：36项原样导入完成

用户最新明确授权本机Nacos配置迁移，**覆盖先前“只搭空服务、不迁配置”的限制**；仍不迁业务数据库、不动正式环境、不启动Java或修改源码profile。同一测试入口`http://192.168.19.20:8848/nacos/`内现有配置如下，namespace ID/name、group与正文保持源原样：

| namespace | ID | 当前配置数 |
| --- | --- | ---: |
| finger-cloud-dev | `08e7191f-3ccd-411a-be00-56798d237533` | 32 |
| finger-trascan | `7bfe03c6-0590-4ff0-8def-e07015016b54` | 4 |
| finger-test（旧域） | `10719261-2641-590a-b821-c8484ca955ac` | 0 |
| finger-test-empty | `23836f2e-9553-5948-84cd-431b2f241bd6` | 0 |
| public | 默认域 | 0 |

[applied](../../completion/20261109-nacos-config-import/applied.json)与[只读verified](../../completion/20261109-nacos-config-import/verified.json)确认合计36项、当前全部group为`DEFAULT_GROUP`，类型35 yaml＋1 text，正文及type/appName/desc等受审元数据在私有流程exact比对通过。原样内容可能仍含源本地连接参数，**没有端点适配，不代表服务器应用已可运行**。

现有测试应用账号`finger_test`原权限仍只覆盖旧finger-test和finger-test-empty两域，**没有grant新导入的两个source namespace**。管理员可管理这两域；未来业务接入须另行明确namespace与应用权限，不能为消除403重置密码/role或自动提权。基础.env/health仍指旧域保兼容，不改源码profile、不启动Java。

旧7项已有guest受保护完整快照；首次删除2项后缓存读回触发安全停止，修复为只读有界等待后，新run另备剩5项、清5→0→导36，没有覆盖旧备份或盲目resume。旧配置history继续保留/产生正常API审计，namespace、用户/role/permissions、业务DB及服务未写，缺失的两source域仅建元数据。这里只记录计数/比较结论，不放旧配置内容、正文hash或密码；后续证据见[导入目录](../../completion/20261109-nacos-config-import/)。

20:27[空域创建](../../completion/20261109-test-env/empty-namespace-created.json)当时“旧7项/历史9保留、新空域0”仍是历史事实；后来用户授权清全部配置并导源，当前旧域已0，不能继续称仍有7项。账号凭据仍只由原受保护文件/渠道保管，不在本文披露值。


## 依赖与环境边界

独立测试 MySQL、Nacos、Redis、RabbitMQ，保留最小 auth/system/coms 测试 schema；不共享正式账号和持久化目录。

四组件及MySQL/Nacos/Redis/Rabbit密码、namespace/vhost与正式实例分开。最小测试schema与合成账号不是生产数据；历史测试Nacos配置不表示允许启动Java业务。

TCP服务端口为 `3306, 8848, 9848, 6379, 5672, 15672`，仅在指定本机19地址按原配置监听；已批准的bridge ACL和应用认证共同约束访问，不因可达就放宽账号权限。Nacos、Rabbit管理端口不得自动经CF公开。

## 测试Nacos的普通LAN访问

现有入口`http://192.168.19.20:8848/nacos/`及客户端TCP9848已允许`192.168.21.0/24`访问，GW转发与PVE桥两层专属规则均完成独立确认：[网关](../../network19/lan-nacos-20261109/gateway-confirmed.json)、[桥](../../network19/lan-nacos-20261109/bridge-confirmed.json)、[网关独立核查](../../network19/lan-nacos-20261109/gateway-independent-check.json)、[桥独立核查](../../network19/lan-nacos-20261109/bridge-independent-check.json)。仅这两个测试Nacos端口，原管理例外及Nacos登录/namespace权限继续生效；没有放开数据库、SSH、集群9849或正式Nacos，也未重启服务。

Studio21.230 HTTP200/TCP9848成功，同来源test3306/22/9849和prod19.11:8848/9848实际timeout，见[负测](../../network19/lan-nacos-20261109/LAN-negative-tests.json)。[Air反馈](../../network19/lan-nacos-20261109/Air-user-confirmation.json)为用户明确访问成功，但未提供逐项命令输出。ICMP没有随本次规则扩展，ping可能不通，不能作为Nacos可用性判据；分别检查HTTP、9848 TCP和既有认证即可，不重置密码或披露私有凭据。本次无NAT、hostforward保持0、WG原许可不变，不改数据或profile。

## SSH、Shell与网络

日常按已批准维护范围，用 `ub` 和客户端 `~/.ssh/yang_local_rsa`，严格核对 `dell-vm210` 既有host key；私钥只在客户端，不进入VM配置目录或Git。更换IP不等于重新信任任意主机，不关闭known_hosts校验，不拷贝别台机器host key。

fish已安装（包版本4.0.2-1）；root/ub默认仍为Bash，没有自动chsh。19网经VM190/19.1路由到OW，PVE21.22只做管理和二层桥、host forwarding=0、无宿主NAT。已授权WireGuard源10.66.66.0/24访问服务器服务；应用认证与原角色ACL继续生效。

基础exporter端点 `192.168.19.20:9100` 由Ops按既有规则采集，collector只输出本机状态，不输出凭据。本轮已按下方审计核基础状态；历史功能通过不代替本轮未重做的认证/内容检查。后续维护时仍核真实监听、单元与指标新鲜度。

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
- [guest210.json](../../cleanup/fish/evidence/guest210.json) — `historical-evidence`：本来宾fish安装与默认登录shell未更改证据。
- [execution-status.json](../../cleanup/monitoring/ten-role/execution-status.json) — `historical-evidence`：清理后10来宾监控合同部署回执，旧数量不得作为实时UP。
- [guest-targets.json](../../cleanup/monitoring/ten-role/candidates/vm210/guest-targets.json) — `historical-evidence`：已审19网监控目标输入；全角色列表属于当时10节点，非直接重部署入口。
- [compose.test-data.yaml](../../infra/data/compose.test-data.yaml) — `current-contract`：公开参数化Compose结构与资源上限；不是含现役IP/秘密的完整rendered配置。
- [images.lock.json](../../infra/data/images.lock.json) — `current-contract`：固定linux/amd64镜像版本与digest。
- [manage.py](../../infra/data/scripts/manage.py) — `current-contract`：来宾挂载/完整服务集合/认证监督器源码；部署需重新审查实际目标和配置，不能在未核实际目标/版本时重跑。
- [README.md](../../infra/data/README.md) — `historical-evidence`：组件设计/监督/秘密边界；原10.63地址与原阶段210待部署文字已过时，仅技术记录。
- [role210-commit-start-evidence.json](../../network19/services-core/role210-commit-start-evidence.json) — `historical-evidence`：组件迁移19网后的受控commit/start回执，不作为当前健康证明。
- [test-data-deployment.json](../../evidence/implementation/test-data-deployment.json) — `historical-evidence`：独立测试四组件部署/认证与持久化原始证据。
- [data-environment-isolation-final.json](../../evidence/implementation/data-environment-isolation-final.json) — `historical-evidence`：正式/测试隔离验收原始记录；旧网历史不能代替19桥ACL现场。
