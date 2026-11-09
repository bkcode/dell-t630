# 当前交接：测试配置与Puyu两库迁入完成

更新：2026-11-09，Asia/Shanghai。用户继续授权完成基础搭建，并明确仅自动备份正式数据库/Nacos配置；内存现场处理/诊断通过由用户此前确认。**最新另授权仅puyu_auth_local/puyu_erp_local迁往210并保留源；正式不动、不合并Nexus、不退役221、不启动Java。** 以前短停合并许可保留为历史，不覆盖这次明确暂缓。

当日执行状态唯一入口：[11月9日交付记录](completion/20261109-prod-db-scope/README.md)。[11月8日恢复记录](recovery/20261108/README.md)为上轮历史。

## 已核事实与实际变更

- 12来宾自然onboot启动、3模板停止；15监控目标UP，Prom/AM无活动告警；主要6HTTP入口通过。盘UUID、容器镜像与健康按角色复核，不能扩写成全量内容/认证/外网E2E验收。
- 当前启动4×32GB/EDAC ce/ue均0，RAID1/5 Optimal/5盘在线；内存维修诊断是用户报告，助手未独立做离线诊断/压力测试。
- PVE桥转发启动漂移已由3个owned guard补齐；11月9日14:24自然重启后，SHA相同、networking→bridge/ExecStartPost→pve-guests实际顺序与全forward0已读回，不再仅为待验候选。管理interfaces/路由/ACL、无NAT边界保持。
- 本轮[空闲iperfserver已停用自启](completion/20261109/idle-iperf-disabled.json)、5201关闭，软件包保留，没有应用/来宾重启。
- 原15旧对象/6临时对象已在此前清理，本轮无多余实例或unused磁盘；只清确认无引用且发行商SHA一致的旧安装ISO，执行结果以恢复记录receipt为准。共享ISO、21回退档、来源不明LXC cache保留。

## 配置与业务边界

221仍独立19.31/原Nexus卷，220仍4CPU4GiB/主IP19.30、0Nexus容器；6CPU8GiB+31alias只在[目标架构](17-publish-artifact-consolidation.md)中，未应用。发布key只220，CF备份只PVE；不得整机备份220或以清理名义删除源221数据。

230/240各一，仅运行基础，无Java业务进程/自启；publisher仍fenced。Penpot保留实际ff1783e版本，用户指定的bkcode/penpot main是未来更新合同，本轮未取码/构建/升级。

## 测试Nacos配置迁移已完成

用户最新授权覆盖之前仅空服务方向：source两域finger-cloud-dev `08e7191f-3ccd-411a-be00-56798d237533` 32项、finger-trascan `7bfe03c6-0590-4ff0-8def-e07015016b54` 4项现已原ID/name/group/body导入210，types35yaml/1text；[applied](completion/20261109-nacos-config-import/applied.json)及[verified](completion/20261109-nacos-config-import/verified.json)确认36项正文/metadata exact。旧finger-test `10719261-2641-590a-b821-c8484ca955ac`、新empty `23836f2e-9553-5948-84cd-431b2f241bd6`及public现均0。20:27空基础创建时旧7项保留的记录仍属历史，不追改原证据。

原7配置完整保护快照留guestprivate：初次删2后因cache延迟停手，另run备剩5/清5→0→导36，未覆盖旧快照或盲resume。namespace、users/role/permissions、业务DB和服务保持，仅缺source域时create元数据；未新增App权限、不Java/不改源码profile。`finger_test`仍只old＋empty，可管理新域的是现有admin；后续业务需显式授权新ID。配置原样可能仍指源本地连接，未适配、不保证业务可运行，旧内容/hash/密码不进普通文档。详见[导入目录](completion/20261109-nacos-config-import/)。


## Puyu两库已迁入测试MySQL

用户本次明确授权仅本机`puyu_*`实际选定两库迁往VM210/`192.168.19.20:3306`，覆盖之前“不迁业务DB”的限制；按**原库名**新增，不覆盖任何原有同名库、不删除源库：

| 数据库 | 表数 | 导出快照行数 |
| --- | ---: | ---: |
| puyu_auth_local | 4 | 178 |
| puyu_erp_local | 47 | 1113 |
| 合计 | 51 | 1291 |

源22:41一致性快照导出，源应用未停止、DML可继续；备份DDL锁持有约0.42秒并已释放，1291为导出快照行数，不是源库以后保持不变的计数，也没有持续同步。原名迁入、写前无同名检查及[prepare](completion/20261109-puyu-db-migration/prepared.json)、[apply](completion/20261109-puyu-db-migration/applied.json)、[verify](completion/20261109-puyu-db-migration/verified.json)已原生通过；同版完整redump的DDL/每表INSERT多集指纹与行数一致，51表CHECK TABLE通过。[独立只读后检](completion/20261109-puyu-db-migration/postcheck.json)已逐表核51个COUNT(*)与导出快照匹配，原四容器、Nacos36配置和既有Finger/Nacos表保持。

源库保留，目标原业务/Nacos数据、既有密码/插件/cnf/服务与应用连接没有修改；临时导入账号和client文件已清理。**没有迁移源MySQL系统账号/全局权限，没有随这次DB迁移导入或改写Puyu Nacos配置，也没有启动Java或切应用连接。** 使用目标既有授权账户，Host匹配、原密码和权限继续生效；SSH仍密钥only、用户ub，Docker管理需`sudo docker`。SQL正文、数据摘要和真实凭据只在受控位置，不在普通文档输出。来源：[预检](completion/20261109-puyu-db-migration/preflight.json)、[源导出](completion/20261109-puyu-db-migration/source-export.json)、[快照计数](completion/20261109-puyu-db-migration/source-fingerprint.json)。

## 当前受信LAN访问（替代早前Nacos-only策略）

用户最新将`192.168.21.0/24`列为受信LAN，允许到`192.168.19.0/24`的有效IPv4服务及网关`21.23/19.1`本机入口；GW和PVE桥两层均已confirmed，hostforward仍全0、无NAT，原WG10.66.66/24许可保持。[GW回执](network19/lan-trusted-20261109/gateway-confirmed.json)、[桥回执](network19/lan-trusted-20261109/bridge-confirmed.json)。

23:00[正测](network19/lan-trusted-20261109/LAN-positive-tests.json)记录ub密钥SSH到19.20和21.23成功，TCP test19.20:3306/8848/9848及prod19.11:8848成功，测试机ping2/2。早前[Nacos-only负测](network19/lan-nacos-20261109/LAN-negative-tests.json)的3306/SSH/正式Nacos timeout是旧策略历史，**不能再作为当前LAN仍被阻断的结论**；新规则不保证不存在的端口有服务，ping也不能替代数据库认证或Nacos权限。

## 正式数据库/Nacos备份交接

**现行自动备份仅VM200正式数据库/Nacos配置。** 当前唯一非系统库`nacos_prod`，12张BASE TABLE全InnoDB；正式业务schema尚未创建，新增库不在显式白名单则拒绝告警并要求更新。首轮逻辑SQL gzip 3,301 bytes通过CRC/传输SHA、DDL锁释放及guest暂存清理，service退出0、timer已enabled，下一次2026-11-10 03:30（Asia/Shanghai）；GFS最近3/每日7/每周4。PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600，不经Mac，见[新首轮与timer](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)、[中央状态](completion/20261109-prod-db-scope/README.md)。

其他数据均不自动备份：VM/OS、测试库、Redis/Rabbit、Nexus、Penpot、NAS、Ops、CF及发布私钥排除。旧11来宾全机jobdisabled、whole-VM规则组退役，原19,747,582,801 bytes全机档和21回退档保留、不自动删除；旧CF档只准PVE。新`dell_prod_db_backup_*`三条db-only规则已原生校验/SIGHUP加载，原Prom身份与既有三告警名/Lark接收对象不变，无testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。仅同机逻辑恢复点，仅下述小档已临时隔离恢复，仍无完整业务恢复/独立灾备或RPO保证；不迁移、不合并Nexus、不启Java、无Mac外部探针。

旧全机启用的早前阶段已被本次用户新范围取代，不按旧手册重新启用。其他完整恢复、真实家庭设备、硬件长期观察仍按原边界另验。

**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

## 告警与待办

用户明确不需要Mac外部探针，现行及后续不配置/恢复；只留内部Prometheus/Grafana/Lark。历史probe文件保留供追溯，不能因此创建恢复任务。同机告警不保证整机失联外发。

继续事项为基础补齐、已授权本机备份收尾及具体已审清理；未来迁移须用户另行恢复该任务，再fresh基线/冷备/唯一盘地址交接/原身份数据验证与回退。真实家庭设备、完整灾备与业务SLO仍未签收。OW完整规则只留本地，不触/不上传，不push local-only分支。

原11月7日02:35验收、02:44:29规划同步和随后UEFI0058记录保留在[硬件事故](cleanup/hardware/DIMM_B1-incident.json)，不改写历史。当前操作手册见[19](19-manual-operations.md)，逐机配置见[machines](machines/README.md)。

## 测试凭据的最新维护约定（11月9日）

VM210三组件按用户指定并再次要求保持的约定同步：MySQL现有root两Host、Redis默认认证、Rabbit指定admin管理身份；原Rabbit管理/应用账号保留。现役guest持久文件与Mac private测试活动来源已同步，实际回执及后检见[凭据交付](completion/20261109-test-credentials/README.md)。这次另获授权的同步发生在数据库快照迁移之后；不改正式/源Mac/Nacos身份，不重跑初始化器覆盖固定值，也不改TLS/插件。真实密码不写普通文档或Git。
