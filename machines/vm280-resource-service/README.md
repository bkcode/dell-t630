# VM280 · resource-service

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

更新：2026-11-10，Asia/Shanghai。此目录是资源服务合同与公开来源索引，不是完整运行配置导出。**VM280及230/240真NFS/guard、非root跨机读写/删除、root_squash/缺挂载负测已通过；仅280约30秒受控重启，fsync canary持久、两client挂载恢复，未重启running。** 现行资源包含NFS与私有FileBrowser管理HTTPS，不含业务图片HTTP、Java启动、旧文件搬迁或自动备份扩围。

## FileBrowser Quantum管理页面

新增私有管理入口 **https://192.168.19.80:8080/**，仅LAN21/24、WG10.66/24及本机；日常`resources`可浏览/下载/新建上传，delete/edit/override/share/提权直接API已验403；维护`admin`有完整权限，不把日常限制说成它也绝对不能删除。密码只在Mac `dell/private/credentials/filebrowser-management-20261110.json`与guest root `/etc/dell-filebrowser/secrets/login.json`保管，不在文档输出值。首次核[tls.crt](../../completion/20261110-filebrowser/tls.crt)的SHA256指纹后接受/导入；无公网域名、无系统truststore变更。

官方native固定v2.1.4-beta（不是stable），UID2000/GID2980、UMask0002、文件660/目录2770，DB/cache在非共享的`/var/lib/dell-filebrowser`700；初始化marker在root的`/etc/dell-filebrowser/bootstrap.complete`，正常后续启动不再注入初始化口令。自身metadata自动备份关闭，不扩正式DB/Nacos备份；Docker未装，NFS/PVE/路由不改，不Java、不业务图片URL、不迁旧文件。

[原生API/NFS验收](../../completion/20261110-filebrowser/native-acceptance.json)passed且fixture已清；[真实浏览器](../../completion/20261110-filebrowser/browser-acceptance.json)只签登录/列表及观察到href后的96PNG深链渲染，自动点击未导航，未签所有按钮。[只重启新app](../../completion/20261110-filebrowser/service-restart.json)已保持账号、scope和JWT且不再注入初始化口令，NFS/VM/clients未重启；[06:12最终后检](../../completion/20261110-filebrowser/final-postcheck.json)已确认13运行来宾、3停止模板、16targets全UP、资源6服务指标及专属CA HTTPS健康均UP，PVE全forward0；未加Promtarget/receiver或外发测试消息。完整[管理页使用手册](../../completion/20261110-filebrowser/usage-manual.md)含证书指纹、账号、维护/升级与故障步骤；[公开服务包](../../infra/resources/filebrowser/README.md)。

本机资料：[配置合同](config.json)、[配置来源](config-sources.json)、[用户使用手册](../../completion/20261109-resources/usage-manual.md)。主AI维护[plan](../../plan.json)与PVE创建/地址/网络；本目录不自动运行provision、格式化或部署。

| 合同 | 参数 |
| --- | --- |
| VM / hostname / IP | 280 / resource-service / 192.168.19.80 |
| 网络 | vmbr19，GW/DNS19.1；PVE21.22仍管理/L2、hostforward0/noNAT |
| 资源 | 2vCPU/2GiB，系统32GiB（9010全克隆，未缩盘）、独立100GiB数据盘，PVE store |
| 数据盘 | UUID `57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b`，ext4，`/srv/resources`，nodev/nosuid/noexec |
| 导出 | 唯一NFSv4.1、TCP2049、fsid0；client远端为`192.168.19.80:/` |
| 客户端 | 230 19.40与240 19.45，均挂`/mnt/resources`；同一目录不分正式/测试 |
| 权限 | server根root:resources 2770＋default ACL组rwX/other0，GID2980；root_squash/sync |
| 管理 | SSH `ub`、既有Mac密钥、严格host key；私钥不复制。后检fish4.0.2、root/ub默认Bash保持；当前10guest＋3模板具备fish基线 |

实际盘初始化见[storage](../../completion/20261109-resources/storage-initialized.json)，只处理新分配100GiB盘，未格式化根盘或其他现役卷。[server installed](../../completion/20261109-resources/server-installed.json)记录NFS激活；同网桥[MAC/IP与peer确认](../../completion/20261109-resources/bridge-confirmed.json)、[DNS A记录](../../completion/20261109-resources/gateway-DNS-applied.json)分别留证。路由/firewall/noNAT未因加DNS重写；本轮DNS文件模式曾导致服务启动失败并已安全恢复，保留[诊断与修复](../../completion/20261109-resources/DNS-recovery.json)，不隐藏中间故障。

## 服务与失效门禁

native单元为`srv-resources.mount`、`dell-resources-firewall.service`与`nfs-server.service`；数据mount/fixed UUID及专属输入保护先于NFS。配置在`/etc/dell-resources/`、`/etc/exports.d/dell-resources.exports`和`/etc/nfs.conf.d/90-dell-resources.conf`，公开工具见[infra/resources](../../infra/resources/README.md)。不开放111/20048/UDP2049，服务器NFS只对两个批准client；普通LAN/WG可路由不等于拥有NFS export权限。

两running的finger保持UID999/GID989，仅加resources附属GID2980；不得把server资源组替换成989。客户端hard/automount、真挂载guard和root0555下层用于防止共享失效后写根盘；存在autofs不算NFS已挂好。240原`/mnt/dell-artifacts`保留。任何未来Java挂载依赖另审、另安装，本轮业务不启。

资源文件**未纳入自动备份**，也未迁入旧文件。当前自动任务仅正式VM200/nacos_prod SQL；RAID、同机共享与数据库备份不提供这些文件的恢复保证。Nginx/业务HTTP图片只是未启用候选，不存在已交付的业务图片或上传URL；FileBrowser受认证管理HTTPS是另一用途。

## 验收与日常入口

[独立native验收](../../completion/20261109-resources/native-acceptance.json)已通过两client真实NFS/guard、finger跨机创建/读写/删除、root_squash、240缺挂载拒写下层与恢复；fixture已清。首轮失败及清理[原记录](../../completion/20261109-resources/native-first-attempt.json)保留；重测提前应用已批准umask0002，未修改服务来追过，不把首轮未捕获的文件mode原因说成已独立证明。

[受控重启](../../completion/20261109-resources/reboot-exercise.json)只操作280，约30秒，bootID改变、fsync共享canary保留且两client恢复；PVE bootID和两running OS保持，未签断电/客户端OS重启。最后[00:20只读后检](../../completion/20261109-resources/final-postcheck.json)status=passed：13来宾运行、3模板停、16/16targetsUP、资源5服务指标UP、UUID/权限正确、fish4.0.2与Bash保持；PVE全部forward0、非client peer2049负测保持拒绝。长期SLO/真实数据恢复仍未签。容量/权限/健康、精确fixture清理、故障恢复和新增running步骤见[使用手册](../../completion/20261109-resources/usage-manual.md)，全机操作见[人工手册](../../19-manual-operations.md)。

模板未来可预装nfs-common与disabled挂载候选，clone后必须登记真实IP与组并获exports/bridge许可才激活；本次未修改9001/9010/9011模板。

应用未接入：Finger `file.upload.path=/mnt/resources`是待另审建议，不是已改配置；HTTPdomain/公开图片URL未搭。Puyu images仍在MySQL内经权限接口下载，未随NFS自动迁文件、改Nacos或启Java。客户端findmnt允许systemd-1 autofs＋唯一真实nfs4，检查可使用`-t nfs4`，不应因合法stack误判失败。

[实际启动配置](../../completion/20261109-resources/PVE-startup-configured.json)确认280 onboot=1、order35/up20/down120；初建时onboot0是待验阶段，后已明确启用。资源server先于230/240客户端，完整新13角色主机重启序列未另行重演。
