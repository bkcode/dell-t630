# 当前访问入口与日常操作

2026-11-10，Asia/Shanghai。**自然重启后基础服务fresh复验；继续基础搭建，仅自动备份正式数据库/Nacos，并按最新授权完成测试Nacos配置原样迁移；最新另授权Puyu两库按原名迁入测试210，正式环境不动。** Nexus仍独立221，Mac外部探针不需要。当日状态见[11月9日交付记录](completion/20261109-prod-db-scope/README.md)，[11月8日恢复](recovery/20261108/README.md)保留历史。应用直接访问真实19地址；PVE21.22只用于宿主管理，原应用DNAT端口已关闭。详见[当前交付](15-network19-delivery.md)与[新网络验收](network19/audit/network19-acceptance.md)。

| 服务 | 当前入口 | 范围 |
| --- | --- | --- |
| 服务导航 | https://192.168.19.30:9080/ | 免登录只读入口；自签TLS，LAN21/WG10；各目标独立认证 |
| PVE | https://192.168.21.22:8006/ | 管理SSH22保留 |
| 虚拟网关190 | WAN192.168.21.23 / LAN192.168.19.1 | 路由、19DNS/DHCP，无NAT |
| Penpot | http://192.168.19.50:9001/ | Git定制版、3设计/973媒体、11服务 |
| 测试Nacos | http://192.168.19.20:8848/nacos/ | 受信LAN21/24可达；cloud-dev32＋trascan4原样保留，账号仍须目标域权限 |
| 测试MySQL / Puyu两库 | 192.168.19.20:3306；puyu_auth_local / puyu_erp_local | 原名新建迁入51表/1291快照行；既有目标账户Host/密码/权限仍有效 |
| Nexus | http://192.168.19.31:8081/ | 目前归221；合并目标归220同NIC服务alias，URL不改 |
| OMV | http://192.168.19.60/ | 家庭NAS管理 |
| Jellyfin | http://192.168.19.60:8096/ | 媒体库、DirectPlay协议已验 |
| SMB | `smb://192.168.19.60/media`、`/games`、`/incoming` | writer/reader分离，匿名拒绝；使用固定IP连接 |
| Grafana | http://192.168.19.70:3000/ | 真实内网入口，无需旧13000隧道 |
| Prometheus / Alertmanager | 192.168.19.70:9090 / :9093 | 仅批准管理来源，不公开 |
| Java业务 | **停用** | 测试五服务无进程/自启，正式无业务应用 |
| 统一资源NFS | `192.168.19.80:/` → 两running `/mnt/resources` | 仅230/240，NFS4.1/TCP2049；与下列管理HTTPS用途不同 |
| FileBrowser管理页 | https://192.168.19.80:8080/ | 日常resources、维护admin；自签TLS，LAN21/WG10；无公开图片URL |
| Java验收模板 | PVE VMID9011 `tpl-java-acceptance` | 唯一验收模板，无应用/业务配置/秘密 |

原HTTP入口是用户同意的LAN阶段；新增服务导航与FileBrowser使用自签HTTPS，公网域名/其他入口HTTPS/SMTP尚未配置。跨子网的发现广播不作为已验能力，电视/播放器请手动填写19.60。NAS用于文件保存/整理/传输，不承诺主机直接从NAS运行游戏。

合并目标为一台VM220 `publish-service`同时承载发布与Nexus，主IP30+服务alias31；`artifact-service`不再是独立目标VM，见[17合并架构](17-publish-artifact-consolidation.md)。**下表是迁移尚未执行的最后验收归属**：

| VMID | 最后验收角色 | IP |
| --- | --- | --- |
| 100 | cf-tunnel CT | 192.168.19.5 |
| 200 / 201 | 正式MySQL / Redis+Rabbit+Nacos | 192.168.19.10 / .11 |
| 210 | 测试MySQL+Redis+Rabbit+Nacos | 192.168.19.20 |
| 220 / 221 | 发布机 / Nexus | 192.168.19.30 / .31 |
| 230 | 正式JDK运行基础，无业务，仅保留一台 | 192.168.19.40 |
| 240 | 测试JDK基础，五业务已停用 | 192.168.19.45 |
| 250 / 260 / 270 | Penpot / NAS / Ops | 192.168.19.50 / .60 / .70 |

所有19来宾默认GW/DNS为19.1；仅网关WAN使用21.23。OW route为19/24经21.23。旧101/104及多余模板/QA已在受保护备份后删除，详见[本轮清理](18-cleanup-and-consolidation.md)。保留的9001/9010/9011三模板仅接vmbr19；已删旧模板只在历史证据中出现。未知clone须先分配IP、登记MAC/IP ACL，不能直接访问正式数据。

SSH使用ub和`~/.ssh/yang_local_rsa`，严格已核host key；受控目标见`evidence/implementation/private-guest-access.json`，代码见`scripts/control.py`。该JSON虽名称含private，内容为IP/公钥指纹索引，不包含私钥；实际`private/known_hosts`不进Git，新电脑须先可信交接指纹。PVE root只用于管理/QGA，不复制客户端私钥，不关闭主机密钥检查。模板克隆按[Java模板说明](network19/java-template/README.md)注入独立hostname与地址。

日常启停、故障处理、克隆和备份步骤见[人工操作手册](19-manual-operations.md)，换电脑接手见[Git交接](20-git-and-handoff.md)。

## 免登录服务导航（VM220新增）

新增 **[服务导航](https://192.168.19.30:9080/)**，无需账号密码，只预览14个HTTP/HTTPS入口，支持分组、搜索、环境筛选、清除筛选、刷新、复制和新标签页跳转。目标由客户端直接访问并继续使用各自认证；不提供SSO或健康探测。首次核对[公开证书](evidence/service-directory-20261110/tls.crt)及[使用手册](evidence/service-directory-20261110/usage-manual.md)中的SHA256指纹，LAN21/24、WG10.66.66/24及本机可达。

这是用户后续明确授权的发布机导航增量：`bkcode/deploy` 仅 `service-directory/` 模块提交 `63b8c0873936e94f8483c4f1f8747aedb0180d43` 已原生启动，专用OS用户UID/GID2001只读运行，无应用账号密码、CRUD、数据库或JSON运行状态。[原生验收](evidence/service-directory-20261110/native-acceptance.json)、[仅导航重启](evidence/service-directory-20261110/service-restart.json)、[浏览器预览](evidence/service-directory-20261110/browser-acceptance.json)及[最终后检](evidence/service-directory-20261110/final-postcheck.json)已通过：14匿名入口保持，13来宾/3模板、16targets全UP、PVE forwarding全0。浏览器签展示/搜索/复制提示/390px布局及href安全属性，真实pointer新窗跳转未签、未探测目标服务；[中央记录](evidence/service-directory-20261110/README.md)含具体边界与源码已本机提交但未push的说明。清单更新走项目Git→新release→只重启导航；不调用原发布链，不改PVE/路由，不启动Java、不合并Nexus、不替用户push或更新Penpot。

## FileBrowser Quantum管理页面

新增私有管理入口 **https://192.168.19.80:8080/**，仅LAN21/24、WG10.66/24及本机；日常`resources`可浏览/下载/新建上传，delete/edit/override/share/提权直接API已验403；维护`admin`有完整权限，不把日常限制说成它也绝对不能删除。密码只在Mac `dell/private/credentials/filebrowser-management-20261110.json`与guest root `/etc/dell-filebrowser/secrets/login.json`保管，不在文档输出值。首次核[tls.crt](completion/20261110-filebrowser/tls.crt)的SHA256指纹后接受/导入；无公网域名、无系统truststore变更。

官方native固定v2.1.4-beta（不是stable），UID2000/GID2980、UMask0002、文件660/目录2770，DB/cache在非共享的`/var/lib/dell-filebrowser`700；初始化marker在root的`/etc/dell-filebrowser/bootstrap.complete`，正常后续启动不再注入初始化口令。自身metadata自动备份关闭，不扩正式DB/Nacos备份；Docker未装，NFS/PVE/路由不改，不Java、不业务图片URL、不迁旧文件。

[原生API/NFS验收](completion/20261110-filebrowser/native-acceptance.json)passed且fixture已清；[真实浏览器](completion/20261110-filebrowser/browser-acceptance.json)只签登录/列表及观察到href后的96PNG深链渲染，自动点击未导航，未签所有按钮。[只重启新app](completion/20261110-filebrowser/service-restart.json)已保持账号、scope和JWT且不再注入初始化口令，NFS/VM/clients未重启；[06:12最终后检](completion/20261110-filebrowser/final-postcheck.json)已确认13运行来宾、3停止模板、16targets全UP、资源6服务指标及专属CA HTTPS健康均UP，PVE全forward0；未加Promtarget/receiver或外发测试消息。完整[管理页使用手册](completion/20261110-filebrowser/usage-manual.md)含证书指纹、账号、维护/升级与故障步骤；[公开服务包](infra/resources/filebrowser/README.md)。

## 统一资源服务（新增VM280）

用户选择正式/测试共用VM280 `resource-service`（19.80）的同一目录。独立100GiB ext4盘挂`/srv/resources`，系统盘保32GiB；两running 230/240目标挂载均为`/mnt/resources`，240原`/mnt/dell-artifacts`不动。NFSv4.1-only/TCP2049/fsid0，只有19.40/19.45获export与bridge/专属输入许可；root_squash、sync、server根2770/defaultACL、共享resources附属组2980。finger原UID999/GID989保留。

[server启动](completion/20261109-resources/server-installed.json)与[实际盘UUID](completion/20261109-resources/storage-initialized.json)已留证；两客户端真NFS挂载/guard、非root跨机创建/读写/删除、root_squash与240缺挂载根盘写入负测均已通过；仅VM280受控重启约30秒，fsync canary持久、两客户端挂载恢复，未重启两台running。**NFS保留，另加受限FileBrowser管理HTTPS；不提供业务图片URL、不启Java、不迁文件、不扩自动备份。** 资源角色使预算变为13来宾（12VM＋CF LXC）、3模板、45vCPU/87GiB；保守125GiB预算余38GiB。[00:20最终只读后检](completion/20261109-resources/final-postcheck.json)确认13来宾运行、3模板停止、16/16 targets UP、资源5项服务指标UP与PVE全forward0。详见[280机器目录](machines/vm280-resource-service/README.md)与[资源使用手册](completion/20261109-resources/usage-manual.md)。

模板仅能将来预装客户端与disabled挂载候选，clone按真实IP/组/exports/bridge登记后显式激活；**本次没有修改三模板**。

[独立native验收](completion/20261109-resources/native-acceptance.json)与[仅280重启](completion/20261109-resources/reboot-exercise.json)覆盖本次专属fixture，不含真实业务或文件恢复。findmnt允许systemd-1 autofs加唯一真实nfs4的合法stack，可用`-t nfs4`辨识；单独autofs仍不算共享已挂载。客户端文件创建明确用umask0002；首轮失败及清理记录保留，随后仅按已批准UMask重跑fixture，未修改服务来追过。新增280 fish4.0.2、root/ub默认Bash已后检；当前10台guest＋3模板具备fish基线。

应用尚未接入：Finger的`file.upload.path=/mnt/resources`仅建议，未改实际配置/Nacos/profile；业务HTTP domain/公开图片URL未搭。Puyu现有images在MySQL内通过权限接口下载，NFS不会自动迁出，也未随部署改Java或应用连接。


## 当前受信LAN访问（替代早前Nacos-only策略）

用户最新将`192.168.21.0/24`列为受信LAN，允许到`192.168.19.0/24`的有效IPv4服务及网关`21.23/19.1`本机入口；GW和PVE桥两层均已confirmed，hostforward仍全0、无NAT，原WG10.66.66/24许可保持。[GW回执](network19/lan-trusted-20261109/gateway-confirmed.json)、[桥回执](network19/lan-trusted-20261109/bridge-confirmed.json)。

23:00[正测](network19/lan-trusted-20261109/LAN-positive-tests.json)记录ub密钥SSH到19.20和21.23成功，TCP test19.20:3306/8848/9848及prod19.11:8848成功，测试机ping2/2。早前[Nacos-only负测](network19/lan-nacos-20261109/LAN-negative-tests.json)的3306/SSH/正式Nacos timeout是旧策略历史，**不能再作为当前LAN仍被阻断的结论**；新规则不保证不存在的端口有服务，ping也不能替代数据库认证或Nacos权限。


## 测试Nacos配置现状：36项原样导入完成

用户最新明确授权本机Nacos配置迁移，**覆盖先前“只搭空服务、不迁配置”的限制**；该次Nacos迁移不涉及业务DB；后续Puyu两库另获本次授权，正式环境不动、不启动Java或修改源码profile。同一测试入口`http://192.168.19.20:8848/nacos/`内现有配置如下，namespace ID/name、group与正文保持源原样：

| namespace | ID | 当前配置数 |
| --- | --- | ---: |
| finger-cloud-dev | `08e7191f-3ccd-411a-be00-56798d237533` | 32 |
| finger-trascan | `7bfe03c6-0590-4ff0-8def-e07015016b54` | 4 |
| finger-test（旧域） | `10719261-2641-590a-b821-c8484ca955ac` | 0 |
| finger-test-empty | `23836f2e-9553-5948-84cd-431b2f241bd6` | 0 |
| public | 默认域 | 0 |

[applied](completion/20261109-nacos-config-import/applied.json)与[只读verified](completion/20261109-nacos-config-import/verified.json)确认合计36项、当前全部group为`DEFAULT_GROUP`，类型35 yaml＋1 text，正文及type/appName/desc等受审元数据在私有流程exact比对通过。原样内容可能仍含源本地连接参数，**没有端点适配，不代表服务器应用已可运行**。

现有测试应用账号`finger_test`原权限仍只覆盖旧finger-test和finger-test-empty两域，**没有grant新导入的两个source namespace**。管理员可管理这两域；未来业务接入须另行明确namespace与应用权限，不能为消除403重置密码/role或自动提权。基础.env/health仍指旧域保兼容，不改源码profile、不启动Java。

旧7项已有guest受保护完整快照；首次删除2项后缓存读回触发安全停止，修复为只读有界等待后，新run另备剩5项、清5→0→导36，没有覆盖旧备份或盲目resume。旧配置history继续保留/产生正常API审计，namespace、用户/role/permissions、业务DB及服务未写，缺失的两source域仅建元数据。这里只记录计数/比较结论，不放旧配置内容、正文hash或密码；后续证据见[导入目录](completion/20261109-nacos-config-import/)。

20:27[空域创建](completion/20261109-test-env/empty-namespace-created.json)当时“旧7项/历史9保留、新空域0”仍是历史事实；后来用户授权清全部配置并导源，当前旧域已0，不能继续称仍有7项。账号凭据仍只由原受保护文件/渠道保管，不在本文披露值。


## Puyu两库已迁入测试MySQL

用户本次明确授权仅本机`puyu_*`实际选定两库迁往VM210/`192.168.19.20:3306`，覆盖之前“不迁业务DB”的限制；按**原库名**新增，不覆盖任何原有同名库、不删除源库：

| 数据库 | 表数 | 导出快照行数 |
| --- | ---: | ---: |
| puyu_auth_local | 4 | 178 |
| puyu_erp_local | 47 | 1113 |
| 合计 | 51 | 1291 |

源22:41一致性快照导出，源应用未停止、DML可继续；备份DDL锁持有约0.42秒并已释放，1291为导出快照行数，不是源库以后保持不变的计数，也没有持续同步。原名迁入、写前无同名检查及[prepare](completion/20261109-puyu-db-migration/prepared.json)、[apply](completion/20261109-puyu-db-migration/applied.json)、[verify](completion/20261109-puyu-db-migration/verified.json)已原生通过；同版完整redump的DDL/每表INSERT多集指纹与行数一致，51表CHECK TABLE通过。[独立只读后检](completion/20261109-puyu-db-migration/postcheck.json)已逐表核51个COUNT(*)与导出快照匹配，原四容器、Nacos36配置和既有Finger/Nacos表保持。

源库保留，目标原业务/Nacos数据、既有密码/插件/cnf/服务与应用连接没有修改；临时导入账号和client文件已清理。**没有迁移源MySQL系统账号/全局权限，没有随这次DB迁移导入或改写Puyu Nacos配置，也没有启动Java或切应用连接。** 使用目标既有授权账户，Host匹配、原密码和权限继续生效；SSH仍密钥only、用户ub，Docker管理需`sudo docker`。SQL正文、数据摘要和真实凭据只在受控位置，不在普通文档输出。来源：[预检](completion/20261109-puyu-db-migration/preflight.json)、[源导出](completion/20261109-puyu-db-migration/source-export.json)、[快照计数](completion/20261109-puyu-db-migration/source-fingerprint.json)。

### MySQL客户端TLS说明

[只读认证诊断](completion/20261109-puyu-db-migration/mysql-auth-diagnostic.json)记录root账号ssl_type为空、require_secure_transport=0；这不是本次新增强制TLS或关闭TLS的配置。客户端TLS仅做只读连接测试，没有修改服务端证书、TLS开关、密码、认证插件或用户Host。网络可达不等于源Mac密码可用于目标：源MySQL系统账户没有迁移，须使用目标原有授权方式；具体客户端协商按现状核查，不据此改服务端安全字段。

## 凭据位置


| 对象 | 受保护位置 |
| --- | --- |
| 数据组件 | Mac `private/data/bundles/<角色>/secrets/` 与各guest受控安装包 |
| 测试Nacos既有应用账号（仅旧域/空域权限） | 用户名查test-data受保护`.env`的`NACOS_CLIENT_USER`；密码查`private/data/bundles/test-data/secrets/nacos-client-password`，不在文档列值 |
| Java合成管理员/测试client | Mac `private/java/secrets/`；测试账号FNTEST0001 |
| Nexus新admin/reader/test publisher | Mac `private/nexus/new-secrets/` 与原221 `/root/dell-nexus-secrets/`；合并验收后由220承接同一身份目录 |
| Penpot新owner | 250 `/etc/penpot/new-identities.json`，owner@dell.local |
| Penpot新worker/MCP | 250 `/etc/penpot/worker-credentials.json`及ID映射文件 |
| NAS新账号 | Mac `private/nas/credentials-metadata.json`索引到600文件 |
| Grafana | Mac `private/ops/bundle/secrets/grafana-admin-password`，账号dell_admin |
| Lark | Mac `private/notifications/lark-webhook`及270 native LoadCredential；实际值不写本页 |
| 发布专用私钥 | **仅220** `/var/lib/dell-publisher/.ssh/test240_ed25519`；不得导出Mac |

目录700、秘密文件600；这些文件不进入普通仓库/日志/截图。旧Penpot账号/session/MCP key没有迁入；客户端旧MCP连接可能仍指Mac源，不能把服务端已验收当客户端配置已自动切换。


Java合成账号与旧配置仅作受控历史备份，不能据此启动业务。旧Mac Penpot MCP连接不自动改写；服务器新origin为19.50，对应客户端接入需使用新目标身份。

## 发布与应用状态

Publisher目标19.45、来源限制19.30、公钥/强制命令与最小权限保留，但`baseline_migrated=false`，业务发布保持冻结。没有发布新Nacos dataId、激活新release或重启五服务。旧immutable JAR/root600配置保留为私有备份；未来上线必须另立明确业务范围、验证新网配置和回退基线，不能直接回指旧10.63配置。

## 监控与备份边界

新增280前，2026-11-09 [Ops审计](completion/20261109/ops-audit.json)再次复验10node+5Ops共15/15UP，Prom/AM无活动告警。本机textfile采集业务范围已移除Java五HTTP检查，当时catalog/installer配套为10节点；资源280加入后实际11node＋5Ops共16目标UP，见[00:20资源后检](completion/20261109-resources/final-postcheck.json)。服务器内部Lark active，172.18内部链与凭据保持；未发送新的验收消息。Mac外部探针明确不需要，已移出当前和后续工作，整机故障无法由机内监控保证外发。

正式业务数据未从开发环境导入。**现行自动备份仅VM200正式数据库/Nacos配置。** 当前唯一非系统库`nacos_prod`，12张BASE TABLE全InnoDB；正式业务schema尚未创建，新增库不在显式白名单则拒绝告警并要求更新。首轮逻辑SQL gzip 3,301 bytes通过CRC/传输SHA、DDL锁释放及guest暂存清理，service退出0、timer已enabled，下一次2026-11-10 03:30（Asia/Shanghai）；GFS最近3/每日7/每周4。PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600，不经Mac，见[新首轮与timer](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)、[中央状态](completion/20261109-prod-db-scope/README.md)。

其他数据均不自动备份：VM/OS、测试库、Redis/Rabbit、Nexus、Penpot、NAS、Ops、CF及发布私钥排除。旧11来宾全机jobdisabled、whole-VM规则组退役，原19,747,582,801 bytes全机档和21回退档保留、不自动删除；旧CF档只准PVE。新`dell_prod_db_backup_*`三条db-only规则已原生校验/SIGHUP加载，原Prom身份与既有三告警名/Lark接收对象不变，无testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。仅同机逻辑恢复点，仅下述小档已临时隔离恢复，仍无完整业务恢复/独立灾备或RPO保证；不迁移、不合并Nexus、不启Java、无Mac外部探针。 真实电视/PS/4K/HDR/转码与生产并发仍待实际验收。


**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

## 2026-11-07 WireGuard受信网段

用户明确全服务授权后，10.66.66.0/24已获准访问19/24全部有效IPv4端口及网关21.23/19.1；NAS的SMB/Jellyfin来源识别同步追加，账号/读写权限不变。外网Mac Air批量入口复测已确认全部正常。无需SNAT，OpenWrt各peer仍独立/32，PVE21.22不恢复转发。见[WireGuard全服务访问](16-wireguard-access.md)。

## 测试凭据的最新维护约定（11月9日）

VM210三组件按用户指定并再次要求保持的约定同步：MySQL现有root两Host、Redis默认认证、Rabbit指定admin管理身份；原Rabbit管理/应用账号保留。现役guest持久文件与Mac private测试活动来源已同步，实际回执及后检见[凭据交付](completion/20261109-test-credentials/README.md)。这次另获授权的同步发生在数据库快照迁移之后；不改正式/源Mac/Nacos身份，不重跑初始化器覆盖固定值，也不改TLS/插件。真实密码不写普通文档或Git。
