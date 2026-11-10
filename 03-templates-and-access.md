# 模板、克隆身份与访问合同

> 2026-11-10阶段更新：用户已恢复Nexus合并与独立221退役，当前状态以[本次交付](completion/20261110-nexus-merge/README.md)、[现行架构](17-publish-artifact-consolidation.md)和[当前交接](11-live-handoff.md)为准。下文是此前基础阶段记录，旧“不合并/221独立/standby”、旧数量和版本不再作为当前现场结论，原验收与未签恢复范围按其时间保留。Java业务不启、旧链fenced；禁止重放历史初始化/迁移器。


更新：2026-11-09。**继续完成基础搭建与正式数据库/Nacos配置自动备份，不迁移数据、不新建克隆或重做现役身份。** [本轮PVE审计](completion/20261109/pve-audit.json)确认14:24自然重启后12来宾自启合同与3停止模板保持；[核心审计](completion/20261109/core-audit.json)再次核严格SSH、fish/Bash和无Java业务。未重新制作/QA模板；UEFI0058是历史事故，用户确认诊断通过与当前计数观察分开记录。状态见[01](01-current-state.md)。

## 1. 最终保留三模板

| VMID | 名称 | 内容与用途 | 不进入模板 |
| --- | --- | --- | --- |
| 9010 | tpl-linux-base | Debian13 AMD64、Cloud-Init、ub/OpenSSH、QGA、时间与基础运维；fish已安装，管理默认Bash | 实例固定IP/hostname、私钥、业务配置/数据 |
| 9001 | tpl-docker-base | Linux基线、Docker29.9.3、Compose5.7.0及日志约定；fish已安装，管理默认Bash | 应用容器/数据、registry或应用凭据 |
| 9011 | tpl-java-acceptance | JDK21.0.13、java非root/nologin、通用验收脚本、安装但masked的node_exporter、fish | Finger/JAR业务、Nacos/DB/Publisher配置和凭据 |

两个核心模板加一份Java验收模板，停止时不持续占用声明内存。NAS不另建模板；CF不制作带token的模板。旧102/103/105/106等和完成的临时QA已按最新清理授权保护备份后删除，不能再列为现役可复用模板。

三核心模板的fish candidate独立QA、受保护VMA恢复替换及最终停放由主AI留证：[模板QA](cleanup/fish/template-QA-summary.json)、[核心替换](cleanup/fish/core-template-replacement.json)。原Java9012完成JDK/唯一身份/DHCP验收后删除；Fish9040..9045全部清理，不保留第四份模板。[Java验收包](network19/java-template/README.md)。

## 2. 模板与应用/角色实例不同

正式与测试共用干净基础镜像，创建独立Full Clone、独立数据盘/账号/网络。数据恢复不在模板中完成；Docker镜像/Compose、Nacos namespace、MQ vhost、数据库、Nexus制品、Penpot设计及NAS媒体在相应实例恢复。Linked Clone依赖原盘链，不替代正式独立备份；已经退出的旧103→104依赖只在历史证据和备份中保留。

Docker模板原存储profile与角色runtime分开：9001保持其overlayfs/live-restore基线，某些数据/离线归档角色使用classic-overlay2。不要为“统一”而在有数据节点直接切driver或删除旧缓存。

## 3. 管理账号与密钥

| 目标/身份 | 登录或运行方式 | 边界 |
| --- | --- | --- |
| PVE21.22 | root，Mac指定私钥 | 宿主写由主AI统一，仅限本轮已批准补齐/清理，不迁移 |
| Linux来宾 | ub，指定公钥由CI注入 | ub是管理身份，不等于业务应用用户 |
| OMV260 | 安装后已验ub/SSH权限 | SMB/Jellyfin账号与管理登录分开 |
| Java验收 | java非root/nologin | 只跑通用临时smoke，无业务服务 |
| 发布220 | 独立publisher身份 | 新发布私钥只在220；业务发布当前fenced |
| 240接收 | 独立deployer/forced-command | 精确受限目标、无通用root shell；不能据历史演练重新激活业务 |

管理员私钥`~/.ssh/yang_local_rsa`只留发起连接的Mac；公钥可经CI注入，凭据值不进Git、模板或普通证据。220发布私钥不得整体备份/导出Mac，CF token及含密钥备份只留PVE；这两条与普通应用备份目的地分别处理。

主机密钥由可信PVE QGA/控制台核对后登记，再strict SSH连接。普通文档/验收只保存指纹，不输出原始公钥/私钥；受控known_hosts按SSH格式保存已核对的服务器公钥。ssh-keyscan只获得候选，不能独立证明身份。不允许StrictHostKeyChecking=no、空known_hosts或在看到错误后自动接受新key。

以下是管理者的只读复核示例，不是本次文档任务执行指令；本轮已由既有strict SSH核验恢复，任何变更另按明确范围：

```bash
dell_root='/Users/yangzhaohui/work/www/harness/dell'
ssh -i "$HOME/.ssh/yang_local_rsa" \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 \
  -o PreferredAuthentications=publickey -o PasswordAuthentication=no \
  -o KbdInteractiveAuthentication=no -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$dell_root/private/known_hosts" \
  root@192.168.21.22 'hostname; id -un; pveversion'
```

来宾建议通过已登记的`scripts/control.py`/可信target info管理，PVE只作SSH跳板和客户端路由，不恢复host转发/NAT。190有双NIC/IP，使用其专用trusted info；同NIC多已批准IP时，只有role明确additional_ips且primary存在、无未知uplink地址才允许，默认管理仍走primary。本轮审计Nexus仍在221，220尚未拥有31；用户明确暂不迁移，不能按合并提案更新信任身份。

## 4. 未来clone必须显式hostname profile（本轮不执行）

generic cicustom user会替代PVE自动生成的user-data，不能保证PVE VM显示名自动成为guest hostname。本次9012首启实际为localhost，之后主AI为该实例注入独立profile显式hostname并正常重启，保住其已生成key后strict SSH/JDK检查通过。

新clone必须在首次启动前：

1. 分配VMID、MAC、地址/网关/DNS，登记PVE二层身份ACL；模板默认server19 DHCP不等于自动获得prod权限。
2. 从通用profile生成每实例user profile，显式hostname与preserve_hostname:false，保留ub/预期SSH公钥及pubkey-only基线。
3. 采用新实例身份重置策略，确认machine-id、hostkeys、CI seed/instance-id没有从制作机复用；CI模块完成且QGA运行。
4. QGA/控制台记录新指纹与VMID/MAC，再strict SSH验证IP/hostname/权限，最后才装角色秘密与应用。

9011镜像ssh_deletekeys:true用于新clone独立身份；190专用false和QA9012已首启后为了保住key的false是**实例级**策略，不可反写通用模板。修改现役CI前要核instance-id与effective userdata，避免网络/hostname变更意外重生hostkeys；也不能为了改hostname重复clean现役machine-id/密钥。

## 5. Java模板验收与实例监控边界

唯一Java模板不含业务；230/240也只有运行基础。[本轮核心审计](completion/20261109/core-audit.json)于11月9日14:42:56–14:43:40确认两台JDK21.0.13可执行、finger账号存在、Java进程0、旧五业务unit not-found/inactive且非enabled，exporter和collector timer正常；未以finger重新执行smoke。模板9011的java身份与masked exporter规则不等于230/240现役实例应停监控。下述脚本以java非root执行临时编译/运行并自动删除源码/class，不启动HTTP、JMX或业务定时器：

```bash
sudo runuser --user java -- /usr/bin/python3 \
  /usr/local/libexec/dell-java-acceptance/verify.py --smoke
```

检查java/javac major21、UID非0、无业务目录/持久Java进程/业务与9100监听、exporter masked以及基础CPU/内存/磁盘。需要监控时按新实例私网IP/角色另行授权后绑定，不在模板默认开放0.0.0.0。

Java业务未来若重新获准，需要单独冻结服务清单、非root运行用户、JVM预算、Nacos/数据源、Snowflake与调度/Outbox/MQ幂等及上传持久化。旧105备注deploy目录与原root发布脚本差异是历史，不是可直接复制的现役发布方案；当前不重新部署JAR或激活发布fence。

## 6. 模板卫生与验收证据

| 对象 | 检查和通过条件 | 当前证据边界 |
| --- | --- | --- |
| hostname/IP/MAC | 与每实例profile、地址及L2登记一致 | 独立克隆是历史验收；本轮恢复核来宾地址/hostname，未新clone或重置身份 |
| machine-id/hostkey/instance-id | clone不同于builder，指纹匹配可信记录 | [Java clone](network19/java-template/clone-evidence.json)、Fish QA |
| 管理公钥 | 仅预期授权，用户可用指定key登录 | 公钥可共享给同一管理者，host私钥必须实例独立 |
| 镜像残留 | 无客户端私钥、业务目录、Nacos/DB/制品/媒体或发布密钥 | 制作/clean与独立clone分别验，不能只看清理命令退出码 |
| Docker | 版本/driver/数据目录约定，无应用容器 | 模板基线与角色数据恢复分开 |
| 监控 | 通用基线或停放；无制作机/角色固定IP与标签 | 新实例登记后才激活采集 |
| fish | 软件已装但root/ub默认Bash | 9来宾+3模板；未chsh，PVE未装 |

通用模板清理使用发行版支持的cloud-init clean选项、machine-id与生成网络清理，再删除制作实例hostkeys/授权/历史。只在专用builder获准清理，清完不先重启再转模板；不对现有数据恢复角色盲删Rabbit/MySQL身份或执行旧clean脚本。

恢复/克隆记录至少含时间、VMID、主机名、MAC/IP、来源模板、OS/版本、登录用户、QGA/CI状态、机器身份hash和公钥指纹、磁盘UUID、结果及限制。本轮不重开模板做新验收，保留[清理与模板结果](18-cleanup-and-consolidation.md)和原始证据。现行自动备份**仅限VM200正式MySQL数据库与完整Nacos外部元数据库**；当前唯一非系统库为`nacos_prod`（12张BASE TABLE、全InnoDB），正式业务schema尚未创建。新增非系统库不在显式白名单即拒绝并告警，需审核更新策略，不能静默漏备。PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600；首轮逻辑SQL gzip **3,301 bytes**已完成CRC/传输SHA校验、DDL锁释放和guest暂存清理，service退出0；03:30（Asia/Shanghai）timer已enabled，下一次2026-11-10 03:30，GFS最近3/每日7/每周4。见[新首轮与timer回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)及[当前中央入口](completion/20261109-prod-db-scope/README.md)。

当前模板、VM系统/镜像与所有非正式DB数据不纳入自动备份；原3模板回退档及旧全机/21档仍保留，不新做模板QA。此前[11档全机首轮成功](completion/20261109/backup-first-success.json)及15:56启用是历史事实，已被用户最新“仅正式数据库/Nacos配置”范围取代；原`dell-local-nightly`不再启用，旧[pve-local实现](infra/backup/pve-local/README.md)退役不可重跑。CF历史档只留PVE，任何旧档/配置均不得因此导出。

不以备份改变clone身份/SSH/JDK和业务禁用边界；仅[该3301B Nacos小档已在VM210临时隔离恢复](completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签。
