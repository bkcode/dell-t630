> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# NAS：受信VPN10.66.66.0/24网络识别范围

当前状态：**NAS配置已提交、运行态及原19来源功能回归通过。真实VPN10源访问由主AI在网关/L2策略生效后单独批测，本子任务不以19源测试冒充VPN实测。**

用户在知悉全服务访问范围后明确授权整个`10.66.66.0/24`。本目录仅负责NAS260应用层来源识别，不修改网关/PVE/NAT、服务器IP或其它role。原业务认证和guest角色隔离不变。

## 精确变更

三个固定共享media/games/incoming的hostsallow从：

`192.168.21.0/24 192.168.19.0/24 127.0.0.1`

仅追加为：

`192.168.21.0/24 192.168.19.0/24 127.0.0.1 10.66.66.0/24`

通过现役OMV8.6的官方SMB.setShare和samba Salt部署；所有其它OMV share字段以及effective valid users/read list/write list/read only/guest/hosts deny保持。没有ALL、匿名放行、账号/密码/组或业务权限变更。

Jellyfin LocalNetworkSubnets保留原`192.168.19.0/24`、`192.168.21.0/24`、`127.0.0.0/8`、`172.18.0.1/32`，仅新增`10.66.66.0/24`。EnableRemoteAccess=false、EnableUPnP=false，XML所有其它现存字节保持；原UID/GID2000与0644权限保持。没有更改PublishedServerUrl、监听端口、卷或地址。

## 客户端保护与实际操作

提交前通过现有admin的受控GET检查，JF正在播放/暂停播放/转码均0；SMB sessions/tcons/open_files均0。提交阶段再次从NAS直接核对这些状态，无流或锁才继续。没有停止任何真实家庭播放。

直接修改网络XML采用原dell-nas-jellyfin.service一次受控stop/start，运行态API重新读回新数组及两项false。官方Samba Salt的service.running/watch实际使smbd MainPID改变，即发生了SMB服务重启，不声称纯reload；之前无客户端/锁。Docker服务MainPID与VM bootID保持，没有重启Docker/VM，也未重启其它role。

原NAS数据UUID`5b19837c-128c-498a-b79d-563db810c34a`、shadow/SSH公钥/根数据guard字节和原合成fixture哈希保持。Jellyfin相同镜像与原监督恢复healthy。

## 备份、失败与边界

实际事务nonce：`d4f269ae477f479b9d240ff52b560812`。原XML/候选XML、完整旧新SMB参数及私有hash只在NAS `/root/dell-wireguard-media/<nonce>`，目录700、文件600。原stage拒绝记录保留：首次6cc04b116eef49028728806579a0578e在network.xml纯转换阶段因关闭标签与最后子项同行而安全拒绝，没有创建stage目录或停止服务。8个fixture验证兼容该实际格式后，仅CAS更新公开纯转换器，未放宽身份/UUID/旧白名单/无客户端等门禁，再以新nonce完成。

原19源回归使用同NAS已有root600 auth文件认证读取三共享原1MiB文件，writer/reader SHA均相同，匿名仍拒绝；不发送share写请求。Mac原生curl同admin/viewer读取原library、既有MP4静态流SHA与DirectPlay profile均通过，没有新建用户/库/影片，没有scan、播放事件或转码请求。没有输出密码、token或私有凭据hash，认证不进入argv/env或普通日志。

最初broad网络范围曾被自动审核拒绝，NAS当时仅只读核对、没有提交；本次在用户获知范围后新的明确授权下执行，不复用被拒绝动作的审批。源记录限本目录；旧迁移/源码与私有原身份未改。

如需撤回，仅由主AI另给窗口：先检查无播放/SMB锁，核对该私有journal的当前字段仍是本次new值，使用其old SMB参数经官方setter恢复、原XML备份原UID/mode原子恢复后原JF unit启动。不能用整个旧19迁移事务盲回滚，否则会同时撤销无关地址迁移。回滚未演练，不宣称已完成灾备/RPO。

## 证据

- preflight.json：原生现役白名单、模型字段、单位、UUID。
- client-preflight.json：播放/转码/SMB客户端0及Salt服务watch来源。
- stage-diagnosis.json、attempt1-stage-rejected.json：首次安全拒绝和业务PID未变。
- serializer-CAS-review.json：纯字节兼容补丁旧新公开SHA。
- apply-result.json：官方配置提交、运行态读回、无Docker/VM重启、保护条件。
- readback-result.json：原19源三共享原文件/匿名拒绝回归。
- nas-jellyfin-post-cutover-verification.json：原NAS身份、原影片字节及DirectPlay profile。
- test_changes.py：8项本地合成格式/字段保护测试；不读取真实凭据。
