> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 家庭NAS与影音服务

状态：**NAS260软件已部署并完成合成客户端验收；真实电视/播放器、PS4/PS5和硬件转码独立待验。** 当前结果见 [runtime-status.json](runtime-status.json)，私有原始证据和凭据元数据在 `dell/private/nas`。本子任务只操作NAS260，未写PVE或其他来宾，未更改源Mac影音项目。

## 当前部署

| 项目 | 当前实测 |
| --- | --- |
| 来宾 | VM260，nas-media，Debian13 AMD64，4 vCPU/4 GiB |
| 私网 | 10.63.40.10/24，网关10.63.40.1，DNS1.1.1.1 |
| 实际稳定接口 | ens18；OMV UI对象与netplan均已对齐，保留原NIC/MAC |
| NAS | OpenMediaVault8.6.0-1 |
| 影音 | Jellyfin12.4.0，官方AMD64 immutable digest |
| 容器 | Docker29.9.3、Compose5.7.0 |
| 数据盘 | 独立drive-scsi1，2199023255552 bytes，GPT+ext4，OMV登记挂载 |
| 根盘 | drive-scsi0，原根UUID保留，未格式化 |
| 运行内容 | OMV+SMB+Jellyfin；没有MoviePilot/qBittorrent/WireGuard或旧完整影音unit |

LAN入口由主AI管理：

- OMV：<http://192.168.21.22:9080>
- Jellyfin：<http://192.168.21.22:8096>
- SMB：`//192.168.21.22/media`、`//192.168.21.22/games`、`//192.168.21.22/incoming`

主AI和本任务均用原生curl验证HTTP200，主AI原生nc验证445可达。证据是 [LAN-entrypoint-cli-probes.json](../../evidence/implementation/LAN-entrypoint-cli-probes.json)。Python在该Mac执行面连SSH22也返回errno65，而系统ssh/nc/curl正常；这不是宿主DNAT故障，不因此改规则。

## 存储与账户

安装前再次核对by-id、序列drive-scsi1、2TiB容量、无分区/FS/签名、未挂载并排除根盘，然后只通过真实OMV FileSystemMgmt.create创建ext4。该盘安装时恰好是/dev/sda，根盘是/dev/sdb1，**不可按sd字母猜测设备**。PVE的H730/store仍由PVE管理。

- 数据UUID：`5b19837c-128c-498a-b79d-563db810c34a`
- 挂载点：`/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a`
- 原根UUID：`2d5cddec-8777-4aef-9b8d-1d7093e60982`
- 三目录/SMB服务/权限均通过已安装OMV8.6 RPC登记，fstab和Samba由OMV Salt管理。
- `naswriter`读写、`nasreader`只读；拒匿名、最低SMB2；验收客户端实际请求SMB3。
- Jellyfin管理员`delladmin`和非管理员`dellviewer`已强密码登录验证。

密码值不在文档、argv、URL、镜像或普通日志中，目录700、文件600，仅经stdin/API请求体传递。路径和用户名见私有 `credentials-metadata.json`。没有复制客户端私钥。

Jellyfin媒体只读挂载，config/cache在经过UUID核验的数据盘上。systemd要求挂载就绪，Docker restart=no，防止容器绕过挂载顺序启动。`family`目录默认私有，没有自动共享个人资料。

## 已执行验收

| 检查 | 实际结果 |
| --- | --- |
| OMV强密码 | 本机HTTP登录通过，重启后再通过；初装默认口令窗口由主AI临时关闭9080并在验证后恢复 |
| SSH | ub严格hostkey+指定私钥重连、sudo/_ssh和公钥摘要保持；OMV默认弱化项已通过SSH.get/set恢复key-only，禁root登录 |
| 三共享 | 合成1MiB文件writer写、reader读和SHA256一致；reader写拒绝、匿名拒绝 |
| 媒体 | network=none临时容器生成原创5秒640×360 H264/AAC MP4，无影片/游戏下载 |
| Jellyfin | 禁互联网provider的验收库索引；viewer DirectPlay支持true，静态流字节SHA一致，实际合成会话没有TranscodingInfo |
| 持久化 | 两次仅NAS重启；bootID变化，原根/媒体UUID、合成文件、账号和服务配置保持，全部服务自启动 |
| 网络 | 同IP/GW/DNS；ens18持久规则与OMV UI一致，NIC/MAC未改 |
| IPv6 | 仅ens18 disable_ipv6=1、accept_ra/autoconf=0；lo及全局disable保持0，无全局IPv6地址，旧eth0项已消除 |
| 系统健康 | systemctl is-system-running=running，failed清单为空 |
| 指标 | exporter按主AI统一启用，仅监听10.63.40.10:9100；本任务未自行改宿主监控规则 |

合成文件摘要：

```text
SMB 1MiB fixture:
fbbab289f7f94b25736c58be46a994c441fd02552cc6022352e3d86d2fab7c83

原创H264/AAC MP4:
5b2499415295d67552b400a8d197fe11c61e73801b8c281247de04567d312905
```

这里验证的是合成客户端协议和原始字节传输，不能扩张为真实电视或控制台全部功能通过。

## 安装中已解决的差异

1. 官方主仓库/公钥入口HTTP503，TUNA403。改用[上游官方安装器列出的GitHub Pages镜像](https://github.com/openmediavault/openmediavault/blob/master/install.sh)和[官方packages仓库公钥](https://github.com/openmediavault/packages/blob/master/archive.key)，保持APT签名验证，没有跳过签名或运行不明联网脚本。来源/hash/指纹留在私有证据。
2. OMV8.6的netplan populate处理原静态cloud-init YAML失败。先备份，通过官方interfaces importer导入完全相同IPv4/GW/DNS，再由OMV networkd生成按MAC匹配配置；主AIQGA待命并实际往返验证。
3. OMV系统变更后重启接口从eth0呈现为ens18。按实际稳定名称修正OMV对象和仅该接口的IPv6规则，重启再次验证，不改PVE虚拟网卡或MAC。
4. 当前镜像实际是Jellyfin12.4.0，要求cache可用空间至少2GiB；原256MiB tmpfs不满足。现改为数据盘cache，不增加RAM。
5. 首次Jellyfin用户初始化需先GET Startup/User触发InitializeAsync，再POST设置强账户；实际源码和OpenAPI已核对。token在Authorization header，旧header混用不再采用。
6. Docker发布流量在本机可呈现为实际bridge网关172.18.0.1。LAN子网额外加入该网关/32，不扩大为外网访问，仍EnableRemoteAccess=false。

ext4内建quota accounting已在mount时自动on，而默认外部quotaon重复激活报EEXIST。本需求没有每用户配额，因此通过OMV FsTab移除usrquota/grpquota外部激活选项、重生成真实依赖；没有mask unit或关闭内建accounting，未配置用户限额。媒体UUID与SMB/Jellyfin保持，当前systemd running且failed清单为空。

原始失败证据保留，不把中间失败覆盖成一直通过。可选ECDSA hostkey缺失警告仍记录；既有受信ED25519不变，严格SSH正常，未生成或轮换hostkey。

## 脚本

| 文件 | 用途 |
| --- | --- |
| install-omv.sh | guest-only，先check再apply；支持经核实官方公钥文件/仓库入口 |
| adopt-omv-network.sh | 相同地址的网络接管，备份后官方populate+networkd；实际接口需参数化 |
| omv-rpc-stdin.php / omv_client.py | root-only真实OMV接口，秘密stdin，结果脱敏 |
| check-data-mount.py | UUID、容量、独立挂载检查，不允许回落系统盘 |
| compose.yaml / deploy-jellyfin.sh | Jellyfin-only，固定digest、非root、限CPU/RAM、数据盘cache、挂载依赖 |
| initialize-jellyfin.py | 真实12.4接口初始化，先loopback完成强账户，再LAN |
| verify-smb.py | 合成文件与三共享权限验证，认证文件600 |
| verify-jellyfin.py | 原创fixture、无网络metadata、DirectPlay协议/hash/无转码会话验证 |
| remote.py | 仅NAS260，使用主AI已验证info，不调用trust_guest改known_hosts |

API参数依据已安装8.6模型，不复制旧裸机README的假设。新对象UUID标识从实际Environment获取，不能把全零UUID当新对象。更新软件版本时先核对实际模型和参数，再重放脚本。

## 独立待验与后续

- 真实电视/播放器：4K/HDR、音轨、字幕、画面和操作体验；需要实际终端联测。
- 真实PS4/PS5：工具、文件格式、终端传输；当前仅文件库，不承诺直接从NAS运行游戏。
- GPU硬转码：未配置、未声称通过。
- 家庭大流量与正式业务的并发SLO：正式负载基线尚未确定，未执行无界负载。
- 独立备份/恢复与外发告警：由主AI另阶段处理；家庭NAS不是正式业务备份目标。CF备份只留PVE，不因本任务导出。

## NAS002 补充权限验收

三个共享分别实测 reader 创建、覆盖修改、重命名、删除均返回 NT_STATUS_ACCESS_DENIED，且每一步后原 nonce 样本 SHA256 保持；writer 对另外新建 nonce 文件的重命名、删除成功。删除拒绝时 smbclient 可返回0，因此按 SMB 状态码和实际文件未变判断，不只看进程码。样本保留，真实媒体/游戏文件未触碰。

Jellyfin 实际 mount 集合仅 config/cache 读写与 media 只读；运行用户2000:2000，容器中 media 可读不可写、games/incoming 路径不存在，未挂载其源目录。脱敏证据为 `evidence/implementation/nas002-detailed-permissions.json`。
