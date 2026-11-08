> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# LaunchAgent 本地网络权限诊断

2026-11-06当前结论：**macOS本地网络隐私策略明确阻挡该GUI LaunchAgent的网络访问。外部实时通知继续停用。** 这不是PVE或七个入口同时故障；直接CLI的成功也不能替代后台环境验收。

主AI已卸载并移除原`com.dell.t630.external-probe`的登录自启plist，保留私有状态与审计副本；先前错误合并主机firing已经被Lark确认，主AI随后发送固定更正消息并得到code0。没有伪造状态为healthy。具体证据在`dell/evidence/implementation/mac-external-probe-{background-mismatch,disabled-persistence,corrective-notice}.json`。

## 实证

- 当前系统macOS27.2，build26B123。
- 主AI批准一次性`com.dell.t630.external-probe-diagnosis`，GUI501、同Python解释器、Background、Nice10、相同工作目录和子进程最小环境，固定7目标。无StartInterval/KeepAlive/RunAtLoad，不写`~/Library/LaunchAgents`；只有显式kickstart一次，进程保留120秒，t=0与t=60各采一次。
- 06:01:22Z的直接CLI同代码7/7成功，两管理端口TCP成功、五HTTP200；同刻LaunchAgent PID50099、PPID1、UID501第一轮0/7，60秒后第二轮也0/7。
- 每条原生命令和限长stderr记录在`background-diagnosis.json`：后台curl对五端口均2–4ms立即exit7/HTTP000；nc两端口exit1、无stderr。直接对照在`background-diagnosis-direct.json`。没有认证、正文或hook。
- `background-diagnosis-localnetwork-log.json`仅查询自身诊断PID及责任身份，系统`com.apple.networkextension`明确记录`Got local network blocked notification: pid: 50099`，并把责任识别为`org.python.python`；同时记录`No team ID found`。旧故障轮也有同类日志。这是本地网络权限阻挡的直接证据。
- Homebrew Python launcher的codesign为adhoc、没有TeamIdentifier、Info.plist not bound；其Framework `Python.app`标识`org.python.python`，当前Info.plist没有`NSLocalNetworkUsageDescription`。原LaunchAgent没有`AssociatedBundleIdentifiers`。这些解释了责任身份不够清楚，但不能仅靠这些metadata断言用户曾点“拒绝”。

诊断没有读取hook、调用sender、写生产state、访问SSH私钥、修改PVE/来宾、改TCC/隐私数据库、重置权限或代点授权。没有用root daemon、cron、接口绑定或冒用受信bundle绕过权限。现有日志不能区分“从未获得授权”与“用户已拒绝”；用户设置页需本人确认。

## 官方依据与正规修复选择

[Apple TN3179：Understanding local network privacy](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy)说明，GUI launchd agent不享有daemon/终端工具的自动例外；系统按responsible code关联提示与用户选择。用户可在System Settings → Privacy & Security → Local Network管理权限。对非SMAppService安装的agent，可通过真实关联的`AssociatedBundleIdentifiers`声明自己的责任app；短命进程可能来不及显示提示。Apple同时建议用Apple签发的代码签名身份保证识别稳定。

可审选项：

1. **现有Python身份，用户手动授权。** 用户亲自到“系统设置 → 隐私与安全性 → 本地网络”检查是否存在`Python`，核实它对应当前Homebrew Framework后决定是否开启。这个授权覆盖共享`org.python.python`责任身份，可能影响其他Python程序；不能宣称只授权Dell探测。若没有该项或身份不明确，不导入/修改数据库、不循环重置权限。
2. **独立自有监控App，长期方案。** 先准备全新自有bundle标识，例如`local.dell.t630.monitor`，明确显示名“Dell T630 Monitor”，Info.plist加入中文`NSLocalNetworkUsageDescription`（只探测固定192.168.21.22服务）。通过真正拥有的代码签名身份签名，保留稳定程序UUID；不借用Terminal/Codex/Python或他人签名。把实际监控helper打包并与该App真实关联，采用SMAppService，或按官方要求关联自己的bundle。首次由用户前台打开，保持存活等正常系统提示，用户亲自授权。App/签名/后台注册与授权都需单独审阅；本次未创建或安装App，签名身份是否可用尚未核实。

无论选哪种，先加载**不发信、不读hook、不写生产state的observation-only**后台检查，连续两个相隔60秒的完整七入口健康周期通过、OS日志不再有该身份的local-network blocked，才允许主AI审阅重新启用live sender。保留原错误事件审计，不把直接CLI healthy或Lark外网可达当成LAN权限已恢复。

如用户不希望授予Mac后台LAN权限，维持当前停用状态，或以后单独批准使用真正位于T630之外的常开探测设备；不以PVE上的自监控替代整机故障外部探测。
