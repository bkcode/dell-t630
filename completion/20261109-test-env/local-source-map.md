# 测试基础环境本地来源图（空服务范围）

更新：2026-11-09，Asia/Shanghai。用户最终范围为**只搭空基础服务，保留现有数据，不迁移、不业务初始化、不启动Java**。此前五业务源码/配置映射方向已停止，本文件只保留VM210基础必要合同，不读取或复制Mac源数据、Finger业务SQL/配置正文、Nacos body、.env值或数据库行。遵循`f-nacos-config`技能；本轮仅读本地公开合同与选定元数据，未SSH、未运行任何部署/测试脚本。

## 已有基础，不需重新搭一套

VM210 `data-test`：`192.168.19.20/24`，2vCPU/4GiB，vmbr19，GW/DNS19.1。system/data均store，数据盘40GiB，ext4 UUID `dd1773f9-aa48-4401-a9c8-caf0f66845f3`，挂载`/srv/dell-data`，数据根`/srv/dell-data/test-data`。启动order12/up90s/down120s。角色唯一来源[plan](../../plan.json)。

| 基础组件 | 固定版本 | 本机TCP端口 | 容器内存上限 |
| --- | --- | --- | --- |
| MySQL | 8.4.5 | 3306 | 896MiB |
| Nacos | 2.4.3，独立test环境/外部MySQL元库nacos_test | 8848、9848 | 1GiB |
| Redis | 7.4.4 | 6379 | 256MiB |
| RabbitMQ | 3.13.7-management | 5672、15672 | 512MiB |

公开Compose与镜像锁记录AMD64 digest，端口由`SERVICE_IP`参数绑定；只索引变量名和挂载目标，不读实际.env/秘密。容器内存合计2688MiB，4GiB余1408MiB覆盖OS/缓存等，不是容量保证。restart=no，由`dell-data-test-data.service`统一核精确挂载UUID和完整服务集合；缺盘不能落根盘，不裸起Compose、不down -v、不重置数据库身份。

[11月9日核心审计](../../completion/20261109/core-audit.json)在14:43附近已核210原UUID、四容器running/healthy/RestartCount0、GW/DNS、NTP/exporter与failed[]；本任务未做新远程采样。后续[隔离恢复回执](../../completion/20261109-prod-db-restore/semantic-attempt-observation.json)只在210临时实例恢复一份正式Nacos小档并清理，原四服务保持；**临时nacos_prod的config_info为空，不能据此推断现役测试nacos_test为空**。

9001为保留Docker核心模板；旧provision创建规则对data-test选择9001，但原provision回执本身没有单列templateID。当前210已经存在，不需要clone、重做模板或重置SSH/machine-id；不把模板overlayfs profile强套现有应用角色存储后端。ub严格SSH/原known_hosts，fish已装、默认Bash保持。

## test namespace：存在有历史证据，当前为空没有证据

基础bootstrap合同的test namespace UUID为`10719261-2641-590a-b821-c8484ca955ac`，显示名合同`finger-test`，稳定UUID5推导匹配。[11月6日部署final-health](../../evidence/implementation/test-data-deployment.json)证明namespace存在、test应用可读本namespace且他namespace拒绝。

[11月6日14:30隔离元数据](../../evidence/implementation/data-environment-isolation-final.json)记录该namespace在`DELL_TEST`组至少有**6项已记录配置**（这里只证明记录中的6项GET状态200，不证明当时namespace配置总数恰好为6）；这里只取namespace/group/count，没有读取配置正文、dataId列表、数据库行或凭据。它不是历史空namespace。当前是否仍有6项/另有空namespace，本地文件不能证明；**不把“空服务”变成清namespace/删库/重新seed，已有配置与数据全部保留**。

如主AI需要当前空/非空证明，只读列namespace的ID/name/configCount即可，不GET配置body、不删旧配置；public默认域也不自动当test隔离域。若确需另一个全空namespace，须明确新身份且不与旧域碰撞；本文件不自行新建、不迁移配置或初始化业务。

## 网关、DNS、ACL与监控合同

PVE21.22仅管理/L2，forward0/无hostNAT；190 WAN21.23/LAN19.1提供路由/DNS，OW21.1为公网出口。同19/24由bridge MAC/IP角色ACL隔离，不能靠GW替代。既有240→210的3306/6379/5672/8848/9848权限只保留网络合同，**不代表Java获准启动**；270→210:9100采集保留。普通管理来源21.22/21.116有既有数据端口许可；受信VPN10.66.66.0/24按原全服务授权，应用认证不变，不新增端口或公网暴露。

exporter为19.20:9100，collector/timer采用既有基础合同；十角色catalog仍含210，不新增业务HTTP检查。本任务不改DNS、MAC/ACL、监听、监控目标或告警，不触Mac外部探针。新自动备份当前仅正式DB/Nacos，测试数据不因为本计划自动纳入。

## 可参考的来源与禁止重跑的旧入口

- `infra/data/compose.test-data.yaml`、`images.lock.json`及role/UUID合同可复用为差异核对依据，不是现役渲染秘密包。没有基础缺项就不重装；“空服务”也不需要业务Spring profile或五业务config。
- `prepare.py`会写private bundle并生成/保留秘密，不是只读检查。`manage.py deploy`会stop旧监督/容器、创建/启用新服务；`bootstrap-nacos`会创建基础管理员/namespace/user/role/permission。已有实例不能直接重跑，若真缺项仅由主AI审准确最小修补。
- `manage.py check/health`也不能当成本轮严格只读、不读body的入口：共享run会写私有日志；health的Nacos probe会读取响应body。当前只参考代码中的身份/挂载/完整服务集合检查，后续使用单独的纯元数据探测。
- `acceptance.py`含fixture/SQL/持久化重启验证写入，不执行。旧`prepare-test-chain.py`/`apply-test-sql.py`/`publish-test-nacos.py`/`manager-init-test.py`是业务schema/seed/Nacos配置初始化或生成，部分含10.63旧网约束；当前范围全部排除。
- 旧Java stage/activate/deploy链、provision-guests、guest-network和stage-core是业务发布、VM创建或网络迁移入口，不能用“补空服务”重放；publisher继续fenced，Java不启动。原Mac数据、正式库和既有测试数据不动。

## 来源索引

- [plan.json](../../plan.json) — VM210身份/IP/资源与挂载合同。
- [03-templates-and-access.md](../../03-templates-and-access.md) — 保留模板9001/9010/9011与身份卫生；不新clone或重做现役身份。
- [infra/provision-guests.py](../../infra/provision-guests.py) — data-test按旧创建器走9001；创建器有PVE写与旧默认网络，不可重跑。
- [evidence/implementation/guests-provisioned.json](../../evidence/implementation/guests-provisioned.json) — 原210已创建记录，模板源仅由创建器规则推导。
- [infra/data/compose.test-data.yaml](../../infra/data/compose.test-data.yaml) — 公开参数化四组件结构，非现役秘密渲染快照。
- [infra/data/images.lock.json](../../infra/data/images.lock.json) — 固定官方AMD64版本/digest。
- [infra/data/prepare.py](../../infra/data/prepare.py) — 通用基础包生成器；写私有bundle/秘密，不能当只读或无差异重部署工具。
- [infra/data/scripts/manage.py](../../infra/data/scripts/manage.py) — 统一挂载监督与Nacos基础账号/namespace bootstrap语义；run会写日志，deploy会停启。
- [infra/data/scripts/acceptance.py](../../infra/data/scripts/acceptance.py) — 包含fixture创建/SQL写/重启验证，当前不得执行。
- [completion/20261109/core-audit.json](../../completion/20261109/core-audit.json) — 14:43最新基础状态记录，未查namespace configCount或业务内容。
- [completion/20261109-prod-db-restore/semantic-attempt-observation.json](../../completion/20261109-prod-db-restore/semantic-attempt-observation.json) — 仅VM210临时隔离恢复，原4服务保持；不能据prod快照空配置推test namespace为空。
- [evidence/implementation/test-data-deployment.json](../../evidence/implementation/test-data-deployment.json) — 11月6日Nacos namespace存在与隔离认证通过元数据。
- [evidence/implementation/data-environment-isolation-final.json](../../evidence/implementation/data-environment-isolation-final.json) — 仅取namespace/group/count元数据；该test namespace历史6配置，不取body/DB rows。
- [network19/migration-plan.json](../../network19/migration-plan.json) — 现役19地址/GW/DNS/许可矩阵，含历史阶段与退役角色时按plan过滤。
- [network19/audit/render-bridge-acl.py](../../network19/audit/render-bridge-acl.py) — 同19网MAC/IP绑定与240→210数据端口/270→210 exporter合同，仅读不render/apply。
- [cleanup/network/dns-runtime/summary.json](../../cleanup/network/dns-runtime/summary.json) — 原DNS清理及服务名称留存验证。
- [infra/ops/guest-baseline/guest-targets.json](../../infra/ops/guest-baseline/guest-targets.json) — 公开当前十角色catalog的210条目。
- [cleanup/monitoring/ten-role/execution-status.json](../../cleanup/monitoring/ten-role/execution-status.json) — 监控目录/source配对应用记录。
- [completion/20261109/ops-audit.json](../../completion/20261109/ops-audit.json) — 15targets UP与textfile采样，不当namespace空证明。

机器可读合同与边界见[local-source-map.json](local-source-map.json)。本地核对不签当前namespace为空、数据一致性、认证端到端或新的运行验收。
