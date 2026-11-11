# Penpot周期性停止：DNS子进程回收修复

更新：2026-11-11，Asia/Shanghai。修复已上线，11服务健康、原生140次加速探针和数据保护后检通过；**70分钟原节律只读连续观察已通过：4200秒、119次采样，全程11healthy、DNS僵尸0、NRestarts0不增长。** 本次只修VM250的DNS init与监督诊断，不改设计、账号密码、业务源码或其它服务。

## 本次故障链与原因

只读observer捕获14:31时DNS是唯一先变unhealthy的服务，随后supervisor连续3次bad触发既有策略，停止整组11服务。DNS容器原Init=false，dnsproxy作为PID1有7个线程，同时积累84个被PID1收养的BusyBox僵尸。原30秒健康检查使用BusyBox timeout watchdog，子进程成为孤儿后缺少init回收，每次约增加一个僵尸；在pids.max=128约束下累积耗尽PID配额，导致后续健康探针失败。该次全组停止来自真实DNS健康失败后原保护策略生效，不能称为worker/内存/令牌故障或监督误报。

原始带内容/进程诊断保留VM250受保护来源，不导出私有快照或设计哈希到Git。公开因果实证见[隔离A/B](dns-reaping-ab.json)：同版本arm64隔离容器、无网络/数据卷/发布端口、readonly和低PID限制；Init=false的12次原探针使僵尸1→13，Init=true的140次为0→0，错误DNS名称仍拒绝，临时容器/目录已清。它证明回收机制，再由服务器amd64原镜像原探针验证，不拿异构本地试验代替现场。

## 最小修复与第一次失败

只对penpot-dns的Compose添加init:true，锁文件追加require_init:true，监督器严格要求DNS实际HostConfig.Init为布尔true；其余服务不新增init约束。健康周期/超时/阈值、PID128、镜像、env、用户、网络、CPU/内存和restart策略不变，没有放宽guard或换镜像来追过。

第一次候选用可选Init的点路径模板，旧容器缺该字段时Docker原生prestart扫描失败；原guard拒绝启动，根任务恢复原fdd384bf监督器并验证11healthy，日志/失败记录保留。该失败不是误报。随后改用可选键安全index模板，原生验证缺失/null/true及11容器扫描后，部署第二候选成功。[兼容修正](template-compatibility-fix.json)、[二次应用](apply-v2-result.json)。最终监督器公开SHA256：`5100430505f0447b6b2dfbaf50dfa6ef172793b657e4b387026a51129894fc3a`。

新增bounded failure ledger只记录固定错误码、异常类别、已观测的服务状态与UTC时间；在stop前写入最近一次正常扫描帧，不额外执行Docker扫描。目录/文件root700/600，最多3×64KiB、单记录8KiB，拒绝不安全路径/权限，诊断写失败不代替原失败/停止策略。旧日志保留；帧可能早于故障时刻，不能当作新鲜根因扫描。

## 已验证与保护范围

- [38项离线记录](candidate/offline-verification.json)：原14个断言方法不变，24项新DNS/诊断/安全文件系统等测试通过；仅DNS fixture适配init策略。其余guard/monitor/stop/main AST保持，阈值/超时/PID/restart不变。
- [部署后检](postcheck-result.json)：Git仍8a9b961 clean，只重建DNS，其他10容器ID保持，11healthy；原8条file记录及全部内容摘要、1661个媒体路径与逐文件全SHA一致，身份/凭据/env/base unit字节保持，不迁数据或写设计。
- [原生amd64加速验证](native-burst.json)：原DNS健康探针140次全部通过（188.35秒），僵尸0→0，端点PID8/128、max events0，监督NRestarts基线0未增加；未改探针节律/阈值或PID上限。加速序列中的短时PID9是运行中进程，端点仍8，不把瞬时采样当绝对恒定。
- [监控恢复](monitoring-restored.json)：15targets全UP，Penpot unit/HTTP/collector UP、该角色活动告警0，只解除本次维护silence；其它规则、接收方与silence未改，无测试通知。

补充[最终离线回归](offline-checks.json)：根任务重跑候选38项通过；canonical原14个guard断言沿用新DNS fixture通过；Node协议/重定向8项、历史迁网18项（冻结原4份fixture字节）均通过。三类范围分别记账，不把14项重复算入38项的新测试，也不称这些离线测试验证了服务器或Go/Java构建。

## 已通过：70分钟实际持续观察

[只读观察启动](stability-started.json)后，[实际稳定性回执](stability-result.json)完成4200秒、119次采样，全程11healthy、DNS僵尸0、NRestarts基线0不增长、failures=null。DNS进程采样范围8–14，上限仍128，首尾均8；不能称全程PID恒8。[最终监控](final-monitoring.json)15UP/角色告警0，[LAN入口](final-LAN.json)HTTP200。观察未写工作负载/设计/凭据或告警规则，观察unit已停止。该有限窗口证明本次机制修复，仍不签长期负载SLO或浏览器内存改善。

日常检查与失败留证见[操作说明](usage-manual.md)。原Git8a/镜像/密码/预填UI/MCP身份保持，自动备份仍只正式MySQL/Nacos；本次服务器受保护快照不是新增自动备份或独立灾备，不能重放apply脚本或fresh-init。
