> 实际实施：新增metadata已并入原collector并部署；首轮/计划启用后最终指标enabled/valid/success=1、running=0、verified=11，见[后验](../../../completion/20261109/final-verification.json)。以下保留准备阶段审查，不能以离线测试替代真实运行。

> 当前实施状态：代码块已通过CAS接入既有PVE采集器，见[收据](../../../completion/20261109/backup-metrics-installed.json)。以下为准备审核与离线测试说明，不等于备份已全部完成。

# PVE本机自动备份元数据指标 · 本地候选审阅

2026-11-09。本次仅准备代码块与离线测试；**尚未部署到PVE采集器，不代表首轮备份完成、native job已启用或实时指标通过**。用户新授权的PVE本机原生snapshot备份与现有基础组件健康是不同交付项。本候选不执行备份、归档验证、恢复、fixture或发送通知。

## 插入位置与原实现保护

源：[原collector](../../ops/pve-push-metrics.py)。其本地SHA与经已有strict SSH仅执行sha256sum获得的安装路径`/root/dell-bootstrap/pve-push-metrics.py` SHA一致：

```text
1bd07d63f59b7af1d19f2d3881b7a1c592295c003d39e9d33634f21c7e0f5804
```

候选：[metrics-block.py.txt](metrics-block.py.txt)，SHA256：

```text
66d2dd0cc9e423932f4dc6b937ab5794cef89b0cf45329f76f3e21e3ce610a3d
```

主AI审阅后如实施，以原collector SHA做CAS前提，在唯一的以下行**之前**插入完整代码块，不替换该行，不修改原PVE/RAID/CF采集或QGA推送：

```python
text='\n'.join(lines)+'\n'
```

仅使用原`metric(name, value)`输出接口；新增名字统一以`_db_`/`_DB_`前缀隔离。已对“原文件＋代码块”的完整候选作AST解析，原文件未写。原collector现有CF单位读取不因本次SHA检查而执行；本次没有访问CF unit/token。

## 指标合同

下表名字均加前缀`dell_pve_local_backup_`。代码块不添加路径、run_id、archive、SHA或其它动态label；site/instance等由原Prometheus采集配置附加。

| 后缀 | 语义 |
| --- | --- |
| `last_success_timestamp_seconds` | 最后完整11来宾verified的`finished_at` UTC时间戳；从未成功为0；不是文件mtime |
| `current_run_state` | 有效hook账本状态：verified=0、running=1、failed=2；未知/坏输入=3，同时valid=0。较新的hook失败记录优先于旧current状态 |
| `running` | `current_run_state==1`的0/1兼容指标；描述有效hook账本，不是独立PVE任务进程探测 |
| `last_run_success` | 最近已完成结果：完整verified=1；较新的failed/guard失败或从未完成=0。新running期间保留最近完成结果，不把“正在备份”伪造成成功 |
| `hook_state_valid` / `state_valid` / `metric_valid` | 完整只读检查均通过才1；任一缺失、权限/语法/语义/CLI/挂载失败均0。三个兼容名称本候选值相同，不能当作三个独立证据 |
| `enabled` | 固定native job `dell-local-nightly`的实际enabled；只有合同有效时可信。未知时默认0且valid=0，不能仅靠enabled=0推断job确已被关闭 |
| `verified_guest_count` | **current.json当前run**具有完整验证标志的来宾数，运行中可0..11；不等于上一成功run数量。只在启用调度前要求11，不在运行中对小于11告警 |
| `free_bytes` | findmnt验证store精确mountpoint/ext4/UUID后，statvfs的`f_bavail*f_frsize`，即当前可用空间；失败默认0且valid=0，告警应先判断valid |
| `current_run_started_timestamp_seconds` | 当前run的UTC started_at，辅助识别长期running；不是原native任务独立存活保证 |

首轮尚未完成时，`running=1,last_run_success=0,last_success_timestamp_seconds=0`是合理状态。首轮成功、11份验证与主AI门禁通过前native job保持disabled；告警失败条件应先gating有效metadata、enabled及running=0，避免把首轮或新一轮进行中误报失败。历史last-success旧但current新run失败时，保留旧成功时间、last_run_success=0，便于同时判新失败与恢复点新鲜度。

## 只读输入与安全门禁

- 只读`/etc/dell-local-backup/policy.json`与`/var/lib/dell-local-backup/{current,last-success,last-failure}.json`。policy/state直接父目录root700，祖先目录root所有且禁止group/world写；每一级以dir_fd、O_DIRECTORY/O_NOFOLLOW打开。文件root600、regular、单hardlink、O_NOFOLLOW/O_NONBLOCK，拒FIFO/设备/链接。
- JSON单文件和固定CLI输出最多65536 bytes；重复key、NaN/Infinity及非object拒绝。文件缺current必须invalid；首次缺last-success、last-failure允许，但不能因此success。last-success存在就必须为完整verified账本。
- UTC时间仅接受带`Z`或`+00:00`的ISO值；拒naive、非UTC、不合法、超过当前时刻60秒的未来值、结束早于开始、验证时间超出run边界。旧成功时间不因为“旧”而伪装无效，应由stale规则判断。
- policy与native job严格固定11来宾集合（100/190/200/201/210/221/230/240/250/260/270），排除220、snapshot、私有storage与hook/tmpdir；native job不能带额外邮件接收人。当前verified必须11个独立来宾全部zstd/native验证标志、bytes正整数及mode0600，不看状态字符串一个值就判成功。
- 固定只读CLI为`pvesh get /cluster/backup/dell-local-nightly --output-format json`及`findmnt -J -T /mnt/pve/store -o TARGET,FSTYPE,UUID`。每条8秒deadline、输出边界，超时杀死自己的只读CLI子进程。无pvesh set/create/start、vzdump、archive读或临时主机文件。
- freebytes只在UUID`75e5b438-5ff3-4139-83d6-b6a6847aedac`与精确store挂载验证通过后读取，缺盘/根盘回落不输出貌似正常空间。
- 所有新增收集异常都被block捕获并输出数值安全默认，原collector的PVE/RAID指标列表与后续QGA delivery继续；stderr只写component/status/error_type，不包含异常message、命令stdout/stderr、路径、归档名、SHA或凭据。不新增listener、外联或导出。

读`last-failure.json`是必要补充：hook在guard失败时可能无法更新current，只能写一个较新失败时间；如果只读current旧verified和last-success，就会掩盖新故障。旧失败早于后来成功时不会覆盖成功。缺失或损坏输入不会“回退”到旧成功并宣称当前有效。

## 本地验证与限制

命令：

```sh
python3 -B infra/backup/pve-local/test_metrics.py
```

结果：**46 tests passed**。覆盖首轮running、running继承前成功/失败、guard失败覆盖旧verified、partial verified/220注入/未知状态/坏时间/错误挂载UUID/根盘回落/native job改变、缺current/last-success、重复key/NaN/超限JSON、root UID/600/700门禁、祖先可写、文件/父目录symlink、hardlink、FIFO、固定CLI大小/退出/超时、错误不影响原指标且不泄漏归档或SHA。

测试在本机不需要root：仅对临时测试祖先的UID/外部目录mode进行隔离mock，叶目录mode、实际O_NOFOLLOW/文件类型/链接/大小保持真实检查；逻辑fixture不执行任何host命令。CLI四测试只运行本地Python合成JSON/失败/超限/超时程序，不连接网络、访问PVE或执行备份。

首轮本机测试曾因macOS临时目录路径含`/var`symlink正确被拒，已将**测试临时根**resolve为canonical路径再验证；生产安全门槛未放宽。实际PVE状态账本、live metric、Prometheus加载与新规则只在主AI另行审核部署后验收。本候选没有读归档/私有文件内容，没有触发备份、CF访问或Lark测试，不能签自动备份已经完成或RPO/RTO通过。
