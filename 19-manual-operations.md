# Dell T630人工操作手册

更新：2026-11-07，Asia/Shanghai。本手册面向掌握PVE root和来宾ub管理权限的管理员，提供逐项复核流程，**不是一键部署脚本，也不代表以下动作现在正在执行**。当前用户已暂停硬件处理与Nexus合并，改做文档Git交付；未经明确恢复执行，不因看到命令就连接、停服、改盘或启动业务。

Nexus短时维护的知情授权已经满足；当前暂停和硬件安全门禁仍有效。旧“待授权”记录只作历史，不能反复索取同一许可，也不能借旧许可越过新暂停。当前拓扑/预算以[plan.json](plan.json)、入口以[12](12-service-access-and-operations.md)、清理事实以[18](18-cleanup-and-consolidation.md)为准。证据采集后的运行状态会变化，硬件故障后必须fresh核查。

## 1. 先处理硬件门禁

已记录iDRAC多位不可纠正内存错误及correctable rate exceeded指向DIMM_B1；后续控制台显示UEFI0058并停在F1/F2/F10/F11提示。控制台该屏本身没有列插槽，B1来自先前SEL。BMC时区尚未核实，不能据显示时间断言该内存条是物理关机唯一原因，也不能跳过接触、插槽、通道或内存控制器检查。

人工恢复检查点：

1. 先保留iDRAC SEL、Lifecycle、POST截图、B1库存/配置及时间/时区。不要先清日志、反复powercycle或改BIOS来隐藏错误。故障证据见[DIMM事件](cleanup/hardware/DIMM_B1-incident.json)。
2. 用户当前暂停，**不要求立即实施物理动作**。将来明确恢复后，由熟悉T630维护规程的人员正常关机、断开电源并采取ESD措施，再按Dell维护资料做离线检查、重新就位/合适替换及诊断；禁止带电插拔，不在本手册猜测DIMM互换布局。
3. F1可能使机器继续启动，**不等于故障已修复**。在POST/内存诊断、iDRAC日志与稳定性未确认前，不搬数据库、不做高负载构建/大恢复，不仅凭SSH重新可达就继续合并。
4. 硬件稳定后，再核RAID/BBU/磁盘、PVE存储、文件系统、实际bootID及服务。旧RAID“Optl”或旧HTTP200是过去证据，不是故障后的新结论。

## 2. 地址、身份与凭据

以下是最后签收的地址配置；当前能否访问须硬件恢复后验证。PVE21.22不再承担应用NAT或L3转发，应用使用真实19地址。

| 对象 | 地址/入口 | 说明 |
| --- | --- | --- |
| OpenWrt | 192.168.21.1 | 19/24静态路由经21.23；本手册不改OW |
| iDRAC | https://192.168.21.21/ | 电源/硬件日志/虚拟控制台，不提供密码 |
| PVE | https://192.168.21.22:8006/；SSH22 | 只管理/二层桥，forward0、无旧hostNAT |
| 网关VM190 | WAN21.23 / LAN19.1 | 路由、19DNS/DHCP；无NAT |
| CF CT100 | 192.168.19.5 | 原隧道与身份保持 |
| 正式数据200/201 | 19.10 / 19.11 | MySQL / Redis、RabbitMQ、Nacos |
| 测试数据210 | 192.168.19.20 | 独立MySQL、Redis、RabbitMQ、Nacos |
| 发布机220 | 192.168.19.30 | 发布仍fenced，私钥只能留此VM |
| 现役Nexus221 | http://192.168.19.31:8081/ | **尚未合并**，220只有待机材料 |
| Java基础230/240 | 19.40 / 19.45 | 正式/测试各1；没有Java业务进程或自启 |
| Penpot250 | http://192.168.19.50:9001/ | 11服务；目标独立身份 |
| NAS260 | http://192.168.19.60/；:8096；SMB445 | OMV / Jellyfin / media、games、incoming |
| Ops270 | http://192.168.19.70:3000/ | Grafana；Prometheus9090、Alertmanager9093为管理入口 |

19.x表示192.168.19.x，21.x表示192.168.21.x。来宾默认GW/DNS为19.1，由网关向OW21.1解析；发现广播跨子网不是已验功能，电视/播放器手动填19.60。

受信VPN10.66.66.0/24现已允许访问19/24有效IPv4服务，Samba/Jellyfin同步来源识别，**不替代账号权限**。不加SNAT、不把不同WG peer都改成同一/24；参考[16](16-wireguard-access.md)。NAS匿名仍拒绝、reader仍不能写，RemoteAccess/UPnP仍关闭。不要为连接失败修改密码或放开ALL。

凭据只查受控文件位置，见[12凭据表](12-service-access-and-operations.md)。目录700、秘密文件600；不把值贴入文档、终端命令、日志、截图或Git。不要`cat`秘密来调试；不把密码放`-pPASSWORD`、URL或环境变量。旧Mac Penpot连接不自动改成新服务，客户端切换需使用正确目标身份，不能拿源key替代。

### SSH严格连接

在持有用户密钥的管理电脑上执行；先按受信PVE/QGA记录核对host key。**private/known_hosts和私钥不在Git；新电脑clone文档后不能直接获得管理信任。** 必须经已知可信管理员/iDRAC控制台/PVE-QGA核实指纹并受控交接本机known_hosts；ssh-keyscan只能收集候选，不能单独证明可信。不要把私钥或known_hosts当普通文档提交。以下路径是原管理电脑示例，新电脑应使用其已核本机路径；示例只用于**当前仍独立的221**：

```bash
ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes \
  -o ConnectTimeout=8 -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/Users/yangzhaohui/work/www/harness/dell/private/known_hosts \
  root@192.168.21.22

ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes \
  -o ConnectTimeout=8 -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/Users/yangzhaohui/work/www/harness/dell/private/known_hosts \
  -o HostKeyAlias=dell-vm221 ub@192.168.19.31
```

第二条需要管理电脑到19网路由/授权已成立。若需跳板，按[scripts/control.py](scripts/control.py)的严格ProxyCommand和已核`info`使用PVE；不要把客户端私钥复制到PVE/来宾，也不forward agent。host key变化先查物理VM/重装/记录，不用StrictHostKeyChecking=no或盲删known_hosts消警。

## 3. 正常启动与关机

**仅硬件稳定、明确恢复运行后使用。** 先在PVE确认`qm list`、`pct list`、`pvesm status`；模板和退休VM不能混进运行清单。这里给人工顺序，不自动改现役onboot。PVE延时只能排序，不能代替DNS、挂载和应用健康。

最后签收的实际onboot order为：**190(1) → CF100(5) → 200(10) → 201(11) → 210(12) → 270(20) → 221(21) → 250(22) → 220(30) → 230(40) → 240(43) → 260(50)**。不要拿旧startup-order.json里已退役231/232的行重新应用。人工分阶段gate如下，不改变已配置顺序：

1. 网络阶段先190：`qm start 190`。通过控制台/QGA确认WAN21.23、LAN19.1、路由、DNS/DHCP及原防火墙；19网测试节点验证DNS。别因21网直接DNS请求受限而扩大WAN监听。随后按order5恢复CF100（需要时`pct start 100`），保持原身份/配置；它只是网络隧道进程先就绪，不代表后面的origin或公网E2E已通过。已运行对象不为检查重复重启。
2. 数据阶段先200 MySQL，确认原UUID与dell-data-prod-db.service健康，再201、210各栈；每台检查后往下，不能先起依赖Nacos/DB的业务。
3. 其它批准对象按现役次序：270监控、221 Nexus、250 Penpot、220发布基础、230/240空Java基础、260 NAS。逐台核健康/挂载，不启动Java业务。应用就绪后才复核原CF origin；未知account-side配置或缺证据不签公网E2E。

单VM的常规命令分别是`qm status <VMID>`、`qm start <VMID>`；CT用`pct status/start <CTID>`。替换已登记ID逐条执行，不写遍历所有VM的一键循环。

停止按实际顺序反向并先排空客户端写入/真实播放：**260 → 240 → 230 → 220 → 250 → 221 → 270 → 210 → 201 → 200 → CF100 → 190**，最后才正常关闭PVE。需要事先关闭外部流量入口时，可先在明确维护范围停隧道连接，但不能改写已登记顺序或把190提前停掉。Ops尽量保留到应用停止后供观察；对某个VM：

```bash
qm shutdown <已核VMID> --timeout 180
qm status <同一VMID>
```

CT对应`pct shutdown 100 --timeout 60`。以上占位符必须替换，输出必须实际是stopped再进入下一步。超时先检查QGA、unit、写入/播放状态；不要直接`qm stop`强断数据库，也不要一口气停网关后再想通过19网管理。整机恢复/断电灾备没有因此自动通过。

## 4. 应用日常检查与受控启停

Docker只放应用来宾，**禁止在PVE宿主安装或运行应用Docker**。进入正确来宾后先核hostname、IP、mount UUID，再检查：

```bash
hostname
ip -br address
systemctl --failed --no-pager
findmnt --json --mountpoint <该角色挂载点> --output TARGET,SOURCE,FSTYPE,UUID
```

| 来宾 | 原应用监督单元 | 数据挂载 |
| --- | --- | --- |
| 200 | dell-data-prod-db.service | /srv/dell-data |
| 201 | dell-data-prod-infra.service | /srv/dell-data |
| 210 | dell-data-test-data.service | /srv/dell-data |
| 221（当前） | dell-nexus.service | /srv/nexus，UUID239dc45a-b1f3-408b-a8ef-7afa77b52204 |
| 250 | dell-penpot.service，Type=notify | /srv/penpot，UUIDccccda03-bffd-4054-afd3-e0e22f0c607e |
| 260 | dell-nas-jellyfin.service；OMV/SMB由OMV管理 | /srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a |
| 270 | dell-ops.service；另有dell-lark-notify.service | /srv/dell-data |

data角色各自UUID以plan和现役assignment为准，不按sda/sdb猜。挂载缺失、UUID不符或目录落在根盘时停止，不创建同名空目录假修复，不裸起Compose。应用容器restart=no由原unit统一拥有；不要将Docker模板的overlayfs/live-restore配置直接套到应用VM，NAS的原后端与其它角色也不同，不能有数据后切换后端。

日常只读状态用：

```bash
systemctl show <该角色原unit> --property=Type,ActiveState,SubState,Restart,RequiresMountsFor,BindsTo
sudo docker --host unix:///var/run/docker.sock inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' <已核容器名>
```

不请求完整Env/Cmd/health日志来取密码。需要停/启某应用时，先记录影响、无写入/播放与回退检查点，再分别`sudo systemctl stop/start <原unit>`；重启也是维护动作，不是通用探测。磁盘/Docker故障恢复后由管理员先核正确挂载，再按原unit显式恢复，不能以reset-failed掩盖原因。

NAS更改用官方OMV模型/界面，不能裸改生成的Samba/fstab文件后与Salt互相覆盖。SMB实际来源过滤在各share，不能只查global；当前21/19/127+VPN10允许，users/readlist/writelist/guest仍受控。Jellyfin配置重启前须检查实际播放/转码，不能强杀真实流。

Ops为机内监控；整台T630失效时可能连告警也失效。Mac外部探针按用户决定停用，不能重新加载其LaunchAgent来假装已修复独立告警。维护静默只在明确范围使用，健康与零真实告警后解除本次项，不清其它管理员的静默。

## 5. 模板克隆与验收

保留模板只有9010 Linux、9001 Docker、9011 Java验收，均停止封存；NAS没有专用模板。9011含JDK21、非root java和通用验收脚本，不含业务JAR/配置/凭据；exporter只安装且masked。Java业务仍未获当前部署范围，克隆模板不等于上线业务。

人工检查点：

1. 选择未占用VMID，登记角色、资源、存储、19地址及新MAC/IP ACL；核模板磁盘backing依赖。不能直接复用旧QA9012或其它已删对象的脚本假设。
2. PVE执行明确全克隆，示意命令中的占位符须先审核：

```bash
qm clone <9010或9001或9011> <新VMID> --full 1 --name <唯一实例名> --storage <已批准存储>
```

3. 首次启动前从通用Cloud-Init user profile派生该实例专用profile，保留ub/公钥认证基线、显式hostname和preserve_hostname=false；分配正确IP/GW/DNS。只传公钥，不传客户端私钥。PVE显示名**不保证**custom user-data里的guest hostname；不能用只写两行的残缺profile覆盖users/key。
4. first-clone保留独立machine-id/hostkey生成；不要把过去已启动QA为保key用的ssh_deletekeys=false抄到新模板。已有实例改hostname不重新clean machine-id/hostkeys。
5. 启动后经QGA可信链记录公钥指纹，再strict SSH核IP/MAC/hostname/Cloud-Init完成、NTP、独立machine-id/hostkey；Docker还核独立engine ID，按角色评审存储profile。无身份重复、无残留源应用/秘密才通过。
6. 9011的实际通用验收命令只在新clone里执行：

```bash
sudo runuser --user java -- /usr/bin/python3 /usr/local/libexec/dell-java-acceptance/verify.py --smoke
```

通过仅表示JDK非root临时编译/运行等基础检查，不启动服务。9100须按新角色另行绑定/授权，不默认0.0.0.0。参考[Java模板实际说明](network19/java-template/README.md)；不要在现役VM运行clean.py。

## 6. 备份与隔离恢复

清理前已保留21份受保护PVE归档，目录`/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/`，root0700，归档/日志0600；压缩约29.9GiB。这是同一物理机/存储内的回退档，**不是异机灾备**。SHA/zstd/VMA全档完整性通过，不表示每份旧实例都恢复开机验过，见[备份汇总](cleanup/backup-summary.json)。

不可跨越：CF归档仅PVE，不导出Mac；publisher私钥仅220，禁止wholebackup/snapshot220来夹带复制它。普通应用初始副本与恢复证据有范围限制：Rabbit definitions不含消息、Redis初始快照0keys、Grafana备份不等于Prometheus/Alertmanager全部历史，NAS媒体不是正式业务备份目标。长期独立目的地/自动调度/保留与真实RPO/RTO尚未签收。

每次备份先登记对象、版本、身份边界、目标、容量、加密/权限及一致性条件。数据库/Blob一起取一致性点，正在运行的目录拷贝不能冒称一致备份。原10.63门禁的历史application-backup脚本必须先核适配现役19配置，不能从旧README直接抄--execute命令。秘密通过受控文件/STDIN使用，不把整个private打包上传Nexus。

隔离恢复人工流程：

1. 硬件稳定后选择明确归档，与受信记录对SHA，并做`zstd --test <归档>`。需要VMA全档核验时在**PVE root700临时目录**解压、文件600，预留足够原始空间，再`vma verify <原始VMA>`；不要解压含秘密整机档到Mac或公共目录。
2. 分配新的恢复QA VMID和预算，确认不会覆盖保留VM/卷。PVE恢复示意：

```bash
qmrestore <已核归档路径> <新QA_VMID> --storage <批准存储> --unique 1
```

3. **首次启动前断开QA网卡或放入已审隔离网络**，保留唯一MAC/身份规划，禁止与原实例同IP/同服务同时写同盘。恢复档可能带原固定地址与秘密，unique MAC不自动消除所有身份/地址冲突。
4. 在QA核OS/UUID/实际应用/账号权限与原数据SHA，再做需要的业务只读校验；数据库不可只看容器running。记录步骤/时间/失败/限制，才决定是否切换。未验恢复不宣称RPO/RTO。
5. 回滚指针/JAR不回滚SQL、Nacos或新用户数据；恢复测试禁止直接覆盖现役数据。QA清理由准确VMID/卷manifest与依赖检查决定，不按目录或base-*通配删除。

## 7. Nexus手动合并：授权已满足，当前硬件暂停

名称与归属以[17合并架构](17-publish-artifact-consolidation.md)为准：最终只保留VM220 `publish-service`，发布与Nexus是该VM的两项职责，31是服务alias；原VM221 `artifact-service`核验后退役。合并验收后须重新核启停清单并移除221，不能继续按旧双机清单启动两个31所有者。

目标已选：220管理primary19.30，Nexus服务alias19.31:8081，OS hostname继续publish-service；220计划6CPU/8GiB，原100GiB数据卷/srv/nexus UUID239dc…保留。服务URL/新账号/EULA/原数据保持；不是新建空仓库。当前仅Docker/两镜像/13项root600 standby准备完成，**221仍是配置归属，220未装active Nexus、未绑定31或迁盘**，故障后的可用性需重新查。

### A. 恢复与fresh基线

- 用户知情短停许可已有，当前暂停必须先明确恢复；管理员核硬件、可信管理、存储稳定，再安排具体窗口。不要反复问已满足许可，也不要省略人工检查点。
- 只读fresh核221/220实际OS、MAC/IP、bootID、unit、两imageIDs、原UUID和数据树。核target Dockerclassic、0容器及原standby nonce `cb01b8582f544381b0461001dfa3ccb4`。
- 对13项standby与source现役code/env/三身份做私有hash比较，只有公开IP/hostname/image差异可输出；秘密值或其hash不进普通终端/Git。发布key只stat，不读/传。
- 仓库原基线49GAV/234主SHA、35metadata语义/1076checksum可能随新合法数据漂移。应冻结当前全量及原数据子集，不删回49凑通过。source只读GET基线驱动**尚未落地**，必须先准备审核；现有verify220.py是target激活后的GET-only验证器，不是source停服脚本。

### B. 原unit停止、冷备、唯一数据盘交接（PVE root人工执行）

`cleanup/nexus/quiesce221.py`不存在，先前整条创建/执行被审批拦在CreateProcess前。不要编造“已完成source quiesce”。基线准备审过后，在**VM221**正常停止：

```bash
sudo systemctl stop dell-nexus.service
sudo systemctl show dell-nexus.service --property=ActiveState,SubState
sudo docker --host unix:///var/run/docker.sock inspect --format '{{.Name}} {{.State.Running}}' nexus-nexus-1 nexus-gateway-1
```

应inactive/dead、两running=false。无数据删除/初始化；必要最小配置/凭据fresh传输应在OS尚能管理时完成，同owner strictSSH内存管道落220root700/600，不能用whole220备份或拷hostkeys替代。

随后PVE root：正常`qm shutdown 221 --timeout 180`，核stopped；对已停止221做受保护完整`vzdump 221 --mode stop --compress zstd --dumpdir <PVE_root700目录>`，完成SHA/zstd/VMA校验，再核它仍off。先关机再stop模式备份避免备份后自动恢复原运行状态；备份不是靠在线拷H2目录凑数。允许221档含本实例Nexus凭据，仅PVE600，不exportMac。

source冷备/停止确认后，正常停220，保留两台scsi0。先读PVE实际磁盘与当前slot/依赖，只列非敏感字段，例如`qm config 221 | rg '^(name|scsi[0-9]+|net0|cores|memory):'`。root已核本机Qemu.pm的确切迁移语义：

```bash
qm set 220 --cores 6 --memory 8192
qm move-disk 221 scsi1 --target-vmid 220 --target-disk scsi2
```

**不传store/storage**；该target-vmid分支会rename卷匹配新owner、从source配置移除并挂到target，**不是保留源拷贝**。确认source无该盘、target scsi2正是原卷/UUID，不能同盘并挂RW。此命令仅在检查证明当前slot仍一致后使用。

### C. 双IP、ACL与管理checkpoint

只有source221 off并退31所有权后，root在220同MACbc:24:11:2a:01:ad上保留30/24并加31/24，默认路由/DNS19.1，实际去19.45的source/prefsrc必须30。先`networkctl status`核实际NetworkFile；旧阶段曾是`/etc/systemd/network/00-dell-server19.network`，不能未经读取就覆盖。双Address的networkd/CI持久配置与PVE bridge MAC/IP集合变更必须事先准备差异、原生校验、控制台/回退；当前没有可直接复用的一键双IP迁移器。

同步把31的L2归属从221MAC移到220MAC，保留业务role矩阵、VPN10范围与发布forced-from30/fenced策略。现有`network19/guest-network.py apply`是单IP设计，会断言/删除额外地址，**不能抄它或旧10.63初始化器来设置双IP**。

管理仍用220/30及其自身hostkey，不能用dell-vm221信任别名连新220，也不能复制221hostkeys伪装旧机器。scripts/control.py在本地**已实现additional_ips严格同NIC白名单支持**，不会替管理员配置alias。将来硬件稳定并恢复任务后，先按唯一角色所有权更新plan：220的ip仍为19.30、additional_ips声明19.31，同时221不能继续作为active角色claim31；然后fresh核实际地址、同一NIC及受信hostkey。未知/未声明地址、重复IP或跨NIC仍拒绝，SSH管理固定primary19.30，不关闭strict检查。

### D. 原盘挂载、候选提交、启动与验证

上述root检查点全部有新证据后，才在220调用已存在target执行器；先核远端工具SHA，本地target.py已有尚未同步的source30路由guard，需root评审后精确CAS，不盲覆盖。原候选nonce已prepared，不能重复stage。

```bash
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py mount --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py commit --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py start --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
```

这些命令会真实写/启服务，**现在暂停，不执行**。mount只用已存在UUID、非根盘、原UID/GID200与非空db/blobs，不format。commit只改hostname合同和两image引用，其余env/身份不变，不fresh-init/EULA/上传；start原unit有限等2healthy。fstab已写但mount失败、commit部分路径留下或unit已active而journal未收尾时，先读状态/私有journal和manifest，停止一键重跑；不删整目录强行通过guard。

实际healthy后用[verify220.py](cleanup/nexus/verify220.py)的GET-only检查原/新鲜GAV与SHA、EULA、用户角色、group、匿名401/403和publisher非docker组/socket拒绝。原key只能220，source30/target45/受限命令和fenced不变，不执行Java业务发布。

监控必须单独配套：当前10node+5=15；合并并确认221退役后才9node+5=14。保留220 role/primary30，增加Nexusunit和本机31HTTP；31不再假造第二node，221SD/物理role退役。以最新ten-role配对SHA为基线，不抄旧12→9 manifest。最后从LAN/VPN复测原URI31，原数据/身份/metrics通过后才退役221；OS盘和冷备不立即删。

### E. 原盘回退

任何身份/UUID/内容/权限差异先停手。root停止220 Nexus、撤31服务alias，正常停220并核无writer，按新鲜slot反向把**原盘**从220 scsi2移回221 scsi1：

```bash
qm move-disk 220 scsi2 --target-vmid 221 --target-disk scsi1
```

先确认221该slot空、盘唯一所有权和原备份在，恢复source原网络/31归属/管理与原监督后再启动；target220保留primary30和发布key，不从旧空库重导或清真实数据。旧桥或ACL若已改也需root配套恢复，文件回滚不等于网络回滚。回退没有实演，不签成恢复保证。

## 8. 失败时停手与禁止重跑清单

| 观察 | 人工下一步 |
| --- | --- |
| UEFI0058/B1不可纠正或硬件不稳定 | 保留日志、维持暂停；合格人员离线诊断，不按F1签修复 |
| SSH key/hostname/MAC/IP或UUID与登记不符 | 停止写操作，通过PVE/QGA/配置核身份，不能关strict或改预期值蒙混 |
| 无挂载、根盘替代、空间不足 | 不启动写服务；查真实盘和容量，不能mkdir空数据目录 |
| 备份未验证/依赖关系不清 | 不删、不移、不覆盖；重新确认准确VMID/卷/DAG |
| baseline合法新增/私有hash漂移 | 冻结现状并审差异，不删数据凑旧数量、不输出秘密 |
| stage/commit中断或模型/RPC参数不符 | 读journal和当前文件，准备最小审核恢复；不换工具绕失败guard |
| 播放/写入仍在、无法干净停止 | 协调维护窗口/排空；不强杀真实流或数据库 |

以下不是日常修复命令，禁止在现役环境全量重跑：

- 旧`infra/provision_network.py`、宿主旧四桥/hostNAT初始化与旧10.63 firewall/bootstrap；现拓扑是190+vmbr19，不能复活旧转发。
- `network19/guest-network.py apply`用于已完成的单IP迁移，不用于220双IP。
- `infra/bootstrap-guest-storage.py`等建盘/格式化初装流程；禁止对保留卷做mkfs/wipefs、通配lvremove或删/srv。
- `infra/nas/install-omv.sh`、旧same-IP `adopt-omv-network.sh`及omv populate初装路线；不能覆盖现役OMV网络/SSH/共享配置。
- Penpot `fresh-target.py init`、历史source凭据复制/PG全库覆盖流程；当前保留Git改造、新身份和既有数据，不重新初始化。
- Nexus `fresh-instance.py`、`bootstrap-new.py`、`accept-eula.py`不用于同实例合并恢复；不重置账号、EULA、repo或导入旧H2。
- Docker `down -v`、volume rm、prune --volumes，或整机/模板目录通配删除；运行中数据不是可清缓存。
- Java模板clean.py、cloud-init clean/machine-id/hostkey删除只用于明确fresh builder，不能“修复”现役VM。
- 已完成的旧15对象/QA删除脚本、旧候选30测试版publisher部署器；不能重复删ID或把未部署候选覆盖现役。
- Mac外部探针LaunchAgent和自动恢复发送；其停用是用户明确范围，不因本手册存在重启。

所有复杂变更先形成具体对象、影响、前置、差异、验证与回退，按已满足的授权范围执行；新业务/删除/外部身份或未涵盖风险另行明确。普通文档检查只运行本地`python3 scripts/validate_docs.py`，不代表远程健康或硬件已修复。
