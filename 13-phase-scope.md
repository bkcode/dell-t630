# 本期范围与验收边界

更新：2026-11-09。继续完成基础搭建，用户最新仅备正式数据库/Nacos配置，不迁移数据。当日状态见[11月9日交付记录](completion/20261109-prod-db-scope/README.md)：14:24自然重启后12running/3tpl、15targets UP、EDAC0/RAIDOptl及forward guard跨重启保持已fresh核验；内存现场维护/诊断通过来自用户。现行正式DB/Nacos首轮3301B、timer启用及db-only三规则已通过，旧全机11档/启用仅历史且job现已disabled，未扩签独立物理根因、原全部验收或灾备恢复。

## 当前范围

- 继续补齐既有基础服务及仅正式数据库/Nacos逻辑备份，盘点、清理可确认多余项；资源为43vCPU/85GiB、230/240各一运行基础、Java业务不部署，publisher fenced，模板9001/9010/9011保留。
- Nexus221继续独立19.31，220原standby。用户明确暂不迁移；合并pending原因是用户延期，本轮不移盘/合并/退役，不因历史维护授权直接执行。
- Mac外部探针用户明确不需要，保持停用并移出当前及后续待办；不列为故障或未来交付承诺。内部Lark原unit运行，未重新发送通知测试。
- **现行自动备份仅VM200正式数据库/Nacos配置。** 当前唯一非系统库`nacos_prod`，12张BASE TABLE全InnoDB；正式业务schema尚未创建，新增库不在显式白名单则拒绝告警并要求更新。首轮逻辑SQL gzip 3,301 bytes通过CRC/传输SHA、DDL锁释放及guest暂存清理，service退出0、timer已enabled，下一次2026-11-10 03:30（Asia/Shanghai）；GFS最近3/每日7/每周4。PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600，不经Mac，见[新首轮与timer](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)、[中央状态](completion/20261109-prod-db-scope/README.md)。 其他数据均不自动备份：VM/OS、测试库、Redis/Rabbit、Nexus、Penpot、NAS、Ops、CF及发布私钥排除。旧11来宾全机jobdisabled、whole-VM规则组退役，原19,747,582,801 bytes全机档和21回退档保留、不自动删除；旧CF档只准PVE。新`dell_prod_db_backup_*`三条db-only规则已原生校验/SIGHUP加载，原Prom身份与既有三告警名/Lark接收对象不变，无testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。仅同机逻辑恢复点，未恢复/无独立灾备或RPO保证；不迁移、不合并Nexus、不启Java、无Mac外部探针。
- OW完整规则只留本地，本轮不触/不上传；禁止push local-only分支或push --all。
- fish9guest+3模板的历史安装保持默认Bash；NAS为家用媒体和游戏文件库，不是正式唯一备份目标。

## 验收集合

| 集合 | 当前解释 |
| --- | --- |
| [原38项](acceptance.json) | 26历史passed/12future/manual pending，不强改状态；旧五服务E2E是历史 |
| [清理记录](cleanup/acceptance.json) | 原9项历史passed保留；Nexus合并pending且本轮用户延期 |
| 6项REC严格恢复 | 硬件/数据/网络/监控有部分11/08证据，冷备/回退未做；均保留pending，不扩签、不作为本轮基础恢复额外门禁 |
| 11/08运行核查 | 上轮恢复记录保留，未做全量内容、账号、SMB、MCP或通知闭环重测 |
| [11/09新范围](completion/20261109-prod-db-scope/README.md) | 正式DB/Nacos首轮3301B、timer启用与三规则加载通过；旧全机阶段已停用，恢复/独立DR不扩签 |

## 原12项延期条件

| 用例 | 原完整用例仍缺什么 |
| --- | --- |
| ACC-NET-003 | 新公网域名/Cloudflare账户侧路由与HTTPS；本期不扩签外网 |
| ACC-DATA-002 | 原Mac Nacos全量业务配置/Derby迁移，本轮用户不迁移 |
| ACC-DATA-003 | 选定真实异步业务的消费者重投、幂等与死信 |
| ACC-JAVA-002 | 业务上线授权及多实例ID并发；当前不部署Java业务 |
| ACC-JAVA-003 | 定时/Outbox并发业务与受控副作用；不外发真实金融/通知 |
| ACC-JAVA-004 | WS与多实例共享文件；旧单测试节点持久结果仅历史 |
| ACC-PEN-002 | 公网HTTPS与真实SMTP；本次未扩大外部配置 |
| ACC-NAS-003 | 真实电视/播放器4K HDR、字幕音轨及持续播放 |
| ACC-NAS-004 | 真实PS4/PS5目标格式/工具传输；本次未读取样本内容重验 |
| ACC-NAS-005 | 已批准业务负载/SLO与真实混合负载 |
| ACC-BAK-001 | 仅正式DB/Nacos逻辑备份03:30+GFS已启用；其他数据不自动备份，长期独立目的地/连续周期仍不等于已验 |
| ACC-BAK-002 | 获批RPO/RTO、独立恢复硬件与完整灾备实演 |

11/07 02:35完整验收、02:44:29最后PVE操作与UEFI0058/B1事故保留为历史，11/08基础恢复和11/09fresh审计/本机备份补齐分别记录。机内监控与T630同故障域，不承诺整机故障独立外部通知；用户不需要的Mac探针不再出现在后续恢复项目中。
