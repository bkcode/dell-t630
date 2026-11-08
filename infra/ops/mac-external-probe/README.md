> 2026-11-08用户明确不需要Mac外部探针，当前方案与后续待办已移除；仅保留历史审计资料。已只读确认原LaunchAgent plist与launchd任务均不存在。不得按下文旧流程重新安装/启动。

> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

> 最新用户决定：**本期仅服务器内部Lark，Mac外部探针保持停用。** 运行任务和登录plist已移除；本目录代码/状态/诊断仅保留审计，当前不再安排权限授权或独立App修复。下述修复路径属于未来需另行范围的资料，不是本期下一步。

> 当前状态（2026-11-06）：系统日志已明确证明本地网络隐私策略阻挡后台Python（自有诊断PID50099，责任org.python.python）；同刻直接CLI7/7成功。原实时任务已停用、登录plist已移除，固定更正消息code0；一次性120秒诊断也已卸载并删除自身临时plist。详见[后台权限诊断与正规修复方案](DIAGNOSIS.md)。两次后台健康周期通过前禁止重新启用live发送。

# Mac 外部探测准备包

历史安装阶段记录：主AI曾安装用户LaunchAgent并进行真实Lark验收，随后因后台网络权限拒绝产生错误合并主机告警而停用；当前事实以上方状态及DIAGNOSIS.md为准。以下保留固定范围、机制、审批和回滚说明。本目录不含hook原值，准备与一次性诊断不读取hook。

这台 Mac 在 PVE 整机故障时仍可独立探测，但依赖 Mac 开机、GUI 用户登录、保持唤醒和可用网络。Mac 睡眠、关机、退出登录或断网时不能提供探测；Mac 到服务器的 LAN 故障也可能表现为“主机不可达”。这不是全天候的独立硬件监控。不会自动唤醒 Mac，也不会用 cron/nohup 替代被拒绝的持久任务。

## 固定探测范围

| 检查 | 固定入口 | 通过条件与能力范围 |
| --- | --- | --- |
| PVE SSH | `192.168.21.22:22` | 原生 `nc` TCP 连通；不登录 |
| PVE UI | `192.168.21.22:8006` | 原生 `nc` TCP 连通；不绕过自签证书做 HTTPS |
| Penpot | `http://192.168.21.22:9001/` | HTTP200；前端可达，不代表全部 worker 健康 |
| Nexus | `http://192.168.21.22:8081/service/rest/v1/status` | 匿名健康路径 HTTP200 |
| OMV | `http://192.168.21.22:9080/` | 登录页 HTTP200；不提交密码 |
| Jellyfin | `http://192.168.21.22:8096/health` | HTTP200；不读取媒体/用户 |
| Java 测试认证 | `http://192.168.21.22:19999/.well-known/openid-configuration` | 匿名 discovery HTTP200；不请求 token，不验证真实业务可用 |

代码中的入口不可通过 CLI、JSON 或环境变量扩展。无 SSH 私钥、认证头、Cookie、用户查询参数。HTTP 使用 `/usr/bin/curl -q --noproxy '*'`，禁重定向，不关闭 TLS 校验，不保存响应正文；TCP 使用 `/usr/bin/nc`，避免本机 Python socket 已观测的 errno65 差异。最多3个并发探测，每个子进程绝对超时7秒。生产一次最多发1个通知，单次外发10秒上限；全程正常限时约31秒，60秒周期没有追补循环，文件锁再防重叠。

## 状态与通知

- 初始健康不发“恢复”；连续两次失败才 firing，已通知故障连续两次成功才 resolved；失败/成功抖动不通知。
- 两管理口连续两次**同时不可达**时，只发 `pve-host` 合并事件并取消未发出的服务通知。已经确认发送的服务故障状态保留；管理口恢复后再根据实际服务状态发送必要恢复或新故障，避免伪造恢复。
- `pve-host`恢复表示至少一个管理口连续两次可达；单口仍故障会单独告警，不声称两个管理口全恢复。
- 同一状态转换有固定 event ID；成功后不重复。发送失败每60秒最多重试一次，每事件总共最多3次，预算在发送前落盘，崩溃不能重置成无限重试。耗尽后保留 exhausted 证据，等待人工处理或后续真正状态转换；不做周期提醒。
- 每轮最多发送1条，主机事件优先；状态/outbox上限为固定8个检查。服务故障在发送成功前已恢复时，取消陈旧故障，不发送没有已确认 firing 的 resolved。
- 超过180秒没有采样，或系统时钟回退，重置连续计数与稳定状态为unknown；旧pending保持事件ID/尝试次数/耗尽标志，但只有该检查与主机合并状态都重新取得两次稳定观测后才可投递。唤醒后两次成功会取消未确认的旧firing，或为已确认firing产生resolved；仍失败时不重置旧事件预算，不补发睡眠期间历史。
- Lark网络超时可能发生“远端已接收、本机未确认”；最多3次有限重试有重复消息可能，相同 event ID 可供识别，不承诺远端恰好一次。

私有状态目录固定为 `/Users/yangzhaohui/work/www/harness/dell/private/notifications/mac-external-probe`，目录700、state/lock/events文件600、当前UID所有。秘密父目录同样要求700；拒绝符号链接和不合规私有文件。state原子替换，lock使用非阻塞flock，日志只留时间/检查ID/phase/尝试次数/是否确认，无hook、密码、正文或异常详情。事件日志约256KiB轮换，最多当前及上一份；LaunchAgent stdout/stderr指向`/dev/null`，不产生无限增长的系统任务输出文件。

## Lark 外发边界

只有显式 `run --deliver` 才读取现有600文件 `dell/private/notifications/lark-webhook`。仅允许 `https://open.larksuite.com/open-apis/bot/v2/hook/<小写UUID>`，无用户信息、端口、query、fragment。`curl -q --config -` 从 **STDIN** 取得hook与完整JSON；argv和子进程环境均无hook或消息，禁proxy、redirect、insecure。只接受HTTP200且响应JSON整数`code=0`，不把HTTP200或兼容字段`StatusCode`单独视为成功。响应只在内存里解析，日志不保留正文。

发送格式采用官方 `{"msg_type":"text","content":{"text":"..."}}`。来源：[Lark自定义机器人指南](https://open.larksuite.com/document/uAjLw4CM/ukTMukTMukTM/bot-v3/use-custom-bots-in-a-group)。不支持未经核实的签名密钥、第三方代理或旧凭据。当前Bot是否有关键词/IP/签名要求，须由受控真实发信验收确认，准备测试不伪造结果。

## 已完成验证

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -I /Users/yangzhaohui/work/www/harness/dell/infra/ops/mac-external-probe/test_probe.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -I /Users/yangzhaohui/work/www/harness/dell/infra/ops/mac-external-probe/probe.py baseline
/usr/bin/plutil -lint /Users/yangzhaohui/work/www/harness/dell/infra/ops/mac-external-probe/com.dell.t630.external-probe.plist
```

23个本地mock测试验证状态转换、合并、抖动、恢复、同事件去重、重试上限/崩溃预算、睡眠间隔、私有文件权限、hook白名单与STDIN传输、code0要求及dryrun不发信。测试使用全零UUID假hook和mock subprocess，没有请求真实Lark。真实LAN基线在`lan-baseline.json`；首次05:39:12Z Penpot正处已授权来宾重启窗口，其他6入口通过，验收角色确认250在05:43:27Z新boot下11服务READY后，`lan-baseline-after-maintenance.json`再次匿名探测，7项全部通过；不把维护期间的一次失败直接定为告警。

稳定解释器已实测：`/opt/homebrew/opt/python@3.14/bin/python3.14`，当前3.14.7，stdlib即可，`-I`隔离环境。使用Homebrew版本opt路径而非Cellar补丁绝对路径；升级/删除Python3.14后需再次验证路径和代码，不能假定永久可用。

## 待主AI审核的安装与演练

本目录`com.dell.t630.external-probe.plist`只是源码，尚未写入`~/Library/LaunchAgents`。其中预期参数是`run --deliver`，用户级`StartInterval=60`、`RunAtLoad=true`、后台低优先级；加载即正式启用真实状态通知，不能把源码文件存在当作已启用。

1. 主AI检查固定范围、plist与下列演练，取得实际持久任务安装/外发的工具审批；若自动审批拒绝，停止安装并说明原因，不替换任务机制。
2. 在受控安装动作中，检查700私有父目录和600hook，创建700状态目录；复制已审plist到`~/Library/LaunchAgents/com.dell.t630.external-probe.plist`（600），再由当前用户执行`launchctl bootstrap gui/<UID> <绝对plist路径>`。不使用sudo/LaunchDaemon，不写其他用户任务。
3. 用`launchctl print gui/<UID>/com.dell.t630.external-probe`和两个周期增长的私有state确认实际运行、锁/日志权限与健康基线；本期没有域名，不新增HTTP认证探测。
4. **外发演练需单独批准两条通知**：使用与生产相同sender及text schema，但消息明确标为`【验收】`，只发送独立`DellMacExternalProbeAcceptance`的firing/resolved，不停真实PVE/服务、不修改生产探测状态、不把验收消息当真实故障。`acceptance.py`已准备固定两条验收消息；无任意目标/正文CLI，默认只打印计划，只有`--send`才真实发信。先firing成功code0，再允许resolved；每phase最多3次且间隔60秒，成功后重跑不重复发送。私有receipt与生产state分开，共用锁防并发，保存无秘密payload摘要/确认结果。真实演练尚未发送。
5. 故障合并与重试逻辑已通过本地mock；若需完整真实探测链演练，另行限定只改测试fixture/专用服务窗口，禁止停PVE整机来凑通过。
6. 回滚由主AI批准执行`launchctl bootout gui/<UID>/com.dell.t630.external-probe`，移除仅该plist，保留私有审计状态；不改hook、不删源配置。Mac状态限制需写入最终交付。

最小风险：准备阶段无外发/无持久任务；正式启用后仅固定匿名读取和状态变更时发到已给Bot。受控通知演练不需要制造真实业务中断。

审批后的固定验收入口（准备阶段只执行不带`--send`的计划）：

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -I /Users/yangzhaohui/work/www/harness/dell/infra/ops/mac-external-probe/acceptance.py firing
/opt/homebrew/opt/python@3.14/bin/python3.14 -I /Users/yangzhaohui/work/www/harness/dell/infra/ops/mac-external-probe/acceptance.py resolved
```

真实外发须主AI审批后分别在命令末尾加`--send`；执行前无需在shell读取hook。实际安装及两条外发目前均pending，不能以mock通过替代。
