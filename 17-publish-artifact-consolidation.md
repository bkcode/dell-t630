# publish-service：发布与Nexus制品仓库

更新：2026-11-10，Asia/Shanghai。用户已明确恢复执行Nexus合并并移除独立artifact-service，覆盖11月8日暂缓范围。本轮执行记录集中在[合并交付目录](completion/20261110-nexus-merge/README.md)。220数据/身份/网络/监控及受控重启核验通过，源221已退役；最终范围以本次原生回执为准。

## 同机职责与地址

```text
VM220 publish-service · 6 vCPU / 8 GiB
├─ 192.168.19.30：管理SSH / 服务导航HTTP9080 / node exporter9100
├─ /opt/deploy-public：Puyu发布工具，MCP仅127.0.0.1:18765
│  CLI prod→main、dev→dev；MCP仅dev，真实发布关闭
├─ /srv/dell-build：原100GiB构建卷 UUID16dc6067-56ef-4687-a314-edc6421f9ed4
└─ 同NIC alias192.168.19.31：Nexus HTTP8081
   原100GiB卷 /srv/nexus UUID239dc45a-b1f3-408b-a8ef-7afa77b52204
   Docker Compose，由dell-nexus.service监督
```

两地址属于同一VM；31是服务兼容入口，不是第二台服务器或网关。既有Maven/Gradle URL、Nexus账号/EULA/仓库身份保留。管理SSH继续使用220自己的host key和primary30；不复制221 host key，不以旧dell-vm221信任别名连接新220。OS/PVE名称均保持publish-service。

Nexus与构建卷分别挂载，禁止把Nexus数据库或blob写进构建盘、容器可写层或根盘。原盘唯一移交，不能让221与220同时挂同一盘读写或同时拥有31。

## 当前边界和预算

最终目标为12个来宾（11VM＋1LXC）、3份停止模板，配置合计45vCPU/87GiB，监控10node＋5Ops＝15targets。220原4CPU4GiB与221原2CPU4GiB合并为6CPU8GiB，总预算不变，不声称额外释放4GiB。停止模板不持续占用声明资源。NFS资源280和其node目标保留。

首期构建建议单并发，构建与Nexus竞争同一VM；本次迁移不签并行构建性能或业务SLO。Nexus原镜像ID、应用限制和数据身份保持，不升级或重新初始化，不重建仓库。

原受限发布链保持fenced，Java业务不构建/启动。deploy-public私有YAML、服务器生成MCP key、仓库DeployKey和构建盘UUID守卫必须保持；MCP仍loopback、dev-only、deploy disabled。六个业务/公共库仓库仍main，上游dev全缺，新dev预检应按设计拒绝。旧五服务dev/main成功仅作历史，不作为当前dev就绪证明。

## 验证与监控

本次源全量基线为12仓库、7hosted、50components、1347assets，GET-only读取；原49GAV/234主件是历史子集，不能覆盖新鲜全量。凭据与私有基线只留受保护服务器文件，不纳普通文档/Git。

源221停止后完成PVE冷备，归档2,400,054,202字节，SHA/zstd/VMA验证通过；仅保留PVE。随后正常停220，设6CPU8GiB，先卸载占用scsi2的旧安装ISO配置（不删ISO文件），再唯一转移原Nexus盘至220 scsi2，原build卷不动。Nexus内容/身份/网络/监控、220原有服务与受控重启通过后已执行退役。

监控220继续只抓30:9100，删除221物理节点，不能再以31假造第二节点。220原SSH/QGA/exporter/导航4项检查保留，追加Docker/Nexus/MCP为7项；只有Nexus HTTP探测使用本机alias31，认证MCP仅监测unit。实际运行监控文件与canonical源存在历史差异，按fresh逐文件CAS更新，不用旧源整体重装覆盖。候选及本地纯验证见[monitoring-candidates](completion/20261110-nexus-merge/monitoring-candidates/README.md)。

## 备份、退役与维护

自动备份仍只覆盖正式MySQL/Nacos白名单库，本次Nexus冷备是单次迁移回退点，不新增自动备份。220原发布私钥只留220，不读取/导出，不对220执行整机备份/快照导出。CF备份仍只PVE。

221已在最终核验后从现役roles、机器索引、Git表、启停和监控移除；逐机历史资料已移到archive/machines-vm221-artifact-service-20261110，不能据归档重建第二个31所有者。最终回执确认221配置和原OS盘已删除，活Nexus盘在220保留，受保护冷备是原221剩余恢复点。回退计划不是已验证灾备，不签RPO/RTO或独立DR。

日常检查与故障处理见[本次操作手册](completion/20261110-nexus-merge/usage-manual.md)、[全局人工手册](19-manual-operations.md)。旧[cleanup计划](cleanup/nexus/PLAN.md)及[resume清单](cleanup/nexus/resume-preflight.md)仅保存过程，禁止重放stage/mount/commit/start或fresh-init。

最终退役回执确认：VM221配置与原OS盘已删除，活Nexus数据盘在220保持；原221恢复点为仅PVE保留的2,400,054,202字节冷备，不再声称保留源OS盘。见[退役回执](completion/20261110-nexus-merge/retirement-result.json)。
