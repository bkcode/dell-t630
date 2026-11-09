> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# CT100 cf-tunnel

## 本轮只读状态与备份归属

15:26:47只读采样：cloudflared本机ready HTTP200、readyConnections=2；本轮不读取token/unit正文，不做公网域名、账户侧origin或外网VPN E2E。CT仍19.5，原身份保留。 证据：[本机分项审计](../../completion/20261109/network-audit.json)。

本机纳入[PVE本机自动备份](../../infra/backup/pve-local/README.md)的固定11来宾白名单；220始终排除，CF档只留PVE。 计划为03:30、最近3份＋每日7点＋每周4点，私有目录root700、归档/日志/状态600，旧21回退档保留。**首轮最终结果、job启用与告警规则后验只以[当日中央入口](../../completion/20261109/README.md)为准，本页不复制进行中状态。** 同机snapshot/crash-consistent不等于DB逻辑/跨VM一致、异机灾备或已恢复；本轮不迁移数据、不恢复覆盖现役。

**仅配置合同与安全元数据；本轮11月9日直接ready200/连接2已复核。** 11月7日02:35运行清单及更早注册记录继续保留历史时点。不能把注册/ready连接写成未知公网源站业务已经全通。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)。最后合同为1CPU/512MiB、Debian LXC、rootfs local-lvm4GiB、19.5/24 vmbr19、GW/DNS19.1。旧21.150/DHCP是历史，不是现在目标。源站remote ingress配置没有从retained日志获得，不能猜新域名或生成假的ingressYAML。

## 身份与备份边界

- cloudflared沿用原身份/含凭据服务字节；19网迁移曾受控重启CT，因此不宣称原PID全程不变。NAT/隧道出口策略由[VM190](../vm190-network-gateway/README.md)和PVE L2 ACL拥有。
- **不读取/复制token，不复制unit正文/ExecStart参数，不导出CF归档到Mac。** 远程token管理模式只按既有安全元数据标注；不假设存在某个token文件路径。
- PVE侧受保护备份目录提示为`/root/dell-bootstrap/protected-cf-backups/`，目录0700、归档0600。这里只链接[元数据](../../evidence/implementation/cf-local-backup-metadata.json)，没有payload；同主机备份不是独立灾备，旧档未恢复实演。
- 不假定容器装了ub SSH；按已授权范围通过PVE管理console/pct核查，不能为方便导出凭据。CT100不装fish；Mac外部probe用户不需要，不列现行或后续任务。

本轮已按用户继续搭建范围fresh核查指定元数据，未读取凭据；后续范围仍以[交接](../../11-live-handoff.md)和[人工手册](../../19-manual-operations.md)。原Nexus合并历史许可保留，但本轮用户明确暂不迁移，与此CT检查无关。
