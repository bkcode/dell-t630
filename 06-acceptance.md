> 2026-11-08恢复更新：用户确认内存已重新插拔/更换且诊断通过；本boot EDAC CE/UE0、RAIDOptl、12实例运行/3模板、15targets UP及6入口HTTP200已有分范围运行证据。UEFI0058/B1事故与11/07 02:35完整验收、02:44:29最后PVE操作保留为历史；不把本次基础恢复当完整硬件/应用重验。

> 2026-11-10阶段更新：用户已恢复Nexus合并与独立221退役，当前状态以[本次交付](completion/20261110-nexus-merge/README.md)、[现行架构](17-publish-artifact-consolidation.md)和[当前交接](11-live-handoff.md)为准。下文是此前基础阶段记录，旧“不合并/221独立/standby”、旧数量和版本不再作为当前现场结论，原验收与未签恢复范围按其时间保留。Java业务不启、旧链fenced；禁止重放历史初始化/迁移器。

> 本轮只补齐既有基础服务并核多余项，用户明确不迁移Nexus；Mac外部探针明确不需要，从现行/后续任务移除。见[11/08证据](recovery/20261108/host-network-postcheck.json)及[当前验收](cleanup/acceptance.json)。

# 验收标准与执行记录规范

原38项历史记录：**26项曾通过、12项未来/人工pending**；不得据此认定当前在线健康。机器可读清单见 [acceptance.json](acceptance.json)。资源与角色以 [plan.json](plan.json) 为唯一来源。

用户已授权实施整套方案。模板创建和克隆验证已执行，其余部署、迁移和恢复按任务与具体目标推进；本文列出命令本身不扩大授权。用户说明 PVE 无重要数据不替代具体测试对象、停机窗口和回退范围；本机 nacos、Penpot 和家庭影音目录仍按有实际数据处理。

## 如何使用

原严格REC-HW/BAK/DATA/NET/OBS/ROLL共6项保留pending（部分已有11/08证据，冷备/回退随迁移用户暂缓；不作为本轮基础恢复额外门禁），详细前置、步骤、通过/失败条件和计划证据路径见[cleanup验收](cleanup/acceptance.md)。本页旧重启、负测、SQL或发布命令不构成本轮执行授权。

1. 实施前完成地址、RAID、存储、账号和上线范围登记；冻结本次验收对应的 plan.json 版本/摘要。
2. 先执行文档门禁与只读前置检查，再在隔离验收实例中完成重建、并发与恢复测试；最后才安排目标环境切换。
3. 每个用例独立留证。`pending` 表示没有足够执行证据，不能解释为通过；正式执行后可由任务管理者改为 `passed`、`failed` 或 `blocked` 并关联证据。
4. P0 用例是相应模块上线的门禁。缺少适用前提时保持 pending/blocked；不把家庭NAS未上线阻塞为已经通过，也不把未上线模块混入已签收范围。
5. 性能SLO、RPO/RTO和可接受并发需要批准后验证；本文不保证单台T630高可用，也不承诺全部Java模块同时运行的容量。

执行类型：`read-only` 为只读核查；`manual-review` 为证据/设计审查；`disruptive-test` 为可能创建、修改、重启、写测试数据或增加负载的受控演练。**已执行项目依据各自证据签收；未执行的修改、恢复和负载测试保持 pending。**

## SSH 约定

PVE 与来宾登录分别验收，密钥只在本地使用，不上传或输出私钥。初次或变更后的主机指纹通过可信通道核验；不使用 `StrictHostKeyChecking=no`。以下来宾IP是占位符，必须先按实际分配填写。

```bash
ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 root@192.168.21.22 'hostname; id -un'
ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 ub@<GUEST_IP> 'hostname; id -un; id -u'
```

PVE root 登录不证明来宾 ub 登录；ub 登录不证明发布权限；发布账号可上传制品不证明业务普通用户能运行。NAS 通过ISO安装的系统账户和现有LXC账户单独登记。

## 原38项历史用例索引

| ID | 验收项 | 阶段 | 执行类型 | 当前状态 |
| --- | --- | --- | --- | --- |
| [ACC-DOC-001](#acc-doc-001) | 文档、角色和资源预算一致 | documentation | read-only | passed |
| [ACC-DOC-002](#acc-doc-002) | 证据、敏感信息与状态审查 | documentation | manual-review | passed |
| [ACC-PVE-001](#acc-pve-001) | PVE 硬件与现有实例基线 | implementation | read-only | passed |
| [ACC-PVE-002](#acc-pve-002) | RAID 成员、保护与磁盘健康 | implementation | read-only | passed |
| [ACC-PVE-003](#acc-pve-003) | 存储唯一归属与容量门限 | implementation | read-only | passed |
| [ACC-NET-001](#acc-net-001) | 地址、端口与路由登记 | implementation | manual-review | passed |
| [ACC-NET-002](#acc-net-002) | 正式与测试网络隔离 | implementation | read-only | passed |
| [ACC-NET-003](#acc-net-003) | Tunnel、家庭入口和管理面边界 | implementation | read-only | pending |
| [ACC-TPL-001](#acc-tpl-001) | 模板软件基线与卫生 | implementation | manual-review | passed |
| [ACC-TPL-002](#acc-tpl-002) | 完整克隆和实例身份去重 | implementation | disruptive-test | passed |
| [ACC-SSH-001](#acc-ssh-001) | PVE 主机访问与证据边界 | implementation | read-only | passed |
| [ACC-SSH-002](#acc-ssh-002) | 目标 Linux 实例 ub 密钥登录与管理权限 | implementation | read-only | passed |
| [ACC-SYS-001](#acc-sys-001) | 重启后的身份、数据和服务恢复 | implementation | disruptive-test | passed |
| [ACC-DOCKER-001](#acc-docker-001) | Compose 版本、健康和资源控制 | implementation | read-only | passed |
| [ACC-DOCKER-002](#acc-docker-002) | 持久化重建验证 | implementation | disruptive-test | passed |
| [ACC-DATA-001](#acc-data-001) | 数据和外部凭据隔离 | implementation | read-only | passed |
| [ACC-DATA-002](#acc-data-002) | Nacos 配置迁移与发现恢复 | implementation | disruptive-test | pending |
| [ACC-DATA-003](#acc-data-003) | Redis 与 RabbitMQ 的受控恢复和投递 | implementation | disruptive-test | pending |
| [ACC-ART-001](#acc-art-001) | Nexus 制品发布、消费和权限 | implementation | disruptive-test | passed |
| [ACC-REL-001](#acc-rel-001) | 发布权限、运行身份和回滚边界 | implementation | disruptive-test | passed |
| [ACC-JAVA-001](#acc-java-001) | 选定业务链端到端验证 | implementation | disruptive-test | passed |
| [ACC-JAVA-002](#acc-java-002) | 多实例 ID 唯一性 | implementation | disruptive-test | pending |
| [ACC-JAVA-003](#acc-java-003) | 定时任务与 Outbox 并发幂等 | implementation | disruptive-test | pending |
| [ACC-JAVA-004](#acc-java-004) | WebSocket 路由与上传持久化 | implementation | disruptive-test | pending |
| [ACC-PEN-001](#acc-pen-001) | Penpot 镜像架构和配置迁移 | implementation | read-only | passed |
| [ACC-PEN-002](#acc-pen-002) | Penpot 登录与外部访问配置 | implementation | disruptive-test | pending |
| [ACC-PEN-003](#acc-pen-003) | Penpot 设计与素材一致性恢复 | implementation | disruptive-test | passed |
| [ACC-PEN-004](#acc-pen-004) | Penpot MCP、worker 与导入任务 | implementation | disruptive-test | passed |
| [ACC-NAS-001](#acc-nas-001) | NAS 磁盘归属与共享容量 | implementation | read-only | passed |
| [ACC-NAS-002](#acc-nas-002) | SMB 家庭账号和文件权限 | implementation | disruptive-test | passed |
| [ACC-NAS-003](#acc-nas-003) | Jellyfin 家庭播放与资源控制 | implementation | disruptive-test | pending |
| [ACC-NAS-004](#acc-nas-004) | 游戏文件保存和传输完整性 | implementation | disruptive-test | pending |
| [ACC-NAS-005](#acc-nas-005) | 家庭负载对正式业务的影响 | implementation | disruptive-test | pending |
| [ACC-NAS-006](#acc-nas-006) | 已有影音配置的有选择迁移 | implementation | manual-review | passed |
| [ACC-BAK-001](#acc-bak-001) | 独立备份目的地与覆盖范围 | implementation | manual-review | pending |
| [ACC-BAK-002](#acc-bak-002) | 隔离恢复演练与 RPO/RTO 实测 | implementation | disruptive-test | pending |
| [ACC-OBS-001](#acc-obs-001) | 服务器内监控与Lark告警闭环（本期） | implementation | disruptive-test | passed |
| [ACC-CUT-001](#acc-cut-001) | 切换、限制和最终签收 | implementation | manual-review | passed |

## 证据要求

未来用例证据目标路径为 `evidence/acceptance/<ID>/result.json`；这些路径是待生成位置，当前不存在不代表测试失败或已经执行。每份记录至少含：

```json
{
  "id": "ACC-SSH-002",
  "status": "pending",
  "executed_at": null,
  "timezone": "Asia/Shanghai",
  "operator": null,
  "target": {"host": null, "vmid": null, "environment": null},
  "plan_sha256": null,
  "preconditions_checked": false,
  "commands_or_steps": [],
  "exit_codes": [],
  "observations": [],
  "artifacts": [],
  "limitations": [],
  "reviewed_by": null
}
```

截图、日志、SQL摘要和文件哈希只保留必要信息，过滤密码、私钥、token、认证头、登录默认值和个人内容。故障后重试保留每次记录，不能覆盖失败证据。备份存在、systemd active、Docker running 和HTTP首页可见只能证明各自局部状态。

## 详细用例

<a id="acc-doc-001"></a>
### ACC-DOC-001 · 文档、角色和资源预算一致

阶段：`documentation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 01～06 文档、README 和 plan.json 已保存；校验器由任务管理者提供。

**步骤 / 命令**

1. 运行 python3 scripts/validate_docs.py；读取 plan.json 计算角色数量、vCPU、内存与宿主余量。
2. 逐项核对文档索引、相对链接、现行决策和待决问题。

**通过条件**

- 角色与资源均以 plan.json 为准；当前计划为 13 个角色、53 vCPU、116.5 GiB 来宾内存。
- 以 125 GiB 计划总量计算余量约 8.5 GiB，满足当前 8 GiB 最低预留；56 为线程数，28 为物理核心。
- 只有 Linux、Docker 两个核心模板，NAS 无必需额外模板；家用 NAS 不作为正式业务备份目标。

**失败条件**

- 存在失效链接、预算不一致或把配置/文档存在写成部署验收通过。

证据目标：`evidence/acceptance/ACC-DOC-001/result.json`。

<a id="acc-doc-002"></a>
### ACC-DOC-002 · 证据、敏感信息与状态审查

阶段：`documentation`；执行类型：`manual-review`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 各子任务交付文件和只读盘点证据齐备。

**步骤 / 命令**

1. 检查 evidence 中采集时间、目标、命令或检查标识、退出码/结果、限制说明。
2. 审查新增文档和 JSON，不包含密码、私钥、token、完整认证头或登录默认值。
3. 将硬件快照、用户说明、建议值、已执行结果分开标记。

**通过条件**

- 所有部署用例实际状态是 pending，除非有后续执行记录支持。
- 文档验证通过只更新文档检查状态；停止模板内部 OS、软件和 ub 登录不得推定通过。

**失败条件**

- 暴露凭据；将 root 登录、容器 running、文档保存等替代完整业务验收。

证据目标：`evidence/acceptance/ACC-DOC-002/result.json`。

<a id="acc-pve-001"></a>
### ACC-PVE-001 · PVE 硬件与现有实例基线

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 已核验 192.168.21.22 主机密钥指纹；root 的只读 SSH 可用。

**步骤 / 命令**

1. 通过规定 SSH 连接执行 hostname、pveversion、lscpu、free -h、pvesm status、qm list、pct list。
2. 只读导出过滤凭据后的 qm/pct 配置和 /etc/pve/storage.cfg；记录模板标志、Cloud-Init 用户、磁盘依赖、运行状态。

**通过条件**

- 实测结果与 01-current-state.md 同一采集时间的证据对应；差异被记录。
- 候选 VMID 100、104 与角色的映射经过核对；新 VMID/IP 在实际分配前仍为待决。

**失败条件**

- 连接目标错误、模板仅凭名称识别、未经核实就复用 VMID/IP。

证据目标：`evidence/acceptance/ACC-PVE-001/result.json`。

<a id="acc-pve-002"></a>
### ACC-PVE-002 · RAID 成员、保护与磁盘健康

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 已有 iDRAC 或控制器只读管理通道；不安装或刷写固件来完成本次检查。

**步骤 / 命令**

1. 读取 H730 的虚拟盘级别、成员盘、阵列状态、缓存策略及电池/超级电容保护状态。
2. 读取物理盘型号、容量、介质类型和健康信息，关联至 PVE 逻辑盘。

**通过条件**

- 每个正式存储逻辑盘的成员、冗余级别和保护状态有证据；不是只凭容量推测 RAID。
- 降级、重建、预测故障及异常扇区均有处置结论；缺失管理信息则继续 pending。

**失败条件**

- 仅用 SMART PASSED 宣布阵列健康；把未知 RAID/缓存状态当生产就绪。

证据目标：`evidence/acceptance/ACC-PVE-002/result.json`。

<a id="acc-pve-003"></a>
### ACC-PVE-003 · 存储唯一归属与容量门限

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 已完成磁盘映射；系统盘、数据盘、模板、备份的预留表可审查。

**步骤 / 命令**

1. 读取 lsblk、findmnt、df -h、pvesm status、lvs 的数据/元数据使用率。
2. 核对全部虚拟磁盘和计划上限，NAS 数据盘应是 PVE 创建的独占虚拟盘。
3. 确认 store 的 ext4 和 H730 继续由 PVE 管理。

**通过条件**

- 同一文件系统不存在由 PVE、NAS 同时挂载的块设备；NAS 不依赖自己的 NFS 才能启动。
- local-lvm 和 store 均设置容量告警；本计划建议至少 20% 实际空闲，若无法满足必须先调小分配或扩容。
- NAS 初始 2048 GiB 未吞并整个 store；thin 虚拟容量和实际用量分别记录。

**失败条件**

- 整盘 /dev/sdb 或共用 H730 被直接交给 NAS；存储池已接近满载却继续分配；循环依赖。

证据目标：`evidence/acceptance/ACC-PVE-003/result.json`。

<a id="acc-net-001"></a>
### ACC-NET-001 · 地址、端口与路由登记

阶段：`implementation`；执行类型：`manual-review`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 可访问 DHCP/路由器地址分配信息，具备既有设备清单。

**步骤 / 命令**

1. 为每个角色登记 VMID、MAC、固定 IP 或 DHCP 绑定、网段、网关、DNS、用途端口。
2. 结合租约、邻居表和目标服务检查冲突；不能以 ping 无响应证明地址空闲。
3. 核对 Nacos 注册 IP 是实际来宾可达地址，检查旧 192.168.1.*、localhost 与家用 Compose 子网的残留。

**通过条件**

- 地址/端口唯一且登记完成；PVE .22 与候选发布机 .23 被明确区分。
- 跨虚拟机的注册、发现、DNS和必要 Nacos gRPC 通信按实际版本验证。

**失败条件**

- 未经冲突核查就分配 IP；服务注册到容器私网/localhost 使消费者无法访问。

证据目标：`evidence/acceptance/ACC-NET-001/result.json`。

<a id="acc-net-002"></a>
### ACC-NET-002 · 正式与测试网络隔离

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 正式与测试部署在独立虚拟机；已定义允许矩阵和已授权的 TCP 连通检查目标。

**步骤 / 命令**

1. 从测试节点对正式 MySQL、Redis、RabbitMQ、Nacos 和管理入口执行有超时的 TCP 连接检查。
2. 从正式 Java 节点检查其被允许的数据组件端口；检查 IPv4、IPv6 和管理路径。
3. 读取防火墙有效规则和命中记录，核对容器暴露端口是否越过预期访问边界。

**通过条件**

- 测试到正式的非授权路径均拒绝；业务必要路径成功；管理访问按允许矩阵工作。
- 隔离来自有效网络/防火墙策略，不仅是 Redis DB 编号、Nacos namespace 或命名。

**失败条件**

- 测试节点可连接正式数据组件；IPv6或Docker端口映射绕过规则；管理链路被误封。

证据目标：`evidence/acceptance/ACC-NET-002/result.json`。

<a id="acc-net-003"></a>
### ACC-NET-003 · Tunnel、家庭入口和管理面边界

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 域名、Tunnel 路由、管理访问方式已登记；只测试自己管理的域名与端点。

**步骤 / 命令**

1. 核对 cloudflared 服务状态、有效路由和实际业务 HTTPS/WebSocket 响应。
2. 用未登录客户端检查 PVE、NAS 管理、Nacos、数据库及 worker 内部端口没有非预期公网入口。
3. 检查家庭终端仅访问 NAS/Jellyfin 所需服务，不能访问正式数据层或发布权限。

**通过条件**

- 外部入口可到达批准的业务服务；内部管理和家庭共享按策略隔离。
- Tunnel running 不替代源站响应、身份认证和 WebSocket 验证。

**失败条件**

- 公网可直接访问敏感管理服务；家庭网络可以横向访问正式业务管理面。

证据目标：`evidence/acceptance/ACC-NET-003/result.json`。

<a id="acc-tpl-001"></a>
### ACC-TPL-001 · 模板软件基线与卫生

阶段：`implementation`；执行类型：`manual-review`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 已授权制作或检查模板；停止模板不为本用例自动启动。

**步骤 / 命令**

1. 核对 Linux 基础模板的 OS 版本、补丁、Cloud-Init、Guest Agent、时间同步与日志配置。
2. 核对 Docker 模板的 Engine/Compose 版本和日志轮转，已有 103/105 仅作为可选复用。
3. 检查无业务数据库、用户文件、真实发布凭据、Tunnel token、遗留应用注册状态。

**通过条件**

- 两个核心模板可追溯到构建步骤与版本；NAS无需模板。
- 应用 Compose、Java 构建配置和真实数据不依赖隐含模板状态。

**失败条件**

- 仅按模板名称认定软件齐备；模板包含真实业务数据、客户端私钥或环境凭据（预期管理公钥除外）。

证据目标：`evidence/acceptance/ACC-TPL-001/result.json`。

<a id="acc-tpl-002"></a>
### ACC-TPL-002 · 完整克隆和实例身份去重

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 后续实施明确授权创建两个专用验收实例；已选空闲 VMID/IP 和存储；不覆盖现有实例。

**步骤 / 命令**

1. 从目标模板创建两个完整克隆，注入各自 hostname、网络和公钥；只启动这两个验收实例。
2. 读取 PVE 磁盘 origin/backing 关系，读取两台来宾 hostname、/etc/machine-id、SSH host 公钥指纹和 MAC。
3. 核对应用实例 ID、监控标识、Snowflake 组合以及后续安装组件的身份参数。

**通过条件**

- 完整克隆不存在对模板的运行磁盘 backing 依赖；两实例可独立启动。
- 实例身份按作用域唯一；不得假设 Cloud-Init 自动完成所有应用身份去重。

**失败条件**

- 仍依赖模板 backing 盘；machine-id、SSH host key或需唯一的应用ID重复。

证据目标：`evidence/acceptance/ACC-TPL-002/result.json`。

<a id="acc-ssh-001"></a>
### ACC-SSH-001 · PVE 主机访问与证据边界

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 可信通道核验并接受 PVE 主机指纹；本地密钥可读且不输出内容。

**步骤 / 命令**

1. 执行 ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 root@192.168.21.22 'hostname; id -un'。
2. 记录目标、用户名、命令和退出码；不关闭主机密钥校验。

**通过条件**

- 返回预期 PVE 主机名与 root，退出码 0。
- 证据仅证明 PVE root 登录，不用于宣称 ub 或发布权限已通过。

**失败条件**

- 连接错误主机、需要未提供的交互密码、私钥出现在输出、跳过hostkey验证。

证据目标：`evidence/acceptance/ACC-SSH-001/result.json`。

<a id="acc-ssh-002"></a>
### ACC-SSH-002 · 目标 Linux 实例 ub 密钥登录与管理权限

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 目标 Linux 实例已在后续实施中启动、IP 已分配且指纹经可信通道核验；OMV ISO 安装后已通过受控控制台创建/确认 ub 并注入指定客户端对应公钥。

**步骤 / 命令**

1. 逐目标 Linux VM（含 OMV ISO 实例）使用指定私钥、公钥限定和严格主机密钥检查执行只读 SSH，读取 hostname、ip -br addr、id -un、id -u。
2. 核对 hostname/IP/VMID 清单及返回用户；只记录公钥指纹或已注入事实，不输出公钥原值或私钥。
3. 读取并核对已批准的 sudo 授权范围；如采用 sudo -n -l，按设计解释其结果，不要求 ub 拥有全命令免密 root 权限；用只读命令验证必要管理权限。

**通过条件**

- 每个目标 Linux VM（含 OMV）均以 ub 使用指定密钥登录，无密码回退，身份和地址匹配。
- ub 仅具备角色所需且已登记的管理权限；应用运行身份与发布权限分别验收。现有 LXC 保留单独登记账号，不凭 PVE root 登录推断其状态。

**失败条件**

- 仅一个实例成功就标记全部成功；账户是root或网络目标错误；依赖密码回退。

证据目标：`evidence/acceptance/ACC-SSH-002/result.json`。

<a id="acc-sys-001"></a>
### ACC-SYS-001 · 重启后的身份、数据和服务恢复

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 后续实施已安排维护窗口；仅先测试专用验收实例，整机重启需单独执行计划。
- NAS 负向测试仅使用专用验收实例和可丢弃测试数据盘/副本，禁止卸载、拔出或修改真实家庭媒体盘。

**步骤 / 命令**

1. 在维护窗口重启指定实例，核对固定网络、数据盘挂载、系统时间和配置。
2. 检查 Docker/systemd 服务自启动及数据库、Nacos、Java与依赖服务健康；验证依赖尚未就绪时的重试。
3. 整机重启演练时按存储/网络、数据、业务、入口顺序检查，保留实际耗时。
4. 在专用 NAS 验收实例模拟预期数据盘未挂载，尝试启动 Jellyfin-only 启动单元；记录挂载检查、容器状态、系统盘目录写入情况和告警；恢复测试挂载后再验证启动。

**通过条件**

- 实例身份和数据不变；挂载正确；业务健康检查通过，且不存在启动循环依赖。
- onboot/startup顺序与实际就绪验证一致，而非只看进程启动。
- NAS 数据挂载缺失时媒体容器不启动、不会向同名系统盘目录写入且产生告警；恢复正确挂载后正常启动。

**失败条件**

- 服务需人工补救、数据盘未挂载却写入系统盘、时间错误、备份或NAS循环依赖。

证据目标：`evidence/acceptance/ACC-SYS-001/result.json`。

<a id="acc-docker-001"></a>
### ACC-DOCKER-001 · Compose 版本、健康和资源控制

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 目标 Compose 已部署；通过安全方式读取配置，不向文档输出完整渲染Env。

**步骤 / 命令**

1. 检查实际镜像版本/digest、架构、restart policy、healthcheck、CPU/内存、日志轮转及挂载。
2. 对比 Compose 声明和 docker inspect 实际状态；确认使用 Linux Docker Engine。
3. 统计各VM的应用、运行时和OS预算，不把容器限制误认为预留内存。

**通过条件**

- 关键镜像固定可追溯版本；有健康检查及明确重启、日志策略。
- 合计预算在 plan.json 内；数据库和资产使用持久化挂载。

**失败条件**

- 关键服务使用未登记可变标签、无持久化、未限制资源导致其他角色被挤占。

证据目标：`evidence/acceptance/ACC-DOCKER-001/result.json`。

<a id="acc-docker-002"></a>
### ACC-DOCKER-002 · 持久化重建验证

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 只使用隔离的验收 Compose 项目、账号和数据卷；已备份，明确不得操作现役容器。

**步骤 / 命令**

1. 在验收数据库和文件卷写入非业务测试标记。
2. 仅重建指定验收容器并复用原有挂载；不删除数据卷。
3. 重新查询标记、记录卷标识与恢复前后结果。

**通过条件**

- 容器被替换后测试数据仍可读取，目录权限正确。
- 测试操作未改变本机现役 nacos、Penpot 或正式环境。

**失败条件**

- 容器替换后数据丢失；误用新空卷；测试触及现役数据。

证据目标：`evidence/acceptance/ACC-DOCKER-002/result.json`。

<a id="acc-data-001"></a>
### ACC-DATA-001 · 数据和外部凭据隔离

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 正式、测试的组件和账号已部署；访问矩阵已登记。

**步骤 / 命令**

1. 核对 MySQL 实例/库/账号、Redis实例、RabbitMQ实例/vhost、Nacos实例/namespace、上传存储位置分别独立。
2. 用各自最小权限账号执行只读查询，确认跨环境账号无权限。
3. 检查测试环境没有真实支付、Broker、短信或邮件外发凭据和待执行生产任务。

**通过条件**

- 实例、凭据、数据和访问控制都隔离；测试不可写正式数据。
- 测试数据如来源生产，已脱敏并清理外发任务/回调地址。

**失败条件**

- 只改库名/namespace但共用高权限账号；测试持有正式外发能力。

证据目标：`evidence/acceptance/ACC-DATA-001/result.json`。

<a id="acc-data-002"></a>
### ACC-DATA-002 · Nacos 配置迁移与发现恢复

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 已授权在目标验收Nacos导入配置；源系统只读导出；namespace清单及敏感配置通过私有渠道保存。

**步骤 / 命令**

1. 单独导出源Nacos配置、namespace和必要账号/权限清单，不只复制logs目录。
2. 在目标恢复配置；正式Nacos外部MySQL方案核对元数据库与账号；测试保持独立。
3. 用验收Java实例核对配置读取、注册发现和有效数据源地址，再重建目标验收Nacos验证持久性。

**通过条件**

- 配置项数量/摘要、namespace对应关系和关键参数核对一致；服务只注册到目标环境。
- 源Derby配置没有因迁移遗漏；日志目录拷贝不被当作配置恢复。

**失败条件**

- 配置丢失、注册旧IP/localhost、目标重建后配置消失、误连正式或旧环境。

证据目标：`evidence/acceptance/ACC-DATA-002/result.json`。

<a id="acc-data-003"></a>
### ACC-DATA-003 · Redis 与 RabbitMQ 的受控恢复和投递

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 隔离验收实例、测试队列和测试账号；恢复/持久化策略已经选定。

**步骤 / 命令**

1. 对Redis写入短期测试键，验证所选持久化策略的预期恢复行为。
2. 对RabbitMQ发布带唯一验收ID的持久化测试消息，按策略重启并消费；模拟一次重投。
3. 核对确认、重试、死信或异常记录，以及消费者幂等处理。

**通过条件**

- 恢复结果与书面持久化策略一致；RabbitMQ测试消息无静默丢失；重复投递不产生重复业务结果。
- Redis缓存与必须持久化状态分别定义，不能把所有Redis键一概要求永久保留。

**失败条件**

- 确认前丢消息却无告警；恢复依赖未登记cookie/nodename；重投产生重复副作用。

证据目标：`evidence/acceptance/ACC-DATA-003/result.json`。

<a id="acc-art-001"></a>
### ACC-ART-001 · Nexus 制品发布、消费和权限

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 目标Nexus已恢复到验收环境；准备专用验收仓库、账号和唯一版本的无业务测试制品。

**步骤 / 命令**

1. 发布专用测试制品，使用消费者只读账号下载并验证SHA-256。
2. 检查构建机能访问，测试发布身份不能写正式发布仓库；发布凭据与运行机分离。
3. 重建验收Nexus后再次下载测试制品，验证仓库数据和配置恢复。

**通过条件**

- 同一版本内容可追溯且摘要一致；权限边界、重启持久化和依赖消费均成立。

**失败条件**

- 只能登录UI却不能发布消费；共用高权限账号；同版本覆盖未受控或制品摘要不一致。

证据目标：`evidence/acceptance/ACC-ART-001/result.json`。

<a id="acc-rel-001"></a>
### ACC-REL-001 · 发布权限、运行身份和回滚边界

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 明确批准的验收应用和运行机；部署用户、sudo白名单、运行用户和目录方案已选定。

**步骤 / 命令**

1. 分别验证 ub 登录、部署账号写制品/管理指定unit的权限、业务普通用户运行权限。
2. 用无业务副作用验收应用执行构建、上传、启动、健康检查、版本标记与回滚。
3. 核对旧发布脚本的User=root、root私有Java路径与模板deploy目录差异已解决；检查测试MCP不能调用正式目标。

**通过条件**

- 登录成功和部署成功分别有证据；应用按批准的普通用户/路径运行。
- 可见版本、健康、制品摘要与发布记录一致；回滚仅说明应用制品，数据库兼容性另验收。

**失败条件**

- 只凭ub登录就认定可发布；root目录对运行用户不可达；脚本成功但应用无健康；测试可发布正式。

证据目标：`evidence/acceptance/ACC-REL-001/result.json`。

<a id="acc-java-001"></a>
### ACC-JAVA-001 · 选定业务链端到端验证

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 上线服务清单和测试数据已确认；使用隔离验收环境和沙箱，真实资金/Broker外发不在本用例范围。

**步骤 / 命令**

1. 选择已批准的用户/认证、BFF、业务服务、数据库/MQ链路，记录请求ID和制品版本。
2. 执行登录与权限、一个读请求和一个可回收的非金融测试写请求，验证最终状态。
3. 检查有效profile、Nacos、数据库、连接池和业务错误日志。

**通过条件**

- 请求到达正确环境并按预期完成；角色权限、持久化和异步最终结果可关联。
- 仅health或注册成功不能替代端到端业务结果。

**失败条件**

- 调用旧地址、环境串线、业务失败被通用成功响应掩盖、出现真实外部副作用。

证据目标：`evidence/acceptance/ACC-JAVA-001/result.json`。

<a id="acc-java-002"></a>
### ACC-JAVA-002 · 多实例 ID 唯一性

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 只对需要共享ID空间的验收写入实例测试；明确Snowflake参数范围和分配表。

**步骤 / 命令**

1. 读取各实例实际生效的dataCenterId/workerId，核对组合唯一。
2. 在隔离ID测试空间按拟上线并发生成记录，核对重复和异常；不要更改宿主时间模拟回拨。
3. 验证模板克隆、重启后分配仍正确。

**通过条件**

- 需共享ID空间的实例不共用默认0/0组合；指定样本中无重复，错误可观测。

**失败条件**

- 只看配置文件未看有效值；重复ID、组合冲突或未定义重启后的身份分配。

证据目标：`evidence/acceptance/ACC-JAVA-002/result.json`。

<a id="acc-java-003"></a>
### ACC-JAVA-003 · 定时任务与 Outbox 并发幂等

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 专用测试记录/消息；目标任务已完成多实例能力审查；禁用真实资金与Broker发送。

**步骤 / 命令**

1. 对拟扩副本的任务在两实例触发同一验收窗口，记录领取、锁、租约与结果。
2. 对同一测试Outbox事件模拟重复投递和一次可恢复失败，验证重试和最终效果。
3. 特别检查MDS定时权重更新等非只读任务，不默认所有定时任务已集群安全。

**通过条件**

- 在声明语义下任务被互斥或幂等处理，最终业务副作用仅出现一次。
- 无法证明集群安全的服务保持单实例并记录限制，不能纳入多副本上线。

**失败条件**

- 重复更新、重复外发、丢失任务或仅凭进程数宣称集群通过。

证据目标：`evidence/acceptance/ACC-JAVA-003/result.json`。

<a id="acc-java-004"></a>
### ACC-JAVA-004 · WebSocket 路由与上传持久化

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 隔离用户和文件；多实例WS模式、节点ID和COMS上传存储方案已确定。

**步骤 / 命令**

1. 建立测试WS会话并记录所在节点，从另一节点触发测试消息，验证送达和重连。
2. 上传唯一小型测试文件，检查链接可读取；在另一实例读取，重建指定验收实例后再次读取。
3. 核对本地 /data/uploads 默认值没有导致多实例分裂或重建丢文件。

**通过条件**

- 分布式模式/节点路由与消息策略吻合，连接恢复和授权正确。
- 文件URL与内容摘要稳定，跨实例和重建后仍可访问。

**失败条件**

- WS只向本地实例投递；共享队列导致部分节点漏推；上传链接可见但内容丢失。

证据目标：`evidence/acceptance/ACC-JAVA-004/result.json`。

<a id="acc-pen-001"></a>
### ACC-PEN-001 · Penpot 镜像架构和配置迁移

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 目标Penpot镜像、部署配置和版本清单已准备；源系统仍保留。

**步骤 / 命令**

1. 检查目标官方核心镜像和本地frontend/worker/import镜像的Architecture为amd64。
2. 核对固定2.18.5基线或经过单独验证的目标版本；确认自定义frontend、resident worker、import、DNS的处理结论。
3. 检查PUBLIC_URI、网络子网、挂载、团队/文件UUID和MCP连接参数；不输出secret值。

**通过条件**

- 目标镜像与T630架构匹配；定制服务功能未因换官方Compose而遗漏。
- 不依赖Mac/OrbStack路径或未确认的DNS环境；升级与迁移是否合并有明确记录。

**失败条件**

- 直接加载仅arm64本地镜像；定制worker/import被遗漏；把上游文件替代本地定制未验证。

证据目标：`evidence/acceptance/ACC-PEN-001/result.json`。

<a id="acc-pen-002"></a>
### ACC-PEN-002 · Penpot 登录与外部访问配置

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 指定测试账号；HTTPS域名和邮件策略已配置。
- 邀请、找回和登录测试仅针对隔离验收账号/测试邮箱；会产生会话或邮件，不属于只读测试。

**步骤 / 命令**

1. 用未登录客户端访问登录页及自定义登录辅助资源，确认没有真实默认邮箱/密码返回。
2. 检查浏览器HTTPS、会话cookie、WebSocket与有效PUBLIC_URI。
3. 通过测试邮箱验证邀请/找回流程；正式使用SMTP，Mailpit仅作为受控测试工具。

**通过条件**

- 不向访问者发送默认凭据；正确账号能登录，未授权访问被拒绝。
- HTTPS和会话可正常使用；邮件按批准的目标送达，测试邮件入口不意外公开。

**失败条件**

- 登录辅助JSON泄露默认凭据；HTTP配置导致会话/剪贴板问题；邮件发往错误对象。

证据目标：`evidence/acceptance/ACC-PEN-002/result.json`。

<a id="acc-pen-003"></a>
### ACC-PEN-003 · Penpot 设计与素材一致性恢复

实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**

方法修订：用户选择应用导出/导入，替代此前整库PostgreSQL/assets恢复。旧要求已归档，源保留，新目标ID映射明确。

**前置条件**

- 用户明确选择改造Git代码与应用导出/导入；Mac源保留；目标使用独立新身份。
- 按活动文件清单导出官方.penpot包，嵌入素材/库关系，包和清单具有SHA及来源时间。

**执行步骤**

- 核对每个源活动文件的官方导出包、源/目标传输SHA和包内文件/库清单；记录软删或未纳入对象。
- 在新目标导入，登记原团队/项目/文件到新ID映射；保留原源文件/UUID与数据，不覆盖Mac源。
- 核对迁入文件页面、形状分型、组件/颜色/字体、媒体内容SHA和目标所有权/访问权限；对专用验收副本检查编辑、导出和再次导入。

**通过条件**

- 活动文件与素材按应用包完整迁入，源/目标结构统计与媒体摘要一致；独立快照之间的库/依赖关系得到明确处理。
- 新目标生成新ID属于本次授权方法，映射完整；源数据/UUID保留，原账号/session/旧MCP身份不被宣称已迁移。
- 专用副本可编辑、导出和重新导入；未纳入的软删数据、账号/历史与导出格式限制明确记录。

**失败条件**

- 包或依赖/媒体不完整，结构或内容摘要不匹配，权限不符或源数据被覆盖。
- 没有记录新ID/账号边界及未迁对象；未完成副本编辑/导出/再次导入却宣称全项通过。

证据：`evidence/acceptance/ACC-PEN-003/result.json`（执行完成后生成）。失败与未执行状态必须如实保留。

<a id="acc-pen-004"></a>
### ACC-PEN-004 · Penpot MCP、worker 与导入任务

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 专用验收设计文件/团队及最小权限MCP账号；导入使用可管理的测试文件。

**步骤 / 命令**

1. 验证worker ready/busy状态，执行一次可撤销的小型设计操作并核对结果。
2. 提交测试导入任务，用同一requestId重试，检查不重复导入和任务状态持久化。
3. 重启指定验收worker/import后检查恢复行为；核对MCP与导入服务鉴权、访问边界和路径。

**通过条件**

- MCP操作反映在正确验收文件，未越权；异步导入可追踪且重试幂等。
- 内部worker/导入接口仅在批准管理通道可访问；凭据无日志泄露。

**失败条件**

- worker健康但实际操作失败；错误团队/文件被修改；请求重试重复导入；鉴权缺失。

证据目标：`evidence/acceptance/ACC-PEN-004/result.json`。

<a id="acc-nas-001"></a>
### ACC-NAS-001 · NAS 磁盘归属与共享容量

阶段：`implementation`；执行类型：`read-only`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- NAS已由OMV官方支持方式安装；PVE存储分配已核准。

**步骤 / 命令**

1. 核对OMV系统盘32GiB和初始2048GiB数据盘，以及数据盘在PVE的独立虚拟磁盘映射。
2. 检查共享目录归属、文件系统容量、配额和PVE store实际余量。
3. 确认没有H730整卡直通、重复挂载sdb，且NAS系统盘不在自身导出的NFS上。

**通过条件**

- 磁盘唯一归属和容量可追溯；用户媒体不会占满所有PVE存储。
- NAS无需额外模板；现有home-cinema-nas文件夹不等于已经部署。

**失败条件**

- 错误物理盘被接管；分配全store；NAS启动依赖自身服务。

证据目标：`evidence/acceptance/ACC-NAS-001/result.json`。

<a id="acc-nas-002"></a>
### ACC-NAS-002 · SMB 家庭账号和文件权限

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 专用验收共享目录与家庭测试账号；不能对真实媒体执行删除测试。

**步骤 / 命令**

1. 用管理账号在专用验收目录创建并保留样本文件，记录文件哈希。
2. 用只读播放账号读取并校验该样本，尝试修改/创建/删除均应拒绝；未认证用户按策略拒绝。
3. 使用另一份独立临时文件验证管理账号重命名与删除能力，保留只读测试样本直到验证结束。
4. 验证 Jellyfin 只读访问媒体目录，家庭照片/文档和游戏目录有独立权限；由管理账号在全部验证结束后清理专用测试文件。

**通过条件**

- 读写能力与账号矩阵一致；拒绝操作有明确结果，不能通过其他共享路径绕过。

**失败条件**

- 匿名可删改内容；Jellyfin被赋予不必要写权限；只读账号可写。

证据目标：`evidence/acceptance/ACC-NAS-002/result.json`。

<a id="acc-nas-003"></a>
### ACC-NAS-003 · Jellyfin 家庭播放与资源控制

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 实际电视/播放器和拥有使用权限的测试片源；媒体扫描与转码限额已确定。

**步骤 / 命令**

1. 播放代表性视频，记录客户端、编码、分辨率、音轨、字幕、码率和播放方式。
2. 在Jellyfin控制台确认Direct Play；再对需转换的样本观察行为和资源限制。
3. 没有证据前不启用或宣称硬件转码；目前未确认适用GPU。

**通过条件**

- 选定直播放片源连续播放无异常缓冲，播放进度与音轨/字幕正常；通过条件对应实际客户端。
- 扫描、缩略图和软件转码受限，超出能力的格式如实记录；4vCPU/4GiB不等于4K多路转码承诺。

**失败条件**

- 只看页面打开；把转码当直播放；Jellyfin耗尽资源或未验证就承诺硬件加速。

证据目标：`evidence/acceptance/ACC-NAS-003/result.json`。

<a id="acc-nas-004"></a>
### ACC-NAS-004 · 游戏文件保存和传输完整性

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 指定可管理的验收样本、源设备和目标设备/工具；只验保存与传输，不涉及主机破解或执行。

**步骤 / 命令**

1. 在源和NAS对同一样本计算SHA-256，Linux用sha256sum，macOS用shasum -a 256。
2. 按实际工具支持的协议从NAS传到目标，再比较摘要及长度。
3. 记录目录结构、权限和实际传输速度，不以SMB共享存在推断主机支持。

**通过条件**

- 源、NAS、目标样本长度和摘要相同；中断后的处理结果明确。
- 结论仅覆盖文件保存传输，不承诺PS4/PS5直接从NAS运行游戏。

**失败条件**

- 摘要不同、文件截断；将NAS文件共享通过等同主机网络运行支持。

证据目标：`evidence/acceptance/ACC-NAS-004/result.json`。

<a id="acc-nas-005"></a>
### ACC-NAS-005 · 家庭负载对正式业务的影响

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 正式业务或等价验收负载的基线与允许阈值已批准；指定维护窗口与停止条件。

**步骤 / 命令**

1. 先记录业务延迟/错误、数据库IO延迟、宿主内存和磁盘余量基线。
2. 逐项叠加一个家庭大文件传输、媒体扫描和实际播放，不同时无界启动。
3. 记录业务和家庭体验指标，验证CPU/IO限额与错峰策略；触发停止条件立即停止验收负载。

**通过条件**

- 所有指标在已批准阈值内，数据无损且无OOM/存储耗尽。
- 尚无业务SLO和基线时保持pending，不编造可用性、吞吐或延迟承诺。

**失败条件**

- 业务指标超阈、OOM、数据库超时，或在没有基线时宣告性能通过。

证据目标：`evidence/acceptance/ACC-NAS-005/result.json`。

<a id="acc-nas-006"></a>
### ACC-NAS-006 · 已有影音配置的有选择迁移

阶段：`implementation`；执行类型：`manual-review`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 已读取home-cinema-nas有效配置及规则；当前任务未授权部署该目录。

**步骤 / 命令**

1. 将旧README中OMV宿主机假设映射为本方案OMV虚拟机；检查Docker挂载路径、用户ID和子网。
2. 当前必选仅Jellyfin；MoviePilot、qBittorrent、WireGuard若采用，需要单独确认用途、网络和额外预算。
3. 对保留配置逐项登记迁移/替换/不采用，禁止直接运行整套旧Compose作为默认验收步骤。
4. 对首期派生的 Jellyfin-only Compose 执行 config --services 等只读核对，并脱敏审查实际启动单元使用的文件列表/命令，确认不会启动未采纳服务。

**通过条件**

- 现有文件仅作配置来源；采用范围、路径和网络符合当前方案。
- 未采纳服务不进入资源预算或完成状态，家用NAS未转变为正式业务备份目标。
- 首期 Compose 有效服务和启动单元只包含获准的 Jellyfin；不能仅替换旧 systemd 示例路径后启动整套服务。

**失败条件**

- 默认部署整套娱乐工具；旧路径/网络直接复制；以文档存在替代运行证据。

证据目标：`evidence/acceptance/ACC-NAS-006/result.json`。

<a id="acc-bak-001"></a>
### ACC-BAK-001 · 独立备份目的地与覆盖范围

阶段：`implementation`；执行类型：`manual-review`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 独立于T630的目的地、访问账号、保留策略与预算已确定。

**步骤 / 命令**

1. 登记正式MySQL及binlog、Nacos配置/元库、Nexus、Penpot数据库/assets、关键配置与虚拟机系统的备份方法。
2. 区分容器卷、挂载文件、外部NFS内容是否被PVE备份覆盖；检查备份加密、权限、摘要与失败告警。
3. 确认家庭NAS和store上的副本只作为同机副本，不是独立灾备。

**通过条件**

- 重要数据有独立故障域内的备份副本，覆盖范围和保留/删除策略明确。
- RAID、PVE快照、容器重建、同机NAS均不被单独认定为备份方案完成。

**失败条件**

- 只有同机副本；凭据不受控；漏备素材/元数据/外部挂载却宣称整机可恢复。

证据目标：`evidence/acceptance/ACC-BAK-001/result.json`。

<a id="acc-bak-002"></a>
### ACC-BAK-002 · 隔离恢复演练与 RPO/RTO 实测

阶段：`implementation`；执行类型：`disruptive-test`；优先级：`P0`；实际状态：**pending / 未执行**。

**前置条件**

- 目标RPO/RTO已批准；独立恢复主机/空间和专用验收数据可用；不覆盖现役实例。

**步骤 / 命令**

1. 从独立备份目的地选一个实际备份批次，在隔离目标恢复数据库、文件和应用。
2. 使用验收数据标记的时间计算可恢复点与故障假定时刻的差值；记录从开始恢复至业务可用的耗时。
3. 验证恢复后的数据摘要、关键查询、文件和权限；记录失败步骤与人工操作。

**通过条件**

- 实测RPO/RTO满足已批准目标；原讨论的RPO≤5分钟、RTO 2～4小时仅为提案，未经批准和演练不能写已达成。
- 恢复目标在独立故障域具备真实资源，恢复后的应用验证完成。

**失败条件**

- 只检查备份文件存在；在原运行卷上测试；无时间证据；数据可读但关键业务不可用。

证据目标：`evidence/acceptance/ACC-BAK-002/result.json`。

<a id="acc-obs-001"></a>
### ACC-OBS-001 · 服务器内监控与Lark告警闭环（本期）

实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**

方法修订：用户明确本期仅服务器内部Lark，Mac外部明确不需要、保持停用并移出当前/后续待办。原要求已归档；不能把机内监控当独立外部监控。

**前置条件**

- 用户已指定并授权Lark自定义机器人，Webhook仅600受保护文件/LoadCredential。
- 本期监控限定T630机内，Mac外部任务已停用且用户明确不需要；不得宣称机内监控能在T630整机故障时通知。
- Ops和各角色既有指标、内网权限与受控通知验收已准备，通知先acceptance-only再开启真实白名单。

**步骤**

- 核对12guest exporter、已激活15角色unit/14本机HTTP及PVE RAID/容量/CF进程指标真实抓取；检查监控配置/规则原生校验与实际加载。
- 安装仅绑定Ops容器网关的认证适配桥，严格TLS/Lark目标、输入/来源/去重/限流，Webhook不得进入argv/env/普通文档日志；原始业务日志/annotation/URL不外发。
- 经真实Alertmanager注入专用验收firing，确认Lark API code0后再resolved，核对两次时间/事件/无秘密回执。
- 维护结束后凭当前boot双阶段proof开启真实告警白名单，核对生效配置/新reload/进程与权限/健康；Mac live与诊断job均不存在。

**通过条件**

- 本期实际指标/目标可用，指定故障与恢复通知经Alertmanager链均被用户指定Lark API成功确认，真实白名单路由已启用。
- 来源与目标/秘密/资源限制符合审查范围，未开启未批准通知通道；同次重试去重且新的故障周期不会被旧缓存吞掉。
- 机内单故障域与Mac明确不需要且保持停用的边界写入交付；独立外部/证书域名/定时备份失败等未实施项目不隐式视为通过。

**失败条件**

- 仅发送函数或HTTP200而无API code0/真实AM闭环；仍acceptance-only却声称真实通知开启；秘密/任意日志外发。
- 未授权外部探针继续运行/误告警未说明，或把机内通知当整机故障外部监控。

**范围排除**

- T630之外Mac持续独立探测已由用户明确不需要，从当前/后续待办移除；不作为待修故障或未来承诺。

**其它延期范围**

- 公网域名/证书有效期监测随未配置域名后续验收。
- 持续独立备份调度及备份失败通知仍在备份后续范围，不由本例代签。

证据记录路径：`evidence/acceptance/ACC-OBS-001/result.json`。

<a id="acc-cut-001"></a>
### ACC-CUT-001 · 切换、限制和最终签收

阶段：`implementation`；执行类型：`manual-review`；优先级：`P0`；实际状态：**passed / 历史证据通过；11/08仅另验基础运行，不代表本例全量重测**。

**前置条件**

- 所有本次上线范围P0用例通过或有明确未上线范围；切换窗口和回退计划已批准。

**步骤 / 命令**

1. 核对源数据保留、目标版本、DNS/Tunnel、发布标记、配置、备份与回退条件。
2. 逐项登记本次实际上线的角色/服务和未上线项；明确单T630整体故障会停机。
3. 由任务管理者审阅证据再签收；数据源和旧环境清理需要另行范围确认。

**通过条件**

- 上线范围、实际证据、限制与遗留项一致；没有pending被隐式视为通过。
- 家庭NAS、Penpot和正式业务分别验收；文档交付完成与部署完成严格分开。

**失败条件**

- 带未核实关键项宣称全部完成；无回退边界；未验收就删除旧数据或切正式流量。

证据目标：`evidence/acceptance/ACC-CUT-001/result.json`。
