# VM220 · publish-service

## 2026-11-11 Puyu空制品仓库与配置对接

已在既有Nexus新增puyu-releases（RELEASE/ALLOW_ONCE）、puyu-snapshots（SNAPSHOT/ALLOW）与puyu-public（仅前两者），以及专用reader/publisher身份。权限fixture正负测通过后已清，当前0components/0assets；原旧库/管理员/账号/EULA/密码不改，Nexus未重启，不复制Finger/imnull制品。

[发布机应用](../../completion/20261111-puyu-nexus/publisher-applied.json)和[连接后检](../../completion/20261111-puyu-nexus/connected-postcheck.json)保存本次实际验证。新group是Puyu内部制品入口，不代理全部公共依赖；项目既有MavenCentral/pluginPortal/JitPack直连保持，Nexus内部网络不放开。两新口令仅VM220受保护600来源，已接入ub600/ignored统一config.local.yaml；artifact_exec.py配置层适配器源码main/2d8f541已推送，Mac75项回归＋固定/bin/bash专项10项通过；发布机已同步同SHA并通过Linux75项回归、离线show/check和固定build.bash ls只列项目，连接后检已通过：真实私有YAML身份认证、MCP协议/匿名401/Origin403与限制保持，未提交新任务；这是配置完成，不是业务构建就绪。它仅CLI显式入口，注入原NEXUS_*环境给固定build.bash，不改build/common/Go/Java、不自动接MCP。

当前主库仍main、dev远端缺失；1.0.0等release版本不能自动发SNAPSHOT，私有gradle-conventions/公共库尚需后续供应。今天不改版本/建分支、不构建或发布业务，MCP仍dev-only/真实deploy关，旧链fenced、原MCPkey不变。[交付状态](../../completion/20261111-puyu-nexus/README.md)、[操作说明](../../completion/20261111-puyu-nexus/usage-manual.md)。

更新：2026-11-10，Asia/Shanghai。用户已明确恢复Nexus合并与独立221退役；目标220已完成内容/身份/网络/监控和受控重启核验，221已移除，见[本次回执](../../completion/20261110-nexus-merge/README.md)。旧4CPU4GiB/唯一30/standby描述仅历史，不作为当前维护入口。

Git来源：[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)；配置合同：[config.json](config.json)，来源元数据：[config-sources.json](config-sources.json)。来源SHA不是完整现场导出，目录不包含秘密或可一键恢复包。

## 资源与两套职责

- 6vCPU/8GiB，primary192.168.19.30；同NIC service alias192.168.19.31，vmbr19/24，GW/DNS19.1。OS/PVE名称publish-service，管理仍用220自己的host key，不沿用旧dell-vm221别名。
- 原build卷100GiB/store，/srv/dell-build，UUID16dc6067-56ef-4687-a314-edc6421f9ed4。
- 原Nexus卷100GiB/store唯一移入scsi2，/srv/nexus，UUID239dc45a-b1f3-408b-a8ef-7afa77b52204。旧scsi2安装ISO只卸CDROM配置、文件保留；不format、不双挂RW、不递归chown树。
- Nexus HTTP19.31:8081，原账号/权限/EULA/仓库内容保持。Docker Engine29.9.3/Compose5.7.0/classic-overlay2角色合同，原两镜像ID不升级。
- 服务导航HTTP19.30:9080，匿名只读、无顶部栏/全宽，不承担SSO/部署/目标健康检查；本次清单13项，FileBrowser移除、Nexus描述归220。PVE/iDRAC内置HTTPS不强改。

## Puyu工具与MCP

/opt/deploy-public来自bkcode/deploy-public main/2d8f541，Linux75测试通过；此前213f/65项仅旧模式阶段记录。MCP以ub运行、仅127.0.0.1:18765，服务puyu-deploy-mcp.service；原ignored YAML/APIkey/DeployKeys和buildUUID守卫保持，不导出、重生成或覆盖私有配置。

CLI prod/main、dev/dev，MCP仅dev、prod覆盖拒绝。六业务/公共库main已克隆且仍main，远程dev均缺，新dev预检failed是预期保护；不自动代建/推分支或fallback main。旧五服务dev/main成功仅历史。prod SSH目标未配置、真实部署关闭，原forced-chainfenced，任何环境不构建/启动Java业务。

[MCP/模式证据](../../evidence/deploy-public-modes-20261110/README.md)、[工具操作说明](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)。合并前MCP PID30260与导航18640是历史进程号，VM重启后不可据此要求PID相同；应核unit/命令/配置保持与新回执。

## 服务与监控

- dell-nexus.service：Docker Compose、/srv/nexus真实UUID守卫和挂载依赖。
- docker.service，原Nexus两个容器健康必须独立核实；不将publisher加入docker组。
- puyu-deploy-mcp.service：原生Python、ub/loopback、APIkey认证、部署关闭。
- dell-service-directory.service与专属firewall.service：原生Python/UID2001，只读导航；本次只更换公开清单release，移除FileBrowser入口并将Nexus描述归220，HTTP/UI保持。
- prometheus-node-exporter.service：只绑定19.30:9100；dell-guest-health.timer采集。
- /usr/local/bin/dell-publish：manual-only/fenced，不真实发布。

220原SSH/QGA/exporter/导航4个健康检查保留，加Docker/Nexus/MCP共7个；只有Nexus HTTP探测本机alias31，MCP认证接口不作为HTTP健康项。31不另建node，移221后总10node+5Ops=15（含资源280），最终15UP见本次回执。

## 备份、维护和限制

本机不纳自动备份，发布私钥只220，禁止读取/复制/导出或wholebackup/snapshot220。单次原221迁移冷备2,400,054,202字节仅PVE root保护保存，SHA/zstd/VMA通过，不导出Mac、不自动删除。自动备份仍只正式MySQL/Nacos，不纳Nexus或构建缓存。

迁移脚本不是幂等安装器，禁止重放旧stage/mount/commit/start或fresh-init。partial安装应先看journal与manifest，不能删路径绕guard。日常检查与故障处理见[本次操作手册](../../completion/20261110-nexus-merge/usage-manual.md)、[全局人工手册](../../19-manual-operations.md)、[访问入口](../../12-service-access-and-operations.md)。回退未演练，独立DR/RPO/RTO与并发构建性能未签。

原始准备记录仍保留：[Docker准备](../../cleanup/nexus/docker220-prepare-result.json)、[standby读回](../../cleanup/nexus/preparation-readback.json)、[原媒体审计](../../completion/20261109/media-audit.json)；它们不是当前无Nexus/无alias31的证明。[17架构](../../17-publish-artifact-consolidation.md)定义当前责任。

最终退役回执确认：VM221配置与原OS盘已删除，活Nexus数据盘在220保持；原221恢复点为仅PVE保留的2,400,054,202字节冷备，不再声称保留源OS盘。见[退役回执](../../completion/20261110-nexus-merge/retirement-result.json)。
