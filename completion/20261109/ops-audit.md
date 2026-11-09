# Ops270 fresh审计与备份缺项 · 2026-11-09

采集：2026-11-09 **14:44:45+08:00**，经既有可信target严格SSH访问VM270/192.168.19.70。本次只读systemd、挂载、容器显式状态、timer/cron元数据、textfile数值，以及本机Prometheus/Alertmanager/Grafana GET；没有部署、备份、恢复、通知、服务重启或QA。完整数据与失败尝试见[JSON](ops-audit.json)。

## fresh基础健康

| 检查 | 实际观察 |
| --- | --- |
| 数据盘 | `/srv/dell-data` ext4/rw，UUID `01b1f302-27be-4fbd-b4af-b8e782d85dea`匹配 |
| 系统/服务 | systemrunning，failed units为空；Ops监督、Docker/containerd、exporter及healthtimer正常 |
| 容器 | 原4个Ops容器均running/healthy，restart_count0、OOMfalse |
| readiness | Prometheus、Alertmanager、Grafana原本机路径均HTTP200 |
| 监控 | 15/15targets UP，无down；Prometheus与AM当前alerts均为空 |
| 新鲜度 | 目标最大scrape age约29.4秒；10guest health collection age约22.5–85.9秒，success均1；10个textfile scrape_error均0；PVE采集约74.5秒新 |
| 内部Lark | 原unit active；没有读配置/LoadCredential内容，没有发送测试，不据unit状态宣称新一轮端到端通知验收 |

以上是采样观察，不新增业务SLO或RPO/RTO数值承诺。Mac外部探针用户明确不需要，本次未访问、启动或添加未来任务。未读取或保存OW完整规则。

## 已安装备份/保留调度的实际范围

270的service/timer元数据只找到 `dpkg-db-backup.service/timer`，timer enabled/active，最后触发成功；它备份系统包数据库，**不是Grafana/应用数据备份**。全部timer名称中没有应用backup/retention/prune任务。

cron.d只有e2scrub_all，daily为apt-compat/dpkg/man-db等系统条目，没有观察到应用备份或保留策略job。`crontab`程序未安装（exit127），因此不将它误写为“crontab -l成功且空”；系统cron文件只在内存计数，未记录命令正文。这里仅审计270，不据此断言PVE或其他来宾都没有备份任务。

`/root/dell-app-backups`存在且700，已知应用backup安装路径未见；没有打开目录中的归档或数据库、没有统计备份内容/验证最近恢复。因此旧目录存在不是当前备份健康证明。

## 本地工具能否直接补齐

- `infra/backup/application-backup.py`是200/201按组件手动生成本地敏感快照的工具，动态调用目标已部署的挂载/IP门禁，没有timer、保留或跨设备导出。MySQL无DDL、Redis fork余量及Rabbit稳定拓扑的确认是实际前置，不能用固定确认参数盲接每日timer。失败可能保留私有partial输出，保留策略必须区分成功manifest和失败残留。
- `infra/ops/backup-grafana-acceptance.py`是历史验收工具：包含合成dashboard POST/DELETE、独立恢复容器，并硬编码旧10.63.30.40。不能原样运行或直接设为定时服务。可抽取其SQLite online backup模式，但需独立生产工具、19.70实际合同和无验收写入行为。
- 原文档记录的是初始受控快照/临时Mac副本，不是持续独立调度或已批准保留/RPO/RTO。当前没有确认长期独立目的地；家庭NAS不能代替正式备份，CF仍仅PVE，220禁止含发布私钥的整机备份。

本次只读查看源码，**没有执行以上备份/恢复脚本，也没有修改它们**。

## 可实施的最小补齐建议

1. 在后续明确窗口准备独立Grafana SQLite在线备份工具：限定VM270/19.70/原挂载UUID，root700/600、flock防重入、超时/容量门槛、原子成功manifest与SHA；只读源SQLite，不写dashboard、不启动恢复容器、不替换现役文件。调度/保留/容量需先明确；本机同盘快照只能标本地恢复点，不能称独立备份。
2. 可先准备纯元数据备份观察器：只从允许的成功manifest采“最近成功/年龄/失败类别/容量”等指标，不读取归档正文或秘密，不新发通知测试。需按既有内部指标/告警归属审查，不增加Mac或其它外部通道。
3. 在确认独立目的地、频次和保留后，再接组件级调度与保留：MySQL无DDL约束、Redis实际COW余量/忙检查、Rabbit topology不含消息；保留仅操作owned固定目录及完整成功manifest，拒symlink/越界，有锁和最低副本/空间保护。21份受保护回退档、CF边界和220私钥排除不动。

这三项是方案建议，尚未部署。需要由主AI集中确认的是**长期独立备份目的地、调度/保留策略及其存储预算**；不能从临时Mac备份或NAS用途推断已经确定。当前Ops服务没有发现需要重启/重装的基础缺项。

## 证据限制与失败保留

15UP不等于数据库内容、硬件长期稳定、业务全链或灾备恢复已验。Lark未做本轮firing/resolved验证；不读完整Env/Cmd/healthlog或HTTP业务正文。

初始本机临时脚本不存在的尝试在SSH前停止；随后只读探针因可选命令缺失中断，已保留JSON中的失败attempt，修为缺命令exit127后完成相同采集。没有为修探针安装软件或改服务器，不改写成所有尝试一直成功。
