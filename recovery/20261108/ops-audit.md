# Ops270恢复只读审计 · 2026-11-08

两次采样：20:18:15、20:19:38（Asia/Shanghai）。沿既有QGA信任的strict SSH target访问VM270/192.168.19.70，未更改known_hosts、服务器文件或服务。完整非秘密元数据见[JSON](ops-audit.json)。本轮不迁移Nexus、不启Java业务。

## 最新观察

- `/srv/dell-data`实挂ext4/rw，UUID `01b1f302-27be-4fbd-b4af-b8e782d85dea`匹配；Docker仍`/var/lib/docker`、overlay2、29.9.3。
- `systemctl is-system-running=running`，failed units为空。`dell-ops.service`、Docker/containerd、node exporter及健康timer正常；健康oneshot完成Result=success后inactive/dead是预期，不是故障。
- 原4个Ops容器全部running/healthy，restart_count=0、OOMKilled=false，持久目录仍位于专盘；两次采样的PID/启动时间没有变动。未读取Env、Cmd、健康日志或容器日志。
- Prometheus、Alertmanager readiness与Grafana健康GET均HTTP200。第二次**15/15注册targets UP、down为空**，Prometheus alerts与Alertmanager alerts均为空。
- 本机health textfile collection_success=1、age约4.4秒；PVE textfile age约27.5秒。timer正常更新，未手动触发collector。
- `dell-lark-notify.service`active/running、NRestarts0、DynamicUser=yes、ProtectSystem=strict、NoNewPrivileges=yes；未读取LoadCredential内容，未调用发送测试或访问第三方。原内部告警链自身可能按既有配置处理启动事件，本审计未触发新测试。

## 启动队列与限制

首轮13/15UP，240(.45:9100)及260(.60:9100)为no-route；220(.30)已UP但前一评估周期的exporter告警仍存在。第二次自然启动完成后，三者告警均消失且15UP；没有为这些瞬间状态重启或改网络。首轮真实down/告警保存在JSON，不追改成一直全绿。

当前没有发现Ops270需要补齐的重启或配置项。15UP只证明现有注册监控目标可抓取，不代替所有应用/数据身份、硬件长期稳定或灾备验收。没有读取PVE启动队列；自然恢复已足以解释本次两处瞬时down，其他应用结论由对应审计补充。

内部Lark进程运行不等于本boot重新完成firing/resolved端到端验收；本次禁止测试外发，不做该声明。Mac外部探针保持用户停用状态，本审计未访问或启动它，也不宣称整机故障独立外部告警已具备。

## 本地forwarding修复脚本只读复审

另静态审查`restore-management-forwarding.py`，没有执行。生成helper/hook的`sh -n`均exit0；IFACE仅vmbr0门禁及固定helper exec符合if-up hook形式，既有unit证据为After network.target/Before pve-guests.service。3个owned新文件O_EXCL、interfaces/routes/ACL前后保护和无network reload/unitrestart边界符合拟定范围，未见范围阻断。

建议失败分支保存脱敏receipt，并对每个回退动作分别try/finally，避免一个unlink或proc写失败中断余项恢复。该建议已交协调者；语法检查不能替代将来ifupdown运行时序或重启持久性实测。本审计没有扩大任何宿主操作授权。
