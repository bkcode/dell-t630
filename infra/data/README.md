> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 基础组件部署包

状态：VM200正式MySQL与VM201正式基础组件已部署，并完成真实认证、隔离与专用fixture重启持久化验收。VM210测试数据部署已明确交给pve_audit，本agent未部署或验收它。本轮未修改PVE/网络、未启停本机源容器、未复制源业务数据或CF资料。

## 角色与固定版本

| 角色 | 服务 | 容器内存上限合计 | 来宾预算/余量 |
| --- | --- | ---: | --- |
| prod-db | MySQL 8.4.5 | 12 GiB | 16 GiB / 4 GiB |
| prod-infra | Nacos 2.4.3、Redis 7.4.4、RabbitMQ 3.13.7-management | 5 GiB | 8 GiB / 3 GiB |
| test-data | 独立 MySQL、Nacos、Redis、RabbitMQ，同版本 | 2.625 GiB | 4 GiB / 1.375 GiB |

版本来自本机当前实际镜像；RabbitMQ 源容器的实际版本为 3.13.7。四个目标镜像均经 registry manifest 检查，固定为 `linux/amd64` 的 digest，详见 `images.lock.json`。ARM64 源镜像不直接搬到 T630。

内存余量覆盖来宾 OS、Docker、缓存及波动，不是服务容量保证。test-data 为小规模模块联调用，MySQL max_connections=40；完整测试服务集需重新预算并实测。容器 swap 上限等于内存上限，避免通过无限 swap 掩盖预算不足。

## 文件与秘密

- `compose.prod-db.yaml`、`compose.prod-infra.yaml`、`compose.test-data.yaml`：三套目标配置，均有健康检查和日志轮转；restart=no，所有 bind 关闭自动创建宿主目录。
- `vendor/nacos-mysql-schema-2.4.3.sql`：官方同版本 schema，原样保存；`vendor/nacos-application-2.4.3.properties`：官方 Docker 同版本配置模板，原样保存；源 URL 与 SHA256 见锁文件。
- `prepare.py`：生成或复用随机秘密，渲染独立私有 bundle，不执行 Docker up。
- `scripts/manage.py`：在分配的来宾执行 `check`、`deploy`、`bootstrap-nacos`、`health`；`supervise/stop` 由 systemd 使用。
- `validate.py`、`validation.json`：本地配置验收，不启动容器。
- `../../private/data/store/prod`、`test`：稳定秘密库，文件 0600，目录 0700；重复 prepare 不轮换密码。
- `../../private/data/bundles/ROLE`：给主 AI 复制到对应来宾的完整私有包，包含其所需秘密。不要发布、打印或提交此目录。

Compose 环境中不直接写入密码。MySQL 使用 `_FILE`，Nacos entrypoint 从秘密文件读取；Redis 在容器内生成仅运行用户可读配置，RabbitMQ 导入包含加盐 SHA256 密码哈希的私有 definitions。deploy 在目标查询实际镜像 UID/GID，再调整秘密与配置文件所有权，保持 0600，避免非 root 服务读不到秘密。

正式与测试拥有独立 MySQL root/Nacos DB 密码、Redis 密码、RabbitMQ 管理/应用账号、Nacos 管理/应用密码和 JWT/服务器身份。prod-db 与 prod-infra 只共享正式 Nacos DB 连接秘密；test 不共享。管理员账号 `nacos` 是 Nacos 官方固定初始化身份，两个实例密码独立；应用账号分别为 finger_prod / finger_test。

## 地址与生成命令

主AI已验证的私网地址：prod-db VM200=10.63.10.10、prod-infra VM201=10.63.10.11、test-data VM210=10.63.20.10。200/201已真实部署；210由另一agent独占实施，其状态以独立证据为准。

```bash
python3 infra/data/prepare.py prod-db --service-ip 10.63.10.10
python3 infra/data/prepare.py prod-infra --service-ip 10.63.10.11 --mysql-host 10.63.10.10
python3 infra/data/prepare.py test-data --service-ip 10.63.20.10
python3 infra/data/validate.py
```

默认数据挂载点 `/srv/dell-data`，数据目录 `/srv/dell-data/ROLE`，安装目录 `/opt/dell/data/ROLE`。可通过 `--data-mountpoint`、`--data-root`、`--install-dir` 适配主 AI 已分配的数据盘；`--namespace-id` 可指定经确认的 namespace UUID。prepare 的默认 namespace 是稳定的、正式/测试不同的 UUID，不代表源端 namespace 已迁移。

部署前必须在对应来宾测得数据文件系统 UUID，再使用 `--data-uuid` 重新生成该角色包。数据盘尚未创建时此值保留 pending；没有实测 UUID，运行端会拒绝启动。重复 prepare 保留已登记 UUID，不自动接受新盘身份。数据路径禁止 `..`、非规范形式和符号链接；运行时逐个核对所有写入目录实际属于预期精确挂载点、source 和 UUID，拒绝嵌套挂载或根盘回落。

服务只绑定传入的来宾 IP：MySQL 3306，Redis 6379，RabbitMQ 5672/15672，Nacos 8848/9848。未发布 RabbitMQ 集群和 Nacos 服务端集群端口。正式/测试通过独立 VM、子网和主 AI 防火墙规则隔离；此 Compose 本身不能代替跨区 ACL。

## 主 AI 部署顺序

1. 创建并验收来宾、ub 密钥登录、Docker Engine/Compose、时钟、DNS、出站镜像访问。先布置网络允许列表，Nacos 管理初始化期间不能经 Tunnel/公网开放。
2. 准备并确认 SSD 来宾数据盘和真实挂载点。本包不格式化、不挂载磁盘；数据目录缺失挂载时拒绝部署。H730 阵列重建期间不向 store 执行大写入。
3. 将对应私有 bundle 安全复制到其 `INSTALL_DIR`，由 root 管理，保留 0700 目录和 0600 秘密。不同角色不要互相复制 bundle。
4. 在目标来宾内执行：

```bash
sudo python3 /opt/dell/data/prod-db/scripts/manage.py check
sudo python3 /opt/dell/data/prod-db/scripts/manage.py deploy
```

5. prod-db 健康后部署 prod-infra；test-data 独立部署。将上例路径替换成对应角色。
6. 首次 deploy 会等待全套健康，再按 Nacos 2.4.3 官方 API 初始化管理员、环境 namespace、独立应用用户及其 namespace 范围的 rw 权限。重复执行先认证并检查已存在对象，不重置现有管理员密码。
7. `health` 要求 Compose 配置中的完整服务集合与实际容器集合完全相等，拒绝缺失、额外或重复服务，再检查逐服务 running/healthy。还验证 Nacos 管理/应用认证、本 namespace 读权限及其他 namespace 拒绝，RabbitMQ 应用 AMQP 认证和 vhost 可达；不发布业务消息。输出脱敏 JSON，`health.json` 与有容量上限的详细命令输出保存在目标私有包。

manage 拒绝 PVE 宿主、非 Linux/AMD64、IP 不属于本机、远程 DOCKER_HOST 和未通过数据挂载身份验证的环境；Docker 命令始终固定本地 Unix socket。重复 deploy 复用数据目录和秘密，受控停止旧目标服务再启动，不清空卷，不执行 down -v，不删除源数据。MySQL schema 仅在新空数据目录首次初始化执行；已存在的非空目录若缺表将健康失败，不自动覆盖或重新初始化。

## 开机与运行期恢复

容器自身 restart=no，禁止 Docker 开机时绕过磁盘检查自动启动。deploy 在对应来宾安装并启用 `dell-data-ROLE.service`，不修改 PVE。单元使用 `RequiresMountsFor`、对精确 mount unit 的 `BindsTo/After`、ExecStartPre UUID 校验，并由 supervise 启动与监控整组容器。所有 bind 的 create_host_path=false，目录缺失时 Docker 不自动在根盘创建替代目录。

- VM 重启：数据盘必须先通过按 UUID 配置的持久挂载，systemd 才启动服务；无盘、错 UUID、只读或错误目录归属均停止启动。
- 运行期间：每约 5 秒复查挂载身份和完整服务健康；发现缺服务、退出、不健康或挂载异常，停止整组容器并由 systemd 按 on-failure/10 秒策略重试。重启频率受 600 秒/5 次限制，不是无限快速拉起。
- mount unit 消失或 Docker 服务停止：BindsTo 停止应用单元，容器不会自行重启。修复正确磁盘挂载或 Docker 后，由管理员检查状态并显式 `systemctl reset-failed dell-data-ROLE.service`、`systemctl start dell-data-ROLE.service`；不承诺设备重新出现后自动恢复。
- 健康检查只改变 Docker health 状态，Docker 本身不会因为 unhealthy 自动重启；恢复职责在本单元。应用级失败会重启本角色整组服务，不是单容器无缝恢复。
- 停止动作不依赖数据挂载或业务 IP 仍可用，避免故障时因为前置检查失败而无法停写。

200/201已完成受控角色重启并用专属fixture验证持久化；这不等于整机重启、掉盘或完整灾难恢复通过。数据盘失效和整机故障仍需独立演练，不承诺零IO错误或业务无中断。

## 数据与验收边界

当前包只建空的 Nacos 元数据库和基础设施账号/namespace，没有创建 Finger 业务数据库、业务表、业务账号，没有导入 Nacos 配置或源端业务状态。Nacos 配置导出不包含全部用户和权限；namespace ID、group/dataId、账号权限与生效目标需独立迁移验收。

Redis 是否保留数据、RabbitMQ 待处理消息及 definitions、业务 MySQL 数据和权限、Nacos namespace/配置保留范围由主 AI 统一处理。Rabbit definitions 只是新实例账号和 vhost 初始化，不含任何源队列消息、队列或业务交换机，不能代替消息保全方案。业务数据库权限应按 provider 数据库配置单独创建，禁止将 MySQL root 或 Nacos DB 用户直接交给所有 Java 服务。

静态验证通过不代表目标 CPU/RSS/启动时间、数据库持久化重启、正式/测试跨区拒绝、实际 API、业务恢复或备份已验收。目标运行后仍需主 AI 留证；health 的 scope 明确为 infrastructure-only，不证明业务迁移完成。

## 官方依据

- https://raw.githubusercontent.com/alibaba/nacos/2.4.3/distribution/conf/mysql-schema.sql
- https://raw.githubusercontent.com/nacos-group/nacos-docker/v2.4.3/build/conf/application.properties
- https://raw.githubusercontent.com/alibaba/nacos/2.4.3/plugin-default-impl/nacos-default-auth-plugin/src/main/java/com/alibaba/nacos/plugin/auth/impl/controller/UserController.java
- https://raw.githubusercontent.com/alibaba/nacos/2.4.3/plugin-default-impl/nacos-default-auth-plugin/src/main/java/com/alibaba/nacos/plugin/auth/impl/authenticate/AbstractAuthenticationManager.java
- https://www.rabbitmq.com/docs/3.13/definitions
- https://docs.docker.com/engine/storage/volumes/

## 本轮真实结果与修复

- VM200：MySQL8.4.5；root与受限Nacos DB用户认证通过，系统库越权拒绝，专用InnoDB fixture跨受控重启保留并已删除。最终只读查询确认正式业务schema数量0，仅nacos_prod元库及系统库。
- VM201：Nacos2.4.3、Redis7.4.4、RabbitMQ3.13.7，完整三服务healthy。Nacos应用用户仅本namespace可读、其他namespace403；Redis AUTH通过、匿名NOAUTH；Rabbit应用AMQP与管理认证通过。
- VM201保留修复前专属fixture，经Redis容器重建与再次受控重启后，Redis AOF key、Nacos config、独立Rabbit vhost的持久化合成消息均保留；随后清理专属对象。最终Redis DBSIZE=0、验收vhost数量0、无active fixture state。Nacos审计历史可保留，不冒充物理清零。
- 所有密码保持原值，只以私有文件/SSH STDIN传输；没有源业务数据导入正式环境。

首次执行发现并修复三项真实问题：新systemd单元未load时reset-failed返回1，现仅is-failed成功时重置；Redis重启写sticky-/tmp旧配置被protected_regular拒绝，现使用root0711的/run私有1MiB tmpfs配置，启动后配置归redis用户0600；Type=simple调用侧看到旧exited状态过早报错，现仅deploy/受控restart调用侧给15秒过渡，严格监督器默认不忽略退出。Redis来宾单独设置vm.overcommit_memory=1，不改变PVE。

证据：

- [200/201验收汇总](../../evidence/implementation/data-deployment-acceptance.json)
- [VM200](../../evidence/implementation/data-deploy-vm200.json)、[VM201](../../evidence/implementation/data-deploy-vm201.json)
- [最终只读版本/空业务库/清理盘点](../../evidence/implementation/data-prod-final-inventory.json)
- [Redis重启RCA](../../evidence/implementation/data201-restart-diagnostic.json)及[修复后真实状态](../../evidence/implementation/data201-post-fix-live-state.json)

上述是采集时点的基础组件结果，不能替代全部业务、完整备份或RPO/RTO验收。测试环境源数据导入由主AI单独协调，不能据本包默认复制。
