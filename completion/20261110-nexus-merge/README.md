# Nexus合并至发布机220

更新：2026-11-10，Asia/Shanghai。用户已明确恢复合并与移除独立artifact-service，覆盖早前暂缓范围。根任务管理者独占服务器写与最终验收。

当前执行已完成源221停服关机、受保护PVE冷备验证，以及220正常停机/6CPU8GiB/旧ISO配置卸载/原Nexus盘唯一移交和服务alias31交接。目标内容/身份/网络/监控和受控重启均验证通过，随后已退役221；原生回执保留失败与修复记录。

目标220保留primary19.30和原构建卷，新增同NIC服务alias19.31和原Nexus100GiB卷。12来宾/3模板、45CPU87GiB、15targets是完成后合同。Nexus入口继续http://192.168.19.31:8081/，管理SSH用19.30及220自身host key。业务发布关闭，旧受限链fenced，Java业务不启。MCP私有设置和key不复制/重生成。

- [架构与责任](../../17-publish-artifact-consolidation.md)
- [日常操作与故障处理](usage-manual.md)
- [监控最小候选及8项本地纯验证](monitoring-candidates/README.md)
- 最终验收以本目录后续真实acceptance.json及原生回执为准；本README不代替证据。

13项源配置与prepared私有CAS保持。原数据盘上的GET-only全量基线为12仓库、7hosted、50components、1347assets；内容/身份差异需在服务器受保护环境比较，不将真实凭据或私有摘要写Git。源PVE冷备2,400,054,202字节且SHA/zstd/VMA通过，归档仅PVE，不能导出Mac。

这不是通用一键安装。一次性迁移脚本与nonce/journal只用于本次记录，禁止重放。原49GAV/234主件及先前备份不覆盖新鲜基线，自动备份仍只正式MySQL/Nacos。

## 已取得的分项回执

- [全量内容与身份比较](baseline-compared.json)：12repos/7hosted/50components/1347资产内容哈希全部通过，仓库配置/users/roles/EULA一致；只忽略GET产生的1172个lastDownloaded运行时间戳，不忽略其它内容字段。
- [磁盘与网络交接](handover-result.json)：2206CPU8GiB、原build卷保持、原Nexus卷唯一归220，31桥归属转220MAC，ISO只卸配置，宿主L3/NAT未改。
- [Ops目标](ops-targets-applied.json)：11node→10，保留280，移除221 SD/Lark角色，无Prom重启/接收方秘密变更或测试通知。
- [导航清单](navigation-updated.json)：HTTP/UI保持，13项，去FileBrowser并更新Nexus归属；不代表原deploy源码已提交推送。

最终221退役与整体后检已完成，详见本目录原生回执。

最终退役回执确认：VM221配置与原OS盘已删除，活Nexus数据盘在220保持；原221恢复点为仅PVE保留的2,400,054,202字节冷备，不再声称保留源OS盘。见[退役回执](retirement-result.json)。

## 最终运行验证

[220受控重启后检](publisher-post-reboot.json)确认双UUID/双IP/source30，原发布器配置/MCPkey/unit/guard与213f源码、六main工作树保持，四原生服务active/enabled、Nexus两容器healthy；原reader/publisher/group读取通过、匿名资产401、EULA保持。

[最终监控](monitoring-final.json)15/15UP，220七项服务及NexusHTTP、280五项服务全UP，无FileBrowser指标。重启后[全量GET验证](baseline-verify.json)完成1390次请求、1347资产内容一致；访问时间差异独立记录，不掩盖其它字段。旧221恢复点仅PVE冷档，不是已执行的恢复演练。

## 独立仓库写入验收

在现有专用dell-acceptance库，仅创建本次随机坐标的微小POM并读回原字节，随后精确核对repository/GAV/资产路径后删除该组件，原组件及资产集合恢复。未对业务仓库上传或删除，也不是Java构建/业务发布。立即search查询存在异步可见性，清理改用有界components列表；资产API的前导斜线按现有规范归一化后仍严格校验路径，未绕过身份门禁。详见[写入与清理回执](baseline-write-canary.json)和[原资产集合核验](baseline-canary-cleanup.json)；本次intent/journal只在220受保护路径，禁止重跑脚本再上传。
