# Penpot DNS回收修复与监督故障操作说明

更新：2026-11-11，Asia/Shanghai。修复已部署，原生140次探针与11healthy后检已过；70分钟持续观察已通过：4200秒/119次采样，11healthy、0僵尸、NRestarts0保持。只适用于VM250现役固定部署，不是通用重装或一键恢复程序。

## 当前入口和运行合同

Penpot：http://192.168.19.50:9001/；管理仍ub@192.168.19.50及既有受信host key。Gitmain/8a9b961 clean、原镜像/数据UUID/凭据保持，原表单预填和服务器MCP不变。Docker11容器由dell-penpot.service监督，容器restart=no；连续3次bad仍停止全组，不能为避免停机而改阈值或绕过监督器。

penpot-dns必须Compose init:true、lock require_init:true、实际HostConfig.Init严格true。PID1应为docker-init，负责回收原BusyBox健康探针产生的孤儿子进程；pids.max仍128，原30秒健康周期/超时保持。其它10服务没有新init强制要求，不能批量recreate整组。

## 日常只读检查

在受信VM250管理会话中执行以下非秘密检查，不打印docker inspect完整JSON或env：

```sh
sudo systemctl show dell-penpot.service -p ActiveState -p SubState -p NRestarts
sudo docker ps --format '{{.Names}}\t{{.Status}}'
curl --noproxy '*' --connect-timeout 4 --max-time 10 -sS -o /dev/null -w 'Penpot HTTP=%{http_code}\n' http://192.168.19.50:9001/
sudo /usr/bin/python3 -I -B /opt/dell/penpot/runtime/health-supervision/supervisor.py check
sudo docker ps --filter label=com.docker.compose.service=penpot-dns --format '{{.ID}}'
```

check只做既有固定配置/挂载/镜像/锁校验，不启动容器。HTTP200、11healthy、worker readiness与DNS进程计数需一起看，不能拿单个HTTP证明全部正常。取得唯一DNS容器ID后，管理员可用精确格式只读查看：

```sh
sudo docker inspect --format '{{json (index .HostConfig "Init")}} {{json .HostConfig.PidsLimit}} {{json .State.Health.Status}}' <已核DNS容器ID>
```

应init=true、limit128、healthy；原实例未启init或缺字段应由guard拒绝，不手改lock跳过。NRestarts以本次修复后基线0比较，历史累计20/首次候选失败均保留，不能把当前0称从未重启。

## 再次出现失败时

先区分DNS首先unhealthy后全组按策略停止，与worker或其它故障；本次观察链是前者，不推定以后所有故障均同因。保留journal时间线、失败码、最后观测帧及容器安全状态，检查DNS Init、zombie数量、pids.current/max/events和真实健康输出。不要自动反复restart、reset-failed、调大PID/内存、改健康阈值、重新生成令牌或清库来追过。

本次原始快照含84个BusyBox僵尸，属于已收养但未回收的进程，不是单纯CPU/内存超限结论。修复后140次原探针僵尸0→0、PID端点8/128/max events0，[70分钟真实节律观察](stability-result.json)现已通过：4200秒/119采样全11healthy、0僵尸、NRestarts0不增长，PID范围8–14/128，首尾8。该窗口之外的长期稳定和负载SLO不由此扩签。

## 持久诊断记录

/var/lib/dell-penpot-supervision为root700，failures.jsonl与.1/.2为root600，最多3份各64KiB、单记录8KiB。只记录固定reason code、异常类别、已观测服务状态及UTC时间；不存env/凭据/设计内容/异常任意文本。诊断只复用最后正常扫描帧，不在失败路径追加Docker扫描；frame_available及frame_observed_at_utc用于辨别是否无帧或旧帧。

记录失败只给固定告警，不改变原停止路径。不得删除ledger/journal掩盖原故障，不把文件权限改宽来查看；管理员只在受保护服务器会话审阅，不将整个诊断/私有快照打包导出Git或聊天。容量限制只约束文件大小，不承诺任意文件系统卡顿下无延迟。

## 部署失败历史与维护

第一次候选使用可选Init字段点查模板，原生Docker扫描失败并被guard阻断；原监督器fdd384bf恢复、11healthy已验证，日志保留。第二版使用安全index模板、先核缺字段/null/true及11容器原生扫描，再受控应用成功。不能描述第一次失败为误报，更不能关闭guard或忽略native兼容性。

本次只recreateDNS，其余10容器ID保持；原8条file内容与1661媒体路径/逐文件SHA保持，账号密码/env/base unit与Git8a不改。公开监督器SHA5100430505f0447b6b2dfbaf50dfa6ef172793b657e4b387026a51129894fc3a，与overlay/lock同步管理；不能直接覆盖被hash锁定的脚本或只改compose不改对应锁。apply/apply-v2和故障再现脚本只存事务历史，禁止重放到生产或执行fresh-init。

## 验收边界

[38项离线测试](candidate/offline-verification.json)、[二次部署](apply-v2-result.json)、[数据后检](postcheck-result.json)、[原生140次](native-burst.json)、[监控恢复](monitoring-restored.json)各签其范围。[70分钟独立只读观察](stability-result.json)已通过4200秒/119采样；不把有限观察扩签长期SLO、真实设计交互/浏览器内存优化或完整恢复。

自动备份仍只正式MySQL/Nacos，Penpot原设计/素材不新增自动备份。受保护服务器本地快照不等于独立备份或灾备演练；本次不迁数据、不变更其它服务，不修改Penpot源码本体或账号密码。

最终后检：[稳定性4200秒/119采样](stability-result.json)、[15监控UP/角色告警0](final-monitoring.json)、[LAN HTTP200](final-LAN.json)。LAN仅核入口响应，没有请求认证或设计内容；观察未产生新工作负载/凭据/规则写入，不宣称真实浏览器设计操作或长期SLO已验。

[最终离线回归](offline-checks.json)保留真实命令和范围：候选38项、canonical原guard14项、Node协议/重定向8项、历史迁网18项均通过，历史4份fixture字节与原快照一致。14个原断言也包含于候选回归，不重复称新增。离线回归不产生服务器操作或业务构建。
