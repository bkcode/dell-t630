> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 19网段媒体服务实际交接

更新：2026-11-06T10:11:06.565157+00:00

三role均已完成新网活动配置提交、原监督启动与语义验收。OS/NIC/路由/OW由root执行，本子任务只在已明确窗口操作所属应用。没有改Git/镜像/卷/UUID或轮换身份。主机/客户端SSH私钥没有复制，凭据值与私有hash未输出。

| VM | 新入口 | 原事务nonce | 应用状态 |
| --- | --- | --- | --- |
| 221 | http://192.168.19.31:8081 | 1058e856fcab43f7ae53816d9659f214 | 原unit与2容器healthy；49GAV/234primary/35metadata/1076checksums、EULA/新身份/角色/只读消费均保持 |
| 250 | http://192.168.19.50:9001 | 05da6bff4609467e8524af42463c78b1 | notify与11healthy；Gitff clean、原3设计data/revn/stats、全部973资产路径SHA（含原971）保持；MCP/既有job/新origin/DNS通过 |
| 260 | OMV http://192.168.19.60:80 / JF :8096 / SMB :445 | 1c97ce46e0e8494aa67f95768a818753 | 原Jellyfin unit healthy；3共享矩阵、原fixture SHA、身份/只读边界、原影片新LAN读取与DirectPlay profile通过 |

## 精确配置与数据边界

Penpot改动7个已审活动文件，公开URI/bind/worker owner运维入口/admin307检查/旧新IP门禁/锁哈希成组；dnsproxy仅192.168.19.1:53，再由GW→OW21.1，内部172.30.250.53不变。worker/import仍内部frontend:8080，不添加旧host泛化alias，不重建Git或镜像。原3设计/原971媒体均保持，当前全部973还含2份已归因官方导出缓存。MCP仅新身份只读上下文/匿名数据拒绝，不做设计写；既有async job25f2efd7-fcca-4d2b-be51-42fb6c8be36d仍completed/同project和file且1文件，不提交import或retry。

Nexus改动4文件，assignment/原fresh marker同步IP但不重建marker，bind和活动验证API origin指新IP。新密码留221，验证硬拒绝非GET；没有重建metadata、写仓库、重接受EULA或请求外部proxy。匿名被拒，reader/publisher原密码认证和本地group读取通过。权限最小性通过实际role定义不变复核，没有再发PUT/DELETE负测。Swagger无独立BaseURL GET，实际hosted download URL随请求origin，无观测到旧host强制跳转；未查询proxy认证。

NAS先由root用官方OMV wired UUID/MAC原对象+Salt改OS（保留IPv6和身份），本子任务只提交.env bind/PublishedURL与JF LocalNetworkSubnets，未改账号或数据。Jellyfin从Mac原生curl新19入口用原admin/viewer认证；已有library/原MP4 SHA相同，PlaybackInfo支持DirectPlay且static原字节匹配，未创建文件/库/用户、未scan/播放事件、未启transcode。真实电视/console/GPU仍未验。

## SMB真实问题与限定修复

初次SMB矩阵未通过，不是用户名空格或密码错误：同guest原root600 auth走127.0.0.1 ls成功，新19地址两用户ACCESS_DENIED。三share各自hostsallow仍有旧40子网；global绑定/hosts.allow/deny为空不能代表share白名单为空。root明确授权后仅通过官方SMB.setShare把：

`192.168.21.0/24 10.63.40.0/24 127.0.0.1`

替换为：

`192.168.21.0/24 192.168.19.0/24 127.0.0.1`

三固定share UUID保持，官方samba Salt生效，其他OMV字段及effective valid users/read list/write list/read only/guest完全相同，没有ALL/密码轮换/用户组调整。随后同guest旧auth原字节在新IP三share矩阵真实passed：writer put/read/rename/delete，reader create/modify/rename/delete均拒绝，匿名拒绝；原3个1MiB fixture SHA保持；JF挂载仍只有media RO，无games/incoming。只新增独立nonce的合成测试对象并保留审计。

## 失败与恢复记录

- NAS第一次preflight是准备门禁误将已用overlayfs假设为overlay2，旧两份审计与当前元数据都证明NAS原本overlayfs。只把迁移工具改为按role精确pin（221/250 overlay2、260 overlayfs），没有转换后端；原失败保留。
- Nexus端口改绑时第一次waiter在容器临时缺名时退出，配置已正确提交、服务随后实际healthy；只在active unit幂等start完成journal，无restart或重commit。公开工具补为原600秒内缺帧重试，必须完整容器数/healthy/相同image/身份才ready；18本地fixture通过。
- 250重复quiesce是root/子AI交接时序重叠，root那次safe拒绝，无额外配置/OS动作；唯一有效停止由本子任务已批准调用完成，随后root仅切OS。失败记录不改写passed。
- 首次SMB unconfirmed/真实ACCESS_DENIED分类和精确白名单修复记录全部保留，不以更换凭据掩盖。

## 回滚与后续操作

以下是回滚参考，不是已执行回滚。每个私有事务在该guest `/root/dell-network19-media/<VM>/<nonce>`，root700、old/new/journal600，不下载到Mac。应用部分按PLAN：新网停止原unit→rollback-files（全old/new SHA/CAS且拒绝第三方改动）→root旧NIC/IP/route→rollback-start；已quiesced但尚未commit的失败也有安全还原入口。数据/身份/Git不回滚。

**NAS追加SMB网络策略需一并回滚**：新网且Jellyfin已停止、SMB客户端已drain时，root先核私有`smb-network-policy.json`，通过官方setter还原3旧参数+Salt，再按原应用文件/OMV OS旧payload恢复。本目录nas-smb-allowlist-rollback.py仅是未执行参考，必须先root审阅/上传，默认不运行。它只还原已保存旧CIDR，不改认证/其他权限。若PVE旧桥已退场，root还须恢复所需旧网络接入，不能认为应用文件回滚等同网络回滚。

当前三个应用无需再quiesce或初始化。新app地址已交root用于Ops目标/collector/ACL/CI映射与旧桥退出。Mac外部探针仍按用户决定停用。暂无HTTPS/domain/真实设备/正式业务SLO/RPO新承诺。

## 主要证据

- standby-stage-result.json（最初stage+原文件/PID/image/身份保护），stage-nonces.json。
- nexus-commit-start-result.json、nexus-post-cutover-verification.json、nexus-baseurl-observation.json。
- penpot-commit-start-result.json、penpot-post-cutover-verification.json。
- nas-commit-start-result.json、nas-jellyfin-post-cutover-verification.json、nas-smb-network-policy-preflight.json、nas-smb-network-policy-result.json、nas-smb-post-cutover-verification.json。
- 初始失败/分类：standby-stage-attempt1.json、NAS-standby-guard-diagnostic.json、NAS-daemon-metadata.json、nexus-commit-diagnosis.json、nas-smb-post-cutover-attempt1-unconfirmed.json、nas-smb-readonly-classification.json。
