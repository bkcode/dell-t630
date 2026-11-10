# Penpot原UI默认填入使用手册

更新：2026-11-10（Asia/Shanghai）。用户已明确授权允许的未登录内网访问者读取原owner账号密码，并要求原UI、不新增逻辑。当前已应用并通过原生后检及真实LAN浏览器默认填入/登录验收，见[证据](README.md)。

## 正常使用

1. 从受信LAN `192.168.21.0/24`或WireGuard `10.66.66.0/24`打开[http://192.168.19.50:9001/](http://192.168.19.50:9001/)。已有旧标签页请刷新；必要时强制刷新。
2. 原登录页面会使用既有helper默认填入`owner@dell.local`及原密码；若原UI先显示邮箱步骤，按原“继续”，密码框出现后再由原helper补齐。
3. 点击原“继续/登录”按钮。不会自动提交，不需要任何新增勾选或保存按钮；当前没有checkbox/forget/localStorage功能。

原helper只补空字段，用户手动修改的字段会被保留。若当前已登录，显示工作区属于正常session行为；退出后再看原登录页，不需重置账号。不同浏览器不依赖个人存储，是否默认填入由访问来源是否获准决定。

## 授权范围与账号

LAN21/24、WG10.66.66/24、VM250 self19.50与loopback被允许；这些来源的**未登录访问者也能通过默认JSON读取账号密码**，这是用户已知并明确授权的便利范围。CF19.5与其它来源拒绝。转发头不能把不可信peer变成白名单；不能为排障开放Docker bridge或ALL。页面仍需正常Penpot登录，默认填入不改变原owner权限。

密码未重置，原owner/MCP/设计保留。真实密码只在Mac `private/credentials/penpot-owner-20261110.json`、guest `/etc/penpot/new-identities.json`及本次guest私有运行JSON；普通文档、日志、截图、Git不记录值或密码hash。当前HTTP入口按用户内网合同使用；不将它称为浏览器或OS密码库保存。

## 没有自动填入时

先确认实际入口、网络来源与原登录表单是否显示，刷新后重试。CF或其它未授权来源不返回默认密码属于合同；来源ACL、浏览器渲染与登录故障应分开核，不能通过改原密码、清设计库或重跑安装来解决。管理员仅查看不含值的HTTP状态、no-store、11服务健康、公开配置SHA及只读mount合同；不要在终端输出该JSON或截取密码框实际值。

维护使用新授权下的`approved-worker.py`精确事务，先核新回执与现役文件，不重放早期prepared或旧worker。禁止`fresh-target.py init`、PG整库覆盖、旧身份复制或取远端旧main替换ff改造。源码两条改造待用户push的任务保持独立，本次配置默认填入不代表Git更新已完成。

## 已验证范围

[16:13应用](approved-applied.json)与[16:19原生后检](native-postcheck.json)确认11服务healthy、镜像匹配lock、核心ff1783e clean及原密码/身份保持，remember挂载已撤回。四种未授权Docker来源请求（无头、伪造X-Real-IP、伪造X-Forwarded-For、两者同时）均403。

[真实LAN浏览器](browser-acceptance.json)确认原表单自动填入原owner，密码框保持mask、原Continue按钮可用，点击后进入已认证dashboard；新增checkbox/remember/forget控件为零。自动化测试的cookies/localStorage已清且session关闭，不替用户保留登录状态。当前未签WG或CF端到端，白名单配置不等于这些路径都实测。
