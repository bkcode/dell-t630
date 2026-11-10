> 更新：2026-11-09（Asia/Shanghai）。本轮基础fresh审计已复核；当日实时收尾状态统一见[11月9日交付记录](../../completion/20261109-prod-db-scope/README.md)。本页仅本地同步带时点证据，不执行服务器操作；不迁移数据、不合并Nexus、不启动Java业务、不升级Penpot，不需要Mac外部探针。

# CT100 cf-tunnel

Git来源唯一入口：**[GIT-REPOSITORIES.md](GIT-REPOSITORIES.md)**（来源/计划与已部署状态分开；不表示本机已clone或已分发key）。

## 本轮只读状态与备份归属

15:26:47只读采样：cloudflared本机ready HTTP200、readyConnections=2；本轮不读取token/unit正文，不做公网域名、账户侧origin或外网VPN E2E。CT仍19.5，原身份保留。 证据：[本机分项审计](../../completion/20261109/network-audit.json)。

本CT与CF文件不纳入现行自动备份。原whole-VM阶段CF历史档仅留PVE，禁止导出；不读取token。 现行仅正式DB/Nacos逻辑SQL导出（非VM snapshot），PVE落点`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600；新未列白名单数据库拒绝告警、需更新。03:30/GFS最近3＋每日7＋每周4，首轮3301B与timer见[新回执](../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)，实际监控/收尾统一见[新中央入口](../../completion/20261109-prod-db-scope/README.md)。旧11来宾job已disabled、原19,747,582,801B档与21回退档保留不自动删；仅[该3301B Nacos小档已在VM210临时隔离恢复](../../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针。

**仅配置合同与安全元数据；本轮11月9日直接ready200/连接2已复核。** 11月7日02:35运行清单及更早注册记录继续保留历史时点。不能把注册/ready连接写成未知公网源站业务已经全通。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)。最后合同为1CPU/512MiB、Debian LXC、rootfs local-lvm4GiB、19.5/24 vmbr19、GW/DNS19.1。旧21.150/DHCP是历史，不是现在目标。源站remote ingress配置没有从retained日志获得，不能猜新域名或生成假的ingressYAML。

## 身份与备份边界

- cloudflared沿用原身份/含凭据服务字节；19网迁移曾受控重启CT，因此不宣称原PID全程不变。NAT/隧道出口策略由[VM190](../vm190-network-gateway/README.md)和PVE L2 ACL拥有。
- **不读取/复制token，不复制unit正文/ExecStart参数，不导出CF归档到Mac。** 远程token管理模式只按既有安全元数据标注；不假设存在某个token文件路径。
- 历史PVE侧受保护备份目录提示为`/root/dell-bootstrap/protected-cf-backups/`，目录0700、归档0600。这里只链接[元数据](../../evidence/implementation/cf-local-backup-metadata.json)，没有payload；同主机备份不是独立灾备，旧档未恢复实演。
- 不假定容器装了ub SSH；按已授权范围通过PVE管理console/pct核查，不能为方便导出凭据。CT100不装fish；Mac外部probe用户不需要，不列现行或后续任务。

本轮已按用户继续搭建范围fresh核查指定元数据，未读取凭据；后续范围仍以[交接](../../11-live-handoff.md)和[人工手册](../../19-manual-operations.md)。原Nexus合并历史许可保留，但本轮用户明确暂不迁移，与此CT检查无关。
