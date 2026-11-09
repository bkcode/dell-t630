# 共享资源NFS独立原生验收

时间：2026-11-10T00:16:05.558203+08:00 至 2026-11-10T00:16:18.513024+08:00（Asia/Shanghai）。当前结果：**passed**。既有严格hostkey/info访问280/230/240；仅写一个新nonce合成目录及240本次新增挂载单元的负测。完整元数据见[native-acceptance.json](native-acceptance.json)。

## 实际通过

- server280 `/srv/resources`实际ext4 UUID`57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b`，root:2980/2770；exports仅19.40/19.45、fsid0/mountpoint/sync/root_squash。内核版本`-3 +4 -4.0 +4.1 -4.2`、manage-gids=n。数据容量105089261568B，采样空闲105070362624B。
- 两client `/mnt/resources`实际NFS源19.80:/、nfs4/vers4.1/TCP/hard/sec=sys及nodev/nosuid/noexec，systemd autofs+NFS合法栈，最终guard均exit0。automount enabled/active，mount static/active；finger仍UID999/GID989并含附组2980。
- 使用已定义的UMask0002，以230 finger mkdir-exclusive创建本次nonce目录与文件；实际目录999:2980/2770、文件660。240读取原字节、追加并创建第二文件，230再读取一致并删除240文件。只访问本次合成内容。
- 两客户端UID0清空附属组后尝试在本次目录创建独立root probe，均errno13拒绝，未产生意外文件；未通过chmod或all_squash/no_root_squash绕过。
- 240只停止mnt-resources.automount/mount：findmnt无真实挂载，guard exit1，finger写底目录errno13。底目录root:root0555、dev/ino/mtime/ctime均保持，无根盘回落写。随后恢复automount和真mount，guard0，原enabled标志保持。
- 全部本次fixture（marker、两文件与nonce目录）已精确清理；没有保留资源文件或改NFS服务。三机SSH/QGA/exporter/networkd/resolved及server NFS/mountd/firewall进程/启动身份前后相等，Java进程两机始终0，failed units为空。

## 原artifact与保护范围

240 `/mnt/dell-artifacts`精确findmnt在前后都无active行，挂载状态相同；没有读取其目录内容或写入，不把这个元数据比较声称为逐字完整性重验。未PVE写、重启机器/NFS服务、启动Java或发送通知。资源仍不纳正式数据库自动备份。

## 首次失败保留

[native-first-attempt.json](native-first-attempt.json)及[说明](native-first-attempt.md)完整保留failed：第一runner以umask0022创建后在权限metadata断言停止，没有进入跨机或240停挂载；createdflag清理后保护状态正常。首轮缺具体文件mode，因此不伪称独立证明其根因。经主AI批准，使用新nonce和已定义UMask0002重验；仅修fixture runner，不改服务/权限，也未复用首轮目录。

## 通过结论的限制

两client同finger UID999；本次证明组继承、mode及跨机共享动作，不等于应用/数据库元数据共享或跨环境独立授权。没有用户上传数据迁移、HTTP图片、Java业务、负载SLO或资源数据备份/恢复验收。server280重启持久性由主AI另做，本次已fixture全清并明确释放后才允许其重启。
