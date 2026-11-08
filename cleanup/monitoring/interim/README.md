> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# Java-only临时监控收口：保留Nexus221

当前只有prepare/nativeparser完成，**没有写270**。停机/退役Nexus221的请求曾被自动审批拒绝，用户维护授权仍pending；本目录无任何Nexus/VM生命周期操作，不能借临时监控绕过拒绝。

只改一个fileSD：移除231/232两节点，12→10node，保留221的`19.31:9100`及所有label原样，Ops其它5目标不变，总数15。220基础health、alias、catalog/installer12配对、Prom配置/规则、PVEpush、网络/hostforward0/WG/数据授权、默认Bash均不改。未来Nexus真正获准迁移后才用原full9/14方案。

## 文件

- `manifest.json`：12/10 exactIDs、固定原SHA/新SHA、唯一目标路径、保护221对象与Ops5标签。
- `guest-node.interim.json`：10node候选；`original12-pinned.json`与`baseline/`是实际源及比较锚，不伪造旧档。
- `native-check.json`：270现役promtool通过STDIN等价10groups，config/SD exit0、精确10地址、Prom主身份/health不变；未写live文件，不代表当前已15UP。
- `sd-only.py`：只fileSD原子替换与精确回退的小工具。本轮只运行plan，**apply/rollback未执行**。
- `full-successor-CAS-contract.json`：将来full9的合法基线只有精确原12或精确interim10，不能随意换oldSHA；不修改原fullmanifest，也不授权Nexus迁移。

## 将来主AI明确执行窗口

`python3 cleanup/monitoring/interim/sd-only.py plan`纯本地。

主AI允许写监控后才运行`... apply --execute`。工具只固定270的`/opt/dell/ops/config/prometheus/targets/guest-node.json`：原bytes/owner/mode/SHA和exact12or10必须同时匹配。首次12→10前真实oldfile备份于270 `/root/dell-monitor-interim-java/<nonce>/guest-node.before.json`，目录0700、文件0600，journal记录实际SHA/mode。只做原子file替换；不restart/reload Prom，不stop任一服务或VM。

提交后再对实际fileSD执行nativepromtool，再等API精确10node+5own=15UP、221仍UP，以及仅231/232的旧告警消失。Ops5label集合须原样。父任务自行确认其它真实告警/清理完成后解除**本site自己的**maintenance；工具不改silence或发Lark消息。

失败自动恢复真实oldfile，结果不confirmed不blindrepeat。显式回退`... rollback --nonce NONCE --execute`只接受本工具的真实12备份及当前固定10或12。若未来full9已经应用，interim回退会因CAS拒绝，不能把已退休Nexus目标“复活”。回退原12会恢复17目标，231/232可能仍down，父任务须管理维护状态。

## 最终full9/14的基线衔接

本次原12SHA与原fullmanifest旧SHA一致；interim10从同一原12只删除231/232，retained9再移221后的bytes与原full候选一致。将来先有用户明确Nexus维护授权、221安全停止/迁移成功、220alias31与Nexushealthy，再fresh readfileSD：只允许(IDs12,固定SHA12)或(IDs10,固定SHA10)。匹配后在经审查的新fullmanifest中选择对应oldSHA，仍保留其它expectedSHA守卫；绝不仅为通过CAS手改SHA。原fullmanifest/脚本本轮未写。
