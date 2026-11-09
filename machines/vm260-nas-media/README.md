> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# VM260 · nas-media

## 本轮只读状态与备份归属

14:43:07媒体工具采样：原2TiB数据UUID/ext4与OMV/SMB/Jellyfin单元、原镜像/容器健康保持，原健康GET通过；本轮未写共享、读媒体内容或播放，不签真实TV/PS/转码。 证据：[本机分项审计](../../completion/20261109/media-audit.json)。

本机VM/OS及应用数据不纳入现行自动备份；不因旧whole-VM名单而重新启用。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；未restore/无异机DR，不迁移/合并/启Java、无Mac探针。

本目录是每机公开合同与来源索引，**不提供秘密或可直接重放的完整部署包**。source of truth为[plan.json](../../plan.json)；11月7日02:35为历史综合基线、UEFI0058为历史事故；用户确认内存处理/诊断通过，11月9日按本页新证据fresh复核，未重验全部应用内容。

## 职责与实际合同

家庭影院及PS4/PS5游戏文件保存/整理/传输；不作为正式业务备份，也不承诺主机从NAS直接运行游戏。

- 实际资源：4 vCPU / 4 GiB；管理/服务地址 `192.168.19.60`，vmbr19、/24、GW/DNS19.1。
- 数据盘：2048 GiB / store；`/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a`；UUID `5b19837c-128c-498a-b79d-563db810c34a`。
- 启停登记：order50、up30s/down120s；延时不代替健康。
- Docker：Engine29.9.3 / Compose5.7.0，该角色driver `overlayfs`。这是角色specific已验配置，不能拿其它角色/模板profile盲套。

## unit / Compose与依赖

- `dell-nas-jellyfin.service`；运行Compose路径：`/opt/dell/nas/compose.yaml`。
- `openmediavault-engined.service, nginx.service`。
- `smbd.service`。

- 专用2TiB原ext4 UUID，挂载由OMV登记，PVE H730/store仍由宿主管理，不能重复挂块盘。
- Jellyfin media仅RO，config/cache在该专盘；无games/incoming挂载；原UID/GID2000。
- ens18原MAC/IPv6策略与key-only SSH；root禁登录；SMB三share用户名/读写/guest保持。

## 维护与安全

- 4vCPU/4GiB为DirectPlay试运行预算，未配置或验收硬件转码/全套影音自动化。
- 本地子网/SMB hostsallow保留19/21/127并加入受信VPN10.66.66/24；JF RemoteAccess=false/UPnPfalse。
- 直接XML变更须先核无播放/转码，官方SMB Salt也须看客户端/锁；不能强杀真实家庭流。
- 真实TV/console/4K HDR/字幕/GPU与并发SLO未签；只有合成客户端协议和原文件字节证据。
- 11月9日已fresh复核基础状态；新的变更仍须在当前范围内核实，F1本身不代表修复。PVE写/VMID/IP/数据盘归属由root统一，严格SSH/ub管理，不关闭hostkey检查、不复制私钥。
- 目录不含任何.env、secrets、Webhook或key；只引用公开合同和历史证据。CF备份只PVE、发布私钥只220，不能wholebackup220或把private打包提交Git。
- 日常流程见[人工操作手册](../../19-manual-operations.md)与[访问入口](../../12-service-access-and-operations.md)；只读[本机config.json](config.json)与[config-sources.json](config-sources.json)核对，不盲重跑初始化器。

## 配置来源与限制

本目录没有configs快照。某些仓库infra准备文件仍含旧10.63地址或旧默认值，索引已标historical-evidence，不能视作现役完整配置。只有path存在和SHA可复核，不等于当前guest文件逐字相等；源文件与guest的逐字一致性未由索引SHA证明，后续维护仍须fresh核。pending-candidate仅未来方案，不能冒作active。

- [plan.json](../../plan.json) · `current-contract`：当前资源/地址/数据卷合同唯一来源；基础运行状态已在11月9日分项复验；不代表全部应用数据/认证通过。
- [11-live-handoff.md](../../11-live-handoff.md) · `current-contract`：当前不迁移范围、11月9日证据入口及历史UEFI0058时间线。
- [12-service-access-and-operations.md](../../12-service-access-and-operations.md) · `current-contract`：当前19网入口及凭据保管规则。
- [19-manual-operations.md](../../19-manual-operations.md) · `current-contract`：人工启停、硬件门禁、克隆、备份与受控恢复。
- [cleanup/final-live-check.json](../../cleanup/final-live-check.json) · `historical-evidence`：2026-11-07 02:35综合验收快照，不代表当前在线。
- [network19/services-media/nas-smb-post-cutover-verification.json](../../network19/services-media/nas-smb-post-cutover-verification.json) · `historical-evidence`：19.60三share真实权限矩阵、原fixture SHA和JF只读挂载。
- [network19/services-media/nas-jellyfin-post-cutover-verification.json](../../network19/services-media/nas-jellyfin-post-cutover-verification.json) · `historical-evidence`：原影片static SHA/DirectPlay profile与原身份读回，非真实TV验收。
- [network19/wireguard/media/apply-result.json](../../network19/wireguard/media/apply-result.json) · `historical-evidence`：仅追加VPN10/24到三share/JF本地识别，权限/身份/UUID保持。
- [network19/wireguard/media/README.md](../../network19/wireguard/media/README.md) · `current-contract`：VPN来源识别范围与必要restart/客户端保护约束。
- [infra/nas/check-data-mount.py](../../infra/nas/check-data-mount.py) · `current-contract`：专盘UUID/容量/非根盘fail-closed规则，不能用来初始化磁盘。
- [infra/nas/compose.yaml](../../infra/nas/compose.yaml) · `historical-evidence`：公开容器结构参考，需要现役受控env，非完整可直接部署快照。
