# CT100 cf-tunnel

**仅元数据合同，硬件暂停、当前在线未知。** 最后02:35运行清单包含CT100；直接cloudflared注册/localready证据更早，来源索引保留各自时点。不能把注册/ready2连接写成未知公网源站业务已经全通。

本机资料：[配置合同](config.json)、[安全来源索引](config-sources.json)。最后合同为1CPU/512MiB、Debian LXC、rootfs local-lvm4GiB、19.5/24 vmbr19、GW/DNS19.1。旧21.150/DHCP是历史，不是现在目标。源站remote ingress配置没有从retained日志获得，不能猜新域名或生成假的ingressYAML。

## 身份与备份边界

- cloudflared沿用原身份/含凭据服务字节；19网迁移曾受控重启CT，因此不宣称原PID全程不变。NAT/隧道出口策略由[VM190](../vm190-network-gateway/README.md)和PVE L2 ACL拥有。
- **不读取/复制token，不复制unit正文/ExecStart参数，不导出CF归档到Mac。** 远程token管理模式只按既有安全元数据标注；不假设存在某个token文件路径。
- PVE侧受保护备份目录提示为`/root/dell-bootstrap/protected-cf-backups/`，目录0700、归档0600。这里只链接[元数据](../../evidence/implementation/cf-local-backup-metadata.json)，没有payload；同主机备份不是独立灾备，旧档未恢复实演。
- 不假定容器装了ub SSH；将来授权恢复后由PVE管理console/pct路径核查，不能为方便导出凭据。fish与Mac外部probe本期排除/停用。

当前不运行上述任何核查。硬件诊断/用户恢复指令优先，见[交接](../../11-live-handoff.md)和[人工手册](../../19-manual-operations.md)。原Nexus合并已获维护许可但尚未执行，与此CT身份/元数据整理无关。
