# 当前访问入口与日常操作

2026-11-07，Asia/Shanghai。**服务器因UEFI0058内存错误暂停；下列为配置入口和最后验收结果，不表示当前可达。** Nexus合并已授权但未执行，仍独立221。应用直接访问真实19地址；PVE21.22只用于宿主管理，原应用DNAT端口已关闭。详见[当前交付](15-network19-delivery.md)与[新网络验收](network19/audit/network19-acceptance.md)。

| 服务 | 当前入口 | 范围 |
| --- | --- | --- |
| PVE | https://192.168.21.22:8006/ | 管理SSH22保留 |
| 虚拟网关190 | WAN192.168.21.23 / LAN192.168.19.1 | 路由、19DNS/DHCP，无NAT |
| Penpot | http://192.168.19.50:9001/ | Git定制版、3设计/973媒体、11服务 |
| Nexus | http://192.168.19.31:8081/ | 原49GAV/234primary内容保持 |
| OMV | http://192.168.19.60/ | 家庭NAS管理 |
| Jellyfin | http://192.168.19.60:8096/ | 媒体库、DirectPlay协议已验 |
| SMB | `smb://192.168.19.60/media`、`/games`、`/incoming` | writer/reader分离，匿名拒绝；使用固定IP连接 |
| Grafana | http://192.168.19.70:3000/ | 真实内网入口，无需旧13000隧道 |
| Prometheus / Alertmanager | 192.168.19.70:9090 / :9093 | 仅批准管理来源，不公开 |
| Java业务 | **停用** | 测试五服务无进程/自启，正式无业务应用 |
| Java验收模板 | PVE VMID9011 `tpl-java-acceptance` | 唯一验收模板，无应用/业务配置/秘密 |

HTTP入口是用户同意的LAN阶段；公网域名/HTTPS/SMTP尚未配置。跨子网的发现广播不作为已验能力，电视/播放器请手动填写19.60。NAS用于文件保存/整理/传输，不承诺主机直接从NAS运行游戏。

| VMID | 角色 | IP |
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

## 凭据位置


| 对象 | 受保护位置 |
| --- | --- |
| 数据组件 | Mac `private/data/bundles/<角色>/secrets/` 与各guest受控安装包 |
| Java合成管理员/测试client | Mac `private/java/secrets/`；测试账号FNTEST0001 |
| Nexus新admin/reader/test publisher | Mac `private/nexus/new-secrets/` 与221 `/root/dell-nexus-secrets/` |
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

2026-11-07 02:35最后验收时10node+5Ops目标共15/15UP；当前在线状态未复验。本机textfile采集业务范围已移除Java五HTTP检查，catalog/installer已配套减为10节点。服务器内部Lark active，172.18内部链与凭据保持；未发送新的验收消息。Mac外部探针继续停用，整机故障无法由机内监控保证外发。

正式业务数据未从开发环境导入。初始OS/应用备份与测试迁移证据保留，Mac只是临时独立副本目的地；长期调度/容量/保留与真实恢复RPO/RTO尚未签。CF归档仅PVE，发布私钥仅220，NAS家庭媒体不作正式业务备份。物理电视/PS主机、4K/HDR/字幕/硬件转码和生产并发仍待实际验收。


## 2026-11-07 WireGuard受信网段

用户明确全服务授权后，10.66.66.0/24已获准访问19/24全部有效IPv4端口及网关21.23/19.1；NAS的SMB/Jellyfin来源识别同步追加，账号/读写权限不变。外网Mac Air批量入口复测已确认全部正常。无需SNAT，OpenWrt各peer仍独立/32，PVE21.22不恢复转发。见[WireGuard全服务访问](16-wireguard-access.md)。
