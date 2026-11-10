# VM280 · resource-service

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

更新：2026-11-10，Asia/Shanghai。此目录是资源服务合同与公开来源索引，不是完整运行配置导出。**现行资源仅保留NFS；FileBrowser网页服务已按用户确认方案停用并masked，TCP/UDP8080无监听。** 230/240继续共用同一资源根，不拆正式/测试，不启业务图片HTTP、Java或自动备份扩围。

## 当前仅NFS，FileBrowser已退休

22:49完成受控停用，22:51只读后检通过：`dell-filebrowser.service`与`dell-filebrowser-firewall.service`均inactive/masked、取消自启，原现役unit移至本机受保护回退目录；独立`inet dell_filebrowser_input`表已撤。原NFS配置、exports、版本、输入规则、目录权限和受保护服务PID/启动身份保持，未重启NFS或客户端。健康配置仅保留原5项资源角色服务，FileBrowser unit与`filebrowser-http-health`检查已移除。

原FileBrowser state、账号/JWT等凭据保留原保护路径，不读秘密内容、不重置、不导出；不是可继续登录的网页服务。回退材料仅在280 `/root/dell-filebrowser-retired-20261110` root700/文件600，不能因旧文档或安装器存在而自动解除mask或重跑初始化。[停用回执](../../completion/20261110-nfs-only/retirement-result.json)、[最终后检](../../completion/20261110-nfs-only/final-postcheck.json)与[新NFS操作手册](../../completion/20261110-nfs-only/usage-manual.md)是当前入口。

本轮新建唯一server canary后，两client以finger经真实NFSv4.1只读读回并检查权限，随后精确清理；没有client写入或已有业务文件读取。先前双client写入/root_squash/缺挂载及仅280重启是[原NFS验收](../../completion/20261109-resources/README.md)的独立历史范围。FileBrowser的[首次HTTPS交付](../../completion/20261110-filebrowser/README.md)与[后续HTTP交付](../../evidence/internal-http-20261110/README.md)均仅历史，不作当前服务可用证明。

本机资料：[配置合同](config.json)、[配置来源](config-sources.json)、[当前用户使用手册](../../completion/20261110-nfs-only/usage-manual.md)。主AI维护[plan](../../plan.json)与PVE创建/地址/网络；本目录不自动运行provision、格式化或部署。

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

资源文件**未纳入自动备份**，也未迁入旧文件。当前自动任务仅正式VM200/nacos_prod SQL；RAID、同机共享与数据库备份不提供这些文件的恢复保证。Nginx/业务HTTP图片只是未启用候选，不存在已交付的业务图片或上传URL；FileBrowser原管理HTTP已退休，当前没有Web文件入口。

## 验收与日常入口

[独立native验收](../../completion/20261109-resources/native-acceptance.json)已通过两client真实NFS/guard、finger跨机创建/读写/删除、root_squash、240缺挂载拒写下层与恢复；fixture已清。首轮失败及清理[原记录](../../completion/20261109-resources/native-first-attempt.json)保留；重测提前应用已批准umask0002，未修改服务来追过，不把首轮未捕获的文件mode原因说成已独立证明。

[受控重启](../../completion/20261109-resources/reboot-exercise.json)只操作280，约30秒，bootID改变、fsync共享canary保留且两client恢复；PVE bootID和两running OS保持，未签断电/客户端OS重启。历史[00:20只读后检](../../completion/20261109-resources/final-postcheck.json)status=passed：13来宾运行、3模板停、16/16targetsUP、资源5服务指标UP、UUID/权限正确、fish4.0.2与Bash保持；PVE全部forward0、非client peer2049负测保持拒绝。长期SLO/真实数据恢复仍未签。当前状态与使用步骤见[新NFS手册](../../completion/20261110-nfs-only/usage-manual.md)，原容量/权限/精确fixture与新增running的历史实施细节见[初始手册](../../completion/20261109-resources/usage-manual.md)，全机操作见[人工手册](../../19-manual-operations.md)。

模板未来可预装nfs-common与disabled挂载候选，clone后必须登记真实IP与组并获exports/bridge许可才激活；本次未修改9001/9010/9011模板。

应用未接入：Finger `file.upload.path=/mnt/resources`是待另审建议，不是已改配置；HTTPdomain/公开图片URL未搭。Puyu images仍在MySQL内经权限接口下载，未随NFS自动迁文件、改Nacos或启Java。客户端findmnt允许systemd-1 autofs＋唯一真实nfs4，检查可使用`-t nfs4`，不应因合法stack误判失败。

[实际启动配置](../../completion/20261109-resources/PVE-startup-configured.json)确认280 onboot=1、order35/up20/down120；初建时onboot0是待验阶段，后已明确启用。资源server先于230/240客户端，完整新13角色主机重启序列未另行重演。
