# Dell T630人工操作手册

> Nexus最新范围（2026-11-10）：用户已明确恢复合并与独立221退役；切换及221退役已完成，最终回执见[本次交付](completion/20261110-nexus-merge/README.md)。旧暂缓措辞与双机启停只留历史，禁止重放旧迁移命令；日常维护按[本次操作手册](completion/20261110-nexus-merge/usage-manual.md)。Java业务不启、旧链fenced、MCP私有设置保持。


更新：2026-11-10，Asia/Shanghai。本手册面向掌握PVE root和来宾ub管理权限的管理员，提供逐项复核流程，**不是一键部署脚本，也不代表以下动作现在正在执行**。用户已确认内存处理/诊断通过；本轮继续完成基础搭建并最新仅选择正式数据库/Nacos配置自动备份，仅测试Nacos配置迁移按用户新授权完成，仅Puyu两库业务数据按随后新授权迁210，正式不动；Nexus随后已获明确恢复合并授权。现行正式DB/Nacos逻辑首轮3301B成功、service退出0，03:30 timer已启用；旧11来宾全机jobdisabled且旧档保留；当日状态入口为[11月9日交付记录](completion/20261109-prod-db-scope/README.md)。下文复杂合并/恢复命令仅保留人工参考，不因服务器可达就停服、改盘或启动业务。

历史Nexus短时维护许可及11月8日暂缓均保留；11月10日用户明确恢复执行，当前以本次合并回执为准，不重复索取已满足许可。当前拓扑/预算以[plan.json](plan.json)、入口以[12](12-service-access-and-operations.md)、清理事实以[18](18-cleanup-and-consolidation.md)为准。证据采集后的运行状态会变化，硬件故障后必须fresh核查。

## Penpot DNS周期故障：修复与70分钟观察通过

14:31只读证据先见DNS unhealthy，连续3bad后原监督策略停11；原DNS无init回收BusyBox timeout孤儿，积累84僵尸并接近PID128上限。本次只DNSinit:true＋lock/runtime严格门禁、安全可选Init扫描与boundedroot600诊断ledger，原镜像/阈值/资源/密码/设计不改。第一候选native字段模板失败被guard拒绝并回退恢复11healthy，第二版safeindex修正后成功，不将失败称误报。

[38项测试](completion/20261111-penpot-hourly/candidate/offline-verification.json)、[原生140探针](completion/20261111-penpot-hourly/native-burst.json)与[8file/1661媒体保护](completion/20261111-penpot-hourly/postcheck-result.json)通过，只DNSrecreate/其余10ID保持、15PromtargetsUP。70分钟只读观察已完成4200秒/119采样，全11healthy/0僵尸/NRestarts0保持，PID范围8–14/128首尾8；日常检查/故障留证见[本次手册](completion/20261111-penpot-hourly/usage-manual.md)。Git8a/clean、原UI/身份/凭据/MCP保持，不重放apply/fresh-init，不放宽健康/PID或删除日志。

## Penpot：原UI默认填入（新明确授权）

用户要求保持原登录UI、不新增逻辑，并[明确授权](evidence/penpot-login-prefill-20261110/explicit-approval.json)让LAN21/24、WG10.66.66/24、VM250自身19.50与loopback的未登录访客可读取原`owner@dell.local`密码并默认填入。原helper/表单结构不改，无新checkbox/forget/localStorage；打开[Penpot](http://192.168.19.50:9001/)、刷新后由原helper填原账号密码，点击原“继续/登录”，不自动提交。CF19.5与其它来源拒绝；这项用户已知授权的密码读取范围不应描述为只保存本人浏览器。

原密码与owner/MCP/设计保持，值仅Mac `private/credentials/penpot-owner-20261110.json`、guest `/etc/penpot/new-identities.json`及guest0600运行JSON，不进文档/Git。此前个人浏览器remember控件/逻辑已[撤回并恢复原UI](evidence/penpot-browser-remember-20261110/restored-original.json)，该目录仅历史。[16:13应用](evidence/penpot-login-prefill-20261110/approved-applied.json)、[16:19原生后检](evidence/penpot-login-prefill-20261110/native-postcheck.json)及[真实LAN浏览器](evidence/penpot-login-prefill-20261110/browser-acceptance.json)已通过：11healthy、四种未授权Docker来源/伪造头均403、原表单账号密码匹配/密码masked，点击原Continue进入已认证dashboard；无新增控件与remember挂载，测试cookies/localStorage已清且session关闭。当前WG/CF端到端未签；core ff1783e clean/镜像保持，不取Git新码，用户push两改造后再更新的独立门禁继续。详见[新证据](evidence/penpot-login-prefill-20261110/README.md)与[使用手册](evidence/penpot-login-prefill-20261110/usage-manual.md)。

## 免登录服务导航（VM220新增）

当前入口 **[服务导航](http://192.168.19.30:9080/)**，无需账号密码，TLS/登录凭据均不加载。顶部“个人内网 / 服务导航”栏已移除，标题和外侧留白缩紧，保持全宽布局。此前14个入口可分组、搜索、环境筛选、刷新、复制及新标签页打开；本轮本地清单已移除FileBrowser变为13项，运行切换由本次维护窗口补签；目标由客户端直接访问并使用各自认证，导航不提供SSO或健康探测。自建内网应用默认HTTP；FileBrowser现已退休，仅保留NFS；PVE/iDRAC内置HTTPS保留。

此前 `bkcode/deploy/service-directory/` 提交为 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`，历史[统一内网HTTP交付](evidence/internal-http-20261110/README.md)、[导航链接应用](evidence/internal-http-20261110/navigation-links-applied.json)与[14:28最终后检](evidence/internal-http-20261110/final-postcheck.json)通过：导航HTTP14条、自身及FileBrowser链接HTTP、无顶部栏、unit只读active；16targets、资源六服务及FileBrowser HTTP指标UP。`ddccc2b`是[此前全宽布局验证阶段](evidence/service-directory-http-20261110/README.md)，`63b8c08`与旧TLS指纹为[首次HTTPS历史](evidence/service-directory-20261110/README.md)。4条任务源码提交均只在本机未push，原4条用户提交未捎带发布。维护走审查后的精确提交→新release→只重启导航；不调用业务发布链，不启动Java、不因导航维护操作Nexus、不替用户push或更新Penpot。[使用手册](evidence/service-directory-20261110/usage-manual.md)。

## 资源访问：仅NFS，FileBrowser已停用

用户明确确认仅保留NFS。VM280的`dell-filebrowser.service`与`dell-filebrowser-firewall.service`已inactive/masked并取消自启；TCP/UDP8080无监听，专属`inet dell_filebrowser_input`表已撤。原账号/JWT/state与受保护回退材料保留，不提供现役网页登录，也不扩NFS来源或修改密码。

NFS仍为`192.168.19.80:/`→230/240的`/mnt/resources`；NFS配置、exports、版本、原输入表和服务PID/启动身份保持，健康仅原5项资源服务，已移除FileBrowser service/HTTP检查。本轮两client以finger读回唯一server canary且已清理，未写client或读业务文件。当前[停用/验证](completion/20261110-nfs-only/README.md)、[后检](completion/20261110-nfs-only/final-postcheck.json)及[使用手册](completion/20261110-nfs-only/usage-manual.md)为准；[旧FileBrowser HTTPS](completion/20261110-filebrowser/README.md)和[HTTP交付](evidence/internal-http-20261110/README.md)仅保留历史。导航运行与VM270最终Prometheus证明由本次统一维护窗口补签。

## 统一资源服务（新增VM280）

用户选择正式/测试共用VM280 `resource-service`（19.80）的同一目录。独立100GiB ext4盘挂`/srv/resources`，系统盘保32GiB；两running 230/240目标挂载均为`/mnt/resources`，240原`/mnt/dell-artifacts`不动。NFSv4.1-only/TCP2049/fsid0，只有19.40/19.45获export与bridge/专属输入许可；root_squash、sync、server根2770/defaultACL、共享resources附属组2980。finger原UID999/GID989保留。

[server启动](completion/20261109-resources/server-installed.json)与[实际盘UUID](completion/20261109-resources/storage-initialized.json)已留证；两客户端真NFS挂载/guard、非root跨机创建/读写/删除、root_squash与240缺挂载根盘写入负测均已通过；仅VM280受控重启约30秒，fsync canary持久、两客户端挂载恢复，未重启两台running。**当前仅保留NFS，FileBrowser网页服务已退休/8080关闭；不提供业务图片URL、不启Java、不迁文件、不扩自动备份。** 资源初建时角色使预算变为13来宾（12VM＋CF LXC）、3模板、45vCPU/87GiB；保守125GiB预算余38GiB。历史[00:20最终只读后检](completion/20261109-resources/final-postcheck.json)当时确认13来宾运行、3模板停止、16/16 targets UP、资源5项服务指标UP与PVE全forward0。详见[280机器目录](machines/vm280-resource-service/README.md)与[当前NFS使用手册](completion/20261110-nfs-only/usage-manual.md)。

模板仅能将来预装客户端与disabled挂载候选，clone按真实IP/组/exports/bridge登记后显式激活；**本次没有修改三模板**。

[独立native验收](completion/20261109-resources/native-acceptance.json)与[仅280重启](completion/20261109-resources/reboot-exercise.json)覆盖本次专属fixture，不含真实业务或文件恢复。findmnt允许systemd-1 autofs加唯一真实nfs4的合法stack，可用`-t nfs4`辨识；单独autofs仍不算共享已挂载。客户端文件创建明确用umask0002；首轮失败及清理记录保留，随后仅按已批准UMask重跑fixture，未修改服务来追过。新增280 fish4.0.2、root/ub默认Bash已后检；当前10台guest＋3模板具备fish基线。

应用尚未接入：Finger的`file.upload.path=/mnt/resources`仅建议，未改实际配置/Nacos/profile；业务HTTP domain/公开图片URL未搭。Puyu现有images在MySQL内通过权限接口下载，NFS不会自动迁出，也未随部署改Java或应用连接。


## 1. 硬件历史、当前恢复与复发门禁

已记录iDRAC多位不可纠正内存错误及correctable rate exceeded指向DIMM_B1；后续控制台显示UEFI0058并停在F1/F2/F10/F11提示。控制台该屏本身没有列插槽，B1来自先前SEL。BMC时区尚未核实，不能据显示时间断言该内存条是物理关机唯一原因，也不能跳过接触、插槽、通道或内存控制器检查。

11月8日用户确认已重插/更换并诊断通过，首次恢复采样EDAC0/RAIDOptl、12running/15UP/6HTTP200；11月9日14:24自然重启后[新PVE审计](completion/20261109/pve-audit.json)再次核EDAC0/RAIDOptl和guard持久，原服务按[当日记录](completion/20261109-prod-db-scope/README.md)fresh复验。这些都不代表单凭计数0已独立确诊原故障。SEL/UEFI0058历史继续保留。以后故障复发时按下列检查点处理：

1. 先保留iDRAC SEL、Lifecycle、POST截图、B1库存/配置及时间/时区。不要先清日志、反复powercycle或改BIOS来隐藏错误。故障证据见[DIMM事件](cleanup/hardware/DIMM_B1-incident.json)。
2. 当前不要求重复物理操作。若将来故障复发并明确安排物理维护，由熟悉T630维护规程的人员正常关机、断开电源并采取ESD措施，再按Dell维护资料做离线检查、重新就位/合适替换及诊断；禁止带电插拔，不在本手册猜测DIMM互换布局。
3. F1可能使机器继续启动，**不等于故障已修复**。在POST/内存诊断、iDRAC日志与稳定性未确认前，不搬数据库、不做高负载构建/大恢复，不仅凭SSH重新可达就继续合并。
4. 硬件稳定后，再核RAID/BBU/磁盘、PVE存储、文件系统、实际bootID及服务。旧RAID“Optl”或旧HTTP200是过去证据，不是故障后的新结论。

## 2. 地址、身份与凭据

以下地址在11月9日fresh核查中保持，实时可用性仍以操作当时检查为准。PVE21.22不再承担应用NAT或L3转发，应用使用真实19地址。

| 对象 | 地址/入口 | 说明 |
| --- | --- | --- |
| OpenWrt | 192.168.21.1 | 19/24静态路由经21.23；本手册不改OW |
| iDRAC | https://192.168.21.21/ | 电源/硬件日志/虚拟控制台，不提供密码 |
| PVE | https://192.168.21.22:8006/；SSH22 | 只管理/二层桥，forward0、无旧hostNAT |
| 网关VM190 | WAN21.23 / LAN19.1 | 路由、19DNS/DHCP；无NAT |
| CF CT100 | 192.168.19.5 | 原隧道与身份保持 |
| 正式数据200/201 | 19.10 / 19.11 | MySQL / Redis、RabbitMQ、Nacos |
| 测试数据210 | 192.168.19.20 | 独立MySQL、Redis、RabbitMQ、Nacos |
| 发布机220 | http://192.168.19.30:9080/ | 免登录只读导航；业务发布仍fenced，私钥只能留此VM |
| Nexus（220承接） | http://192.168.19.31:8081/ | 同NIC服务alias31，原身份保持；最终签收见本次回执 |
| Java基础230/240 | 19.40 / 19.45 | 正式/测试各1；没有Java业务进程或自启 |
| Penpot250 | http://192.168.19.50:9001/ | 11服务；目标独立身份 |
| NAS260 | http://192.168.19.60/；:8096；SMB445 | OMV / Jellyfin / media、games、incoming |
| Ops270 | http://192.168.19.70:3000/ | Grafana；Prometheus9090、Alertmanager9093为管理入口 |

19.x表示192.168.19.x，21.x表示192.168.21.x。来宾默认GW/DNS为19.1，由网关向OW21.1解析；发现广播跨子网不是已验功能，电视/播放器手动填19.60。

受信VPN10.66.66.0/24现已允许访问19/24有效IPv4服务，Samba/Jellyfin同步来源识别，**不替代账号权限**。不加SNAT、不把不同WG peer都改成同一/24；参考[16](16-wireguard-access.md)。NAS匿名仍拒绝、reader仍不能写，RemoteAccess/UPnP仍关闭。不要为连接失败修改密码或放开ALL。

凭据只查受控文件位置，见[12凭据表](12-service-access-and-operations.md)。目录700、秘密文件600；不把值贴入文档、终端命令、日志、截图或Git。不要`cat`秘密来调试；不把密码放`-pPASSWORD`、URL或环境变量。旧Mac Penpot连接不自动改成新服务，客户端切换需使用正确目标身份，不能拿源key替代。

### 测试Nacos配置的当前使用范围

入口`http://192.168.19.20:8848/nacos/`。现有admin可管理导入域：finger-cloud-dev `08e7191f-3ccd-411a-be00-56798d237533` 32项、finger-trascan `7bfe03c6-0590-4ff0-8def-e07015016b54` 4项，共36，当前均DEFAULT_GROUP，35yaml/1text。旧finger-test `10719261-2641-590a-b821-c8484ca955ac`、finger-test-empty `23836f2e-9553-5948-84cd-431b2f241bd6`和public配置均0。[applied](completion/20261109-nacos-config-import/applied.json)/[verified](completion/20261109-nacos-config-import/verified.json)为当前证明；20:27旧7项仍保留的[空域创建记录](completion/20261109-test-env/empty-namespace-created.json)仅按当时解释。

应用`finger_test`原role只允许旧finger-test和finger-test-empty，没有grant两导入域；不能把应用账号403当网络故障、改密码或自动提权。未来业务接入另行明确namespace/权限；基础.env/health仍可指旧域保兼容。本期最新用户配置迁移授权覆盖先前只空服务限制，但该次不含Java启动或源码profile修改；随后仅Puyu两库DB迁移另获明确授权，按下节现状理解。

两源域ID/name/group和正文原样，没有端点适配，可能仍含源本地连接参数；保存成功不代表应用可运行。不把这些连接信息、正文/hash或密码贴进文档/终端/Git，凭据仍按[12受保护位置](12-service-access-and-operations.md)管理，本文不列值。

旧7项保护快照保存在guest私有位置；首run删2后遇缓存暂态停手，新run重新保护剩5并清5→0→导36。不要覆盖旧backup或重跑旧manifest“resume”；失败应先只读核DBmetadata与普通GET缓存差异。DELETE读回仅等404/原基线200，不重复DELETE；POST读回404可等、200错正文立即停。所有namespace/账号/role/权限/业务DB/服务保留，缺两域仅元数据create，不通过SQLtruncate或重启凑通过。后续参见[本次导入记录](completion/20261109-nacos-config-import/)。

### Puyu两库已迁入测试MySQL

用户本次明确授权仅本机`puyu_*`实际选定两库迁往VM210/`192.168.19.20:3306`，覆盖之前“不迁业务DB”的限制；按**原库名**新增，不覆盖任何原有同名库、不删除源库：

| 数据库 | 表数 | 导出快照行数 |
| --- | ---: | ---: |
| puyu_auth_local | 4 | 178 |
| puyu_erp_local | 47 | 1113 |
| 合计 | 51 | 1291 |

源22:41一致性快照导出，源应用未停止、DML可继续；备份DDL锁持有约0.42秒并已释放，1291为导出快照行数，不是源库以后保持不变的计数，也没有持续同步。原名迁入、写前无同名检查及[prepare](completion/20261109-puyu-db-migration/prepared.json)、[apply](completion/20261109-puyu-db-migration/applied.json)、[verify](completion/20261109-puyu-db-migration/verified.json)已原生通过；同版完整redump的DDL/每表INSERT多集指纹与行数一致，51表CHECK TABLE通过。[独立只读后检](completion/20261109-puyu-db-migration/postcheck.json)已逐表核51个COUNT(*)与导出快照匹配，原四容器、Nacos36配置和既有Finger/Nacos表保持。

源库保留，目标原业务/Nacos数据、既有密码/插件/cnf/服务与应用连接没有修改；临时导入账号和client文件已清理。**没有迁移源MySQL系统账号/全局权限，没有随这次DB迁移导入或改写Puyu Nacos配置，也没有启动Java或切应用连接。** 使用目标既有授权账户，Host匹配、原密码和权限继续生效；SSH仍密钥only、用户ub，Docker管理需`sudo docker`。SQL正文、数据摘要和真实凭据只在受控位置，不在普通文档输出。来源：[预检](completion/20261109-puyu-db-migration/preflight.json)、[源导出](completion/20261109-puyu-db-migration/source-export.json)、[快照计数](completion/20261109-puyu-db-migration/source-fingerprint.json)。

### 当前受信LAN访问（替代早前Nacos-only策略）

用户最新将`192.168.21.0/24`列为受信LAN，允许到`192.168.19.0/24`的有效IPv4服务及网关`21.23/19.1`本机入口；GW和PVE桥两层均已confirmed，hostforward仍全0、无NAT，原WG10.66.66/24许可保持。[GW回执](network19/lan-trusted-20261109/gateway-confirmed.json)、[桥回执](network19/lan-trusted-20261109/bridge-confirmed.json)。

23:00[正测](network19/lan-trusted-20261109/LAN-positive-tests.json)记录ub密钥SSH到19.20和21.23成功，TCP test19.20:3306/8848/9848及prod19.11:8848成功，测试机ping2/2。早前[Nacos-only负测](network19/lan-nacos-20261109/LAN-negative-tests.json)的3306/SSH/正式Nacos timeout是旧策略历史，**不能再作为当前LAN仍被阻断的结论**；新规则不保证不存在的端口有服务，ping也不能替代数据库认证或Nacos权限。

### Puyu数据库使用与认证/TLS

连接目标`192.168.19.20:3306`，使用目标原有授权账户和原密码，遵守MySQL用户Host及schema权限；不能把源Mac系统账号/密码当成已一并迁移。SSH继续ub密钥only，Docker管理需`sudo docker`，这是管理通道而非数据库登录。普通文档不记录真实密码、SQL正文或数据指纹。

[TLS/认证只读诊断](completion/20261109-puyu-db-migration/mysql-auth-diagnostic.json)中root ssl_type为空、require_secure_transport=0；本次仅测试客户端连接，没有新增服务端TLS配置/证书，也没有修改密码、认证插件、Host或安全开关。不要把客户端协商差异解释为已经改过服务器安全配置。

这份源快照的DDL及每表单行INSERT多集/行数通过同版完整redump比对、51表CHECK TABLE；不是业务应用上线、持续复制或完整灾备。[独立只读后检](completion/20261109-puyu-db-migration/postcheck.json)已逐表核51个COUNT(*)与导出快照匹配，原四容器、Nacos36配置和既有Finger/Nacos表保持；不重新初始化/跑源码migration或seed来“补齐”，应用连接与Puyu Nacos参数本次没有改。

### SSH严格连接

在持有用户密钥的管理电脑上执行；先按受信PVE/QGA记录核对host key。**private/known_hosts和私钥不在Git；新电脑clone文档后不能直接获得管理信任。** 必须经已知可信管理员/iDRAC控制台/PVE-QGA核实指纹并受控交接本机known_hosts；ssh-keyscan只能收集候选，不能单独证明可信。不要把私钥或known_hosts当普通文档提交。以下路径是原管理电脑示例，新电脑应使用其已核本机路径；示例用于**合并后的220管理地址**：

```bash
ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes \
  -o ConnectTimeout=8 -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/Users/yangzhaohui/work/www/harness/dell/private/known_hosts \
  root@192.168.21.22

ssh -i ~/.ssh/yang_local_rsa -o IdentitiesOnly=yes -o BatchMode=yes \
  -o ConnectTimeout=8 -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/Users/yangzhaohui/work/www/harness/dell/private/known_hosts \
  -o HostKeyAlias=dell-vm220 ub@192.168.19.30
```

第二条需要管理电脑到19网路由/授权已成立。若需跳板，按[scripts/control.py](scripts/control.py)的严格ProxyCommand和已核`info`使用PVE；不要把客户端私钥复制到PVE/来宾，也不forward agent。host key变化先查物理VM/重装/记录，不用StrictHostKeyChecking=no或盲删known_hosts消警。

## 3. 正常启动与关机

**仅硬件稳定且有相应维护窗口时使用；本次已自动恢复的对象不重复启动。** 先在PVE确认`qm list`、`pct list`、`pvesm status`；模板和退休VM不能混进运行清单。这里给人工顺序，不自动改现役onboot。PVE延时只能排序，不能代替DNS、挂载和应用健康。11月8日已补宿主forward守卫，11月9日自然重启后文件SHA、执行顺序及全forward0已真实读回，见[PVE审计](completion/20261109/pve-audit.json)；日常仍复核全0/无hostNAT，不用恢复宿主转发来修来宾服务。

最后签收的实际onboot order为：**190(1) → CF100(5) → 200(10) → 201(11) → 210(12) → 270(20) → 250(22) → 220(30) → 280(35) → 230(40) → 240(43) → 260(50)**。不要拿旧startup-order.json里已退役231/232的行重新应用。280新增后的完整PVE启动序列未重新整机演练；本次只重启280。人工分阶段gate如下，不改变已配置顺序：

1. 网络阶段先190：`qm start 190`。通过控制台/QGA确认WAN21.23、LAN19.1、路由、DNS/DHCP及原防火墙；19网测试节点验证DNS。别因21网直接DNS请求受限而扩大WAN监听。随后按order5恢复CF100（需要时`pct start 100`），保持原身份/配置；它只是网络隧道进程先就绪，不代表后面的origin或公网E2E已通过。已运行对象不为检查重复重启。
2. 数据阶段先200 MySQL，确认原UUID与dell-data-prod-db.service健康，再201、210各栈；每台检查后往下，不能先起依赖Nacos/DB的业务。
3. 其它批准对象按现役次序：270监控、250 Penpot、220发布与Nexus、280资源NFS、230/240空Java基础、260 NAS。逐台核健康/挂载，不启动Java业务。应用就绪后才复核原CF origin；未知account-side配置或缺证据不签公网E2E。

单VM的常规命令分别是`qm status <VMID>`、`qm start <VMID>`；CT用`pct status/start <CTID>`。替换已登记ID逐条执行，不写遍历所有VM的一键循环。

停止按实际顺序反向并先排空客户端写入/真实播放：**260 → 240 → 230 → 280 → 220 → 250 → 270 → 210 → 201 → 200 → CF100 → 190**，最后才正常关闭PVE。需要事先关闭外部流量入口时，可先在明确维护范围停隧道连接，但不能改写已登记顺序或把190提前停掉。Ops尽量保留到应用停止后供观察；对某个VM：

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
| 220导航 | dell-service-directory.service；dell-service-directory-firewall.service | 固定release位于/opt/dell/service-directory，不是业务发布链 |
| 220 | dell-nexus.service | /srv/nexus，UUID239dc45a-b1f3-408b-a8ef-7afa77b52204 |
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

Ops为机内监控；整台T630失效时可能连告警也失效。Mac外部探针用户明确不需要，现行/后续均移出操作范围；不再要求隐私授权、独立App或重新加载LaunchAgent，历史代码/误告警仅供审计。维护静默只在明确范围使用，健康与零真实告警后解除本次项，不清其它管理员的静默。

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

### 当前仅正式数据库/Nacos逻辑备份

**现行自动备份仅VM200正式数据库/Nacos配置。** 当前唯一非系统库`nacos_prod`，12张BASE TABLE全InnoDB；正式业务schema尚未创建，新增库不在显式白名单则拒绝告警并要求更新。首轮逻辑SQL gzip 3,301 bytes通过CRC/传输SHA、DDL锁释放及guest暂存清理，service退出0、timer已enabled，下一次2026-11-10 03:30（Asia/Shanghai）；GFS最近3/每日7/每周4。PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600，不经Mac，见[新首轮与timer](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)、[中央状态](completion/20261109-prod-db-scope/README.md)。

其他数据均不自动备份：VM/OS、测试库、Redis/Rabbit、Nexus、Penpot、NAS、Ops、CF及发布私钥排除。旧11来宾全机jobdisabled、whole-VM规则组退役，原19,747,582,801 bytes全机档和21回退档保留、不自动删除；旧CF档只准PVE。新`dell_prod_db_backup_*`三条db-only规则已原生校验/SIGHUP加载，原Prom身份与既有三告警名/Lark接收对象不变，无testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。仅同机逻辑恢复点，仅下述小档已临时隔离恢复，仍无完整业务恢复/独立灾备或RPO保证；不再迁移其他数据、不启Java、无Mac外部探针。

任务由PVE `dell-prod-db-backup.service`/`.timer`编排，受限QGA从VM200导出与分块回收PVE；不读取完整Env/Cmd，不在终端cat SQL/manifest或秘密。worker持LOCK INSTANCE备份锁、single-transaction导出，前后固定表元数据一致；当前仅BASE TABLE/InnoDB、无view/routine/event/trigger，出现新库/对象必须先审核更新策略，不强行放行以凑成功。

日常只核定时器/服务与中央脱敏回执，不重跑安装器或旧全机job：

```sh
systemctl status dell-prod-db-backup.timer
systemctl status dell-prod-db-backup.service
```

暂停未来timer不代表正在进行的导出已停止；取消或故障先核本次run_id、own dump PID/starttime/pidfd及锁会话退出证明，不kill mysqld、不删未知文件、不通配删除归档/guest暂存。PVE已原子收存并校验后才cleanup本次双文件；失败产物需准确核查，不用替换路径绕过门禁。本轮仅将该小快照恢复到独立临时实例，禁止直接导入覆盖现役库。

**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

本次guest核验47.522秒、PVE总流程59.857秒、unit退出0；这不是业务RTO。最终仍严格核DDL/列顺序、逐列HEX/NULL行摘要、CHECK TABLE和重启持久化；仅MySQL官方bug110825的引号外紧邻COLLATE、经临时实例COLLATIONS映射证明相同的冗余CHARACTER SET作同义规范化，不忽略真实字符集/COLLATE、类型、索引或COMMENT差异。旧失败和cleanup证据保留。

### 历史回退档与应用备份边界

清理前已保留21份受保护PVE归档，目录`/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/`，root0700，归档/日志0600；压缩约29.9GiB。这是同一物理机/存储内的回退档，**不是异机灾备**。SHA/zstd/VMA全档完整性通过，不表示每份旧实例都恢复开机验过，见[备份汇总](cleanup/backup-summary.json)。

不可跨越：CF归档仅PVE，不导出Mac；publisher私钥仅220，禁止wholebackup/snapshot220来夹带复制它。普通应用初始副本与恢复证据有范围限制：Rabbit definitions不含消息、Redis初始快照0keys、Grafana备份不等于Prometheus/Alertmanager全部历史，NAS媒体不是正式业务备份目标。旧11档全机成功保留为历史，但原生job现已disabled；当前仅正式DB/Nacos逻辑备份；长期独立目的地与真实RPO/RTO仍未签收。

每次备份先登记对象、版本、身份边界、目标、容量、加密/权限及一致性条件。数据库/Blob一起取一致性点，正在运行的目录拷贝不能冒称一致备份。原10.63门禁的历史application-backup脚本必须先核适配现役19配置，不能从旧README直接抄--execute命令。秘密通过受控文件/STDIN使用，不把整个private打包上传Nexus。

### 全机归档恢复人工参考（本轮未执行）

以下是旧全机归档的未来恢复流程，与本次SQL临时恢复不同，本轮未执行：

1. 硬件稳定后选择明确归档，与受信记录对SHA，并做`zstd --test <归档>`。需要VMA全档核验时在**PVE root700临时目录**解压、文件600，预留足够原始空间，再`vma verify <原始VMA>`；不要解压含秘密整机档到Mac或公共目录。
2. 分配新的恢复QA VMID和预算，确认不会覆盖保留VM/卷。PVE恢复示意：

```bash
qmrestore <已核归档路径> <新QA_VMID> --storage <批准存储> --unique 1
```

3. **首次启动前断开QA网卡或放入已审隔离网络**，保留唯一MAC/身份规划，禁止与原实例同IP/同服务同时写同盘。恢复档可能带原固定地址与秘密，unique MAC不自动消除所有身份/地址冲突。
4. 在QA核OS/UUID/实际应用/账号权限与原数据SHA，再做需要的业务只读校验；数据库不可只看容器running。记录步骤/时间/失败/限制，才决定是否切换。未验恢复不宣称RPO/RTO。
5. 回滚指针/JAR不回滚SQL、Nacos或新用户数据；恢复测试禁止直接覆盖现役数据。QA清理由准确VMID/卷manifest与依赖检查决定，不按目录或base-*通配删除。

## 7. Nexus已恢复合并：按本次回执维护

用户已明确恢复执行，覆盖此前暂缓范围。220已完成目标启动/验收与受控重启，6CPU8GiB、primary30和同NIC服务alias31，原Nexus盘唯一移入scsi2；最终数据/身份/网络/监控及221退役已按[本次交付](completion/20261110-nexus-merge/README.md)签收。旧迁移命令不再是可重放维护流程。

现役日常检查、正常启停、认证、卷UUID、发布器和备份边界统一见[合并后操作手册](completion/20261110-nexus-merge/usage-manual.md)。31仍Nexus8081兼容URL，SSH管理用30及220自身host key；不复制221 host key，也不用旧dell-vm221信任别名连接新220。原build卷保留，不将Nexus数据写入根盘/构建目录，不启动双writer。

本次GET-only新鲜基线为12repos/7hosted/50components/1347assets；原49GAV234主件只是历史子集。源停服关机后PVE冷备2,400,054,202字节且SHA/zstd/VMA通过，仅PVE保留。旧安装ISO占用220 scsi2，已先卸CDROM配置再移原盘，未删除ISO文件。target commit遇generated mount发现时，先核13目标SHA一致、daemon-reload，再将真实generated srv-nexus.mount一并原生验证；不关闭验证追过。

220原SSH/QGA/exporter/导航4项检查保留，加Docker/Nexus/MCP为7项；Nexus HTTP只本机alias31，MCP仅unit。移除221后包含280的10node+5Ops=15targets，不能误删资源280。实际runtime与canonical历史有差异，按fresh逐文件CAS，禁止重装全部collector覆盖已有profile。

旧[技术计划](cleanup/nexus/PLAN.md)和[resume清单](cleanup/nexus/resume-preflight.md)只保存历史过程，禁止重放stage/mount/commit/start/fresh-init。原盘回退并未实演；221最终删除后，不能照抄反向move给不存在实例，需先按受保护备份/隔离地址重新评估恢复。220发布私钥始终仅220，不整机备份、读出或复制；自动备份仍只正式DB/Nacos。

## 8. 失败时停手与禁止重跑清单

OW完整规则按用户要求只留本地，不触碰或上传，也不push其local-only分支；本机备份或文档交付不扩大这一范围。

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
- Penpot `fresh-target.py init`、历史source凭据复制/PG全库覆盖流程；当前保留Git改造、新身份和既有数据，不重新初始化；main文档合同更新不授权升级历史ff1783e应用。
- Nexus `fresh-instance.py`、`bootstrap-new.py`、`accept-eula.py`不用于同实例合并恢复；不重置账号、EULA、repo或导入旧H2。
- Docker `down -v`、volume rm、prune --volumes，或整机/模板目录通配删除；运行中数据不是可清缓存。
- Java模板clean.py、cloud-init clean/machine-id/hostkey删除只用于明确fresh builder，不能“修复”现役VM。
- 已完成的旧15对象/QA删除脚本、旧候选30测试版publisher部署器；不能重复删ID或把未部署候选覆盖现役。
- Mac外部探针LaunchAgent和自动恢复发送；用户明确不需要，现行和后续不配置，不因本手册存在而重启。

所有复杂变更先形成具体对象、影响、前置、差异、验证与回退，按已满足的授权范围执行；新业务/删除/外部身份或未涵盖风险另行明确。普通文档检查只运行本地`python3 scripts/validate_docs.py`，不代表远程健康或硬件已修复。

## 测试凭据的最新维护约定（11月9日）

VM210三组件按用户指定并再次要求保持的约定同步：MySQL现有root两Host、Redis默认认证、Rabbit指定admin管理身份；原Rabbit管理/应用账号保留。现役guest持久文件与Mac private测试活动来源已同步，实际回执及后检见[凭据交付](completion/20261109-test-credentials/README.md)。这次另获授权的同步发生在数据库快照迁移之后；不改正式/源Mac/Nacos身份，不重跑初始化器覆盖固定值，也不改TLS/插件。真实密码不写普通文档或Git。

## 2026-11-10 Puyu设计导入

VM250 owner工作区新增 **puyu项目 / puyu文件**，包含puyu-mobile、puyu-components、puyu-mobile · 商城三页，共58,240图形、19组件。源为本机rev2821，旧7文件保持，当前11healthy，原代码与默认填入保持；本次未部署首次引导源码或迁账号。详见[导入使用手册](evidence/penpot-puyu-import-20261110/usage-manual.md)。这是快照导入，不自动同步，不扩正式DB/Nacos之外的备份。

## 本地Penpot MCP切服务器

Codex私有配置两项MCP已改SSH stdio到VM250，密钥只在服务器；实际新进程返回puyu/组件页，原生11healthy、原设计/密码保持。当前聊天旧连接缓存仍在，需客户端重载MCP或重启Codex，最后一项验收pending；无法通过受限GUI代点重载。见[连接手册](evidence/penpot-client-mcp-20261110/usage-manual.md)。Mac原实例仍运行。

## VM220 Puyu local发布器与MCP

发布器源码在`/opt/deploy-public`，MCP为ub运行的puyu-deploy-mcp.service，仅127.0.0.1:18765。最新源main/213f1f4已推送并由VM220同步clean，Linux65测试通过；新MCP预检按设计拒绝缺origin/dev，服务active，回执见[模式更新](evidence/deploy-public-modes-20261110/README.md)。密钥只在VM220统一YAML600，不打印或进Git，不替换全局Codex MCP连接。

CLI支持prod→main、dev→dev；MCP仅dev，拒绝prod和调用方环境覆盖。六仓库main源码已经准备，工作树仍main，上游dev全部缺失；新dev预检应拒绝缺origin/dev，不能复用初装dev/main成功结果。prod目标`puyu-prod`身份留空时也应拒绝，不复用测试目标deployer@19.45。真实发布任务仍关闭，旧受限链fenced，不创建/推送业务分支、不构建或启动Java。

项目详情区分source_ready、expected_branch、current_branch和target_branch_available，最后一项仅本地origin引用。列出/预检不fetch；显式sync才取配置分支，真实远端缺dev时失败，不回退main。源码/产物/队列仍在原100GiB构建盘并保UUID启动门禁。更新只Git快进受审查版本，先核clean与无活动任务，不覆盖私有YAML或重生成APIkey，不重跑bootstrap。220原专用发布私钥不得导出，Nexus合并按本次独立回执，备份仍只正式DB/Nacos。

[发布机操作手册](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)、[完整操作说明](https://github.com/bkcode/deploy-public/blob/main/docs/OPERATIONS.md)、[初装验收历史](evidence/deploy-public-publisher-20261110/README.md)。


当前FileBrowser已按后续明确授权从现役安装路径移除（不再只是masked停用），专属闲置账号删除，NFS及资源文件保持；旧说明仅阶段历史。详见[移除后NFS使用说明](completion/20261110-filebrowser-remove/README.md)。
