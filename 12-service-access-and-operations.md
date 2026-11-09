# 当前访问入口与日常操作

2026-11-09，Asia/Shanghai。**自然重启后基础服务fresh复验；继续完成搭建并仅备正式数据库/Nacos配置，不迁移数据。** Nexus仍独立221，Mac外部探针不需要。当日状态见[11月9日交付记录](completion/20261109-prod-db-scope/README.md)，[11月8日恢复](recovery/20261108/README.md)保留历史。应用直接访问真实19地址；PVE21.22只用于宿主管理，原应用DNAT端口已关闭。详见[当前交付](15-network19-delivery.md)与[新网络验收](network19/audit/network19-acceptance.md)。

| 服务 | 当前入口 | 范围 |
| --- | --- | --- |
| PVE | https://192.168.21.22:8006/ | 管理SSH22保留 |
| 虚拟网关190 | WAN192.168.21.23 / LAN192.168.19.1 | 路由、19DNS/DHCP，无NAT |
| Penpot | http://192.168.19.50:9001/ | Git定制版、3设计/973媒体、11服务 |
| 测试Nacos | http://192.168.19.20:8848/nacos/ | 同实例新空域finger-test-empty，需登录并显式选namespace；旧域保留 |
| Nexus | http://192.168.19.31:8081/ | 目前归221；合并目标归220同NIC服务alias，URL不改 |
| OMV | http://192.168.19.60/ | 家庭NAS管理 |
| Jellyfin | http://192.168.19.60:8096/ | 媒体库、DirectPlay协议已验 |
| SMB | `smb://192.168.19.60/media`、`/games`、`/incoming` | writer/reader分离，匿名拒绝；使用固定IP连接 |
| Grafana | http://192.168.19.70:3000/ | 真实内网入口，无需旧13000隧道 |
| Prometheus / Alertmanager | 192.168.19.70:9090 / :9093 | 仅批准管理来源，不公开 |
| Java业务 | **停用** | 测试五服务无进程/自启，正式无业务应用 |
| Java验收模板 | PVE VMID9011 `tpl-java-acceptance` | 唯一验收模板，无应用/业务配置/秘密 |

HTTP入口是用户同意的LAN阶段；公网域名/HTTPS/SMTP尚未配置。跨子网的发现广播不作为已验能力，电视/播放器请手动填写19.60。NAS用于文件保存/整理/传输，不承诺主机直接从NAS运行游戏。

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

## 测试Nacos空namespace已搭好

同一VM210/`192.168.19.20:8848`测试Nacos内新增 **`finger-test-empty`**，namespace ID `23836f2e-9553-5948-84cd-431b2f241bd6`。20:27验收时配置0、跨组注册服务0，见[空namespace回执](completion/20261109-test-env/empty-namespace-created.json)。这是新增逻辑隔离域，**没有清空整个Nacos实例、旧namespace或MySQL数据库**；旧namespace `10719261-2641-590a-b821-c8484ca955ac` 的7项配置、历史计数9及原3个业务schema（表数3/10/6）保持，原4容器帧未变。

沿用既有测试应用账号及role，仅增加新域`:*:*`的rw授权，已核新域缺配置404、无关域403；没有重置密码/账号role关系、迁移、业务DDL/配置发布、Java启动或服务重启。基础bundle `.env`和health仍指旧namespace以保兼容，不为了“空”改其namespace值；未来业务若另获准使用新域必须显式选新ID，当前不改源码profile。

用户名只按受保护的`private/data/bundles/test-data/.env`中`NACOS_CLIENT_USER`查看，密码引用`private/data/bundles/test-data/secrets/nacos-client-password`；guest对应`/opt/dell/data/test-data/.env`和`secrets/nacos-client-password`。仅说明保管位置，不读取/展示值、不通过命令参数或截图传播；原管理账号继续用原受控位置。

## 凭据位置


| 对象 | 受保护位置 |
| --- | --- |
| 数据组件 | Mac `private/data/bundles/<角色>/secrets/` 与各guest受控安装包 |
| 测试Nacos新空域沿用账号 | 用户名查test-data受保护`.env`的`NACOS_CLIENT_USER`；密码查`private/data/bundles/test-data/secrets/nacos-client-password`，不在文档列值 |
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

2026-11-09 [Ops审计](completion/20261109/ops-audit.json)再次复验10node+5Ops共15/15UP，Prom/AM无活动告警。本机textfile采集业务范围已移除Java五HTTP检查，catalog/installer已配套减为10节点。服务器内部Lark active，172.18内部链与凭据保持；未发送新的验收消息。Mac外部探针明确不需要，已移出当前和后续工作，整机故障无法由机内监控保证外发。

正式业务数据未从开发环境导入。**现行自动备份仅VM200正式数据库/Nacos配置。** 当前唯一非系统库`nacos_prod`，12张BASE TABLE全InnoDB；正式业务schema尚未创建，新增库不在显式白名单则拒绝告警并要求更新。首轮逻辑SQL gzip 3,301 bytes通过CRC/传输SHA、DDL锁释放及guest暂存清理，service退出0、timer已enabled，下一次2026-11-10 03:30（Asia/Shanghai）；GFS最近3/每日7/每周4。PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups`，目录root700/文件600，不经Mac，见[新首轮与timer](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)、[中央状态](completion/20261109-prod-db-scope/README.md)。

其他数据均不自动备份：VM/OS、测试库、Redis/Rabbit、Nexus、Penpot、NAS、Ops、CF及发布私钥排除。旧11来宾全机jobdisabled、whole-VM规则组退役，原19,747,582,801 bytes全机档和21回退档保留、不自动删除；旧CF档只准PVE。新`dell_prod_db_backup_*`三条db-only规则已原生校验/SIGHUP加载，原Prom身份与既有三告警名/Lark接收对象不变，无testsend，见[规则回执](completion/20261109-prod-db-scope/alerts-installed.json)。仅同机逻辑恢复点，仅下述小档已临时隔离恢复，仍无完整业务恢复/独立灾备或RPO保证；不迁移、不合并Nexus、不启Java、无Mac外部探针。 真实电视/PS/4K/HDR/转码与生产并发仍待实际验收。


**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

## 2026-11-07 WireGuard受信网段

用户明确全服务授权后，10.66.66.0/24已获准访问19/24全部有效IPv4端口及网关21.23/19.1；NAS的SMB/Jellyfin来源识别同步追加，账号/读写权限不变。外网Mac Air批量入口复测已确认全部正常。无需SNAT，OpenWrt各peer仍独立/32，PVE21.22不恢复转发。见[WireGuard全服务访问](16-wireguard-access.md)。
