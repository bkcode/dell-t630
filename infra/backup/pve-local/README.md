# PVE本机自动备份

2026-11-09。用户选择先搭建PVE本机自动备份，独立目的地后续接入。**本机恢复点不等于异机灾备**；源码、数据库内容不因备份而迁移/导入，Nexus221继续独立、220不合并，Java业务保持停用。

**首轮11项已完整验证，原生任务OK/退出0，每日03:30计划已启用，三条规则已原生校验并SIGHUP加载。** 具体回执与边界以[本轮交付记录](../../../completion/20261109/README.md)为准；本页记录方案和维护方法，不把候选文件存在写成已启用。

## 对象、目录与权限

| 项目 | 配置 |
| --- | --- |
| PVE存储 | `dell-local-backup`，只允许backup内容 |
| 存储父挂载 | `/mnt/pve/store`，ext4 UUID `75e5b438-5ff3-4139-83d6-b6a6847aedac` |
| 归档目录 | `/mnt/pve/store/dell-artifacts/scheduled-backups/dump` |
| 原生任务 | `dell-local-nightly`，每日03:30，Asia/Shanghai |
| 对象 | 100、190、200、201、210、221、230、240、250、260、270，共11个 |
| 明确排除 | **220发布机**，禁止整机备份复制发布专用私钥 |
| 保留 | 最近3份、每日7个点、每周4个点，由PVE原生算法组合执行 |
| 模式 | snapshot；不主动stop/restart来宾，QGA/文件系统冻结可能短时影响IO |
| 执行 | 来宾串行，max-workers=1是单VM备份IO并发设置；压缩zstd、2线程、ionice7 |
| 带宽 | 不按虚拟逻辑零块额外限速，避免2TiB稀疏NAS扫描被人为拖成十多小时；后续实际媒体量增长需重估窗口 |
| 空间保护 | 目标挂载UUID、100GiB底线；有旧档时另保守要求2倍旧档大小余量 |
| 文件权限 | 备份根/dump/state均root700，归档/日志与状态root600；原生临时工作父目录root0711 |

CF100归档可能包含隧道凭据，**仅PVE本机保存，不导出Mac、Git或Nexus**。本目录不包含备份payload。旧21份受保护回退归档在原cleanup-backups目录，不受新namespace保留策略影响。三份停止模板沿用已验证回退档，不每日重复备份。

原生LXC临时目录需供uid映射进程穿越：专用`/var/tmp/dell-local-backup`父目录0711，native临时子目录按PVE默认UMask0022创建；不能把归档私有父目录700直接当LXC临时打包目录，也不能把native worker改成UMask0077后期待非特权tar可读取。最终归档的保护由独立root700 namespace和Hook600保证，不能因此放宽dump目录。

## 备份一致性和验证

完整来宾磁盘/容器文件系统快照会保留系统、软件配置及现有应用数据；它不是MySQL/Nacos/Redis/Rabbit/Jellyfin等逐应用逻辑备份，也不保证不同VM之间同一事务时点。数据库仍运行，不能宣称已经完成生产RPO/RTO或完整业务恢复。

每档完成后执行：

1. 核root-owned、无symlink、固定VMID/归档格式、限定私有目录，收紧为600。
2. `zstd -t`完整压缩流检查。
3. QEMU归档用解压流接`vma verify -`；CF容器归档用解压流接`tar -t -f -`，不提取、不打印成员或内容。
4. 本机记录归档SHA、大小和验证时点；普通指标只输出状态/年龄/数量，不输出秘密或归档内容。

Hook以全部11项verified、无backup-abort/验证错误/日志权限错误才记录整轮成功；`job-end`回调本身不是成功证明。第一次计划保持disabled，首轮完成且原生进程退出0后才启用。

**PVE原生prune在backup-end Hook完整性检查之前执行。** 首轮remove=0不删旧档，之后日常保留按原生时序；不能声称“仅通过自定义校验的新档才影响保留”。完整性错误会留失败状态并触发监控，管理员应及时处理。恢复时先重新校验归档，禁止覆盖现役数据；本轮不执行VM恢复或业务迁移。

## 状态与告警

- PVE GUI：备份任务、存储`dell-local-backup`与任务日志。
- `/var/lib/dell-local-backup/`：root700，current/last-success/last-failure及各run metadata为600。
- 原PVE metadata collector经既有QGA推送`dell_pve_local_backup_*`指标；不新增宿主监听、key或外部探针。
- 告警候选为失败、成功超36小时、任务关闭或状态无效，均for10m。只有完成首备、启用job、指标有效及既有Lark/AM三名白名单配套后才安装，避免初始过程误报。
- 复用既有机内Lark接收对象，不新增接收人、不发送本轮人工测试；同机失效仍可能同时失去备份和通知。

## 运维

先查状态，不在现役机器重跑install.py或初始化原磁盘：

```sh
pvesh get /cluster/backup/dell-local-nightly --output-format json
pvesh get /nodes/pve/storage/dell-local-backup/content --content backup --output-format json
systemctl status pvescheduler.service
```

管理员若需暂停未来计划，可将该job的enabled设为0；**这不停止正在进行的备份**。不要通过kill来宾、强制unlock或删snapshot“取消备份”；应使用PVE准确任务ID并核原生清理、thaw与锁状态。恢复启用前重新核Hook/策略、原挂载、任务白名单及指标，不能让220进入名单。

调整保留或目录前核容量与最近成功，不能用通配删除dump目录或旧21回退档。接入独立目的地时另审敏感数据导出：CF只PVE和220私钥仅220的限制继续有效，不能全量同步目录来绕过。

源码与审核：[policy.json](policy.json)、[hook.py](hook.py)、[install.py](install.py)、[首轮server启动器](start-first-run.py)、[首轮成功后的单次启用器](enable-after-first-success.py)、[指标审核](metrics-review.md)、[告警审核](review.md)。这些是本轮实施代码，不是日常无条件重跑入口。

配置热载依据[Prometheus官方SIGHUP说明](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)、[Alertmanager官方热载说明](https://prometheus.io/docs/alerting/latest/configuration/)。本机Prometheus关闭HTTP lifecycle，本次采用固定原容器ID的SIGHUP，不为热载重建容器。
