# Penpot原UI：原账户密码默认填入

更新：2026-11-10（Asia/Shanghai）。用户明确要求原UI、不增加控件或保存逻辑，并[明确授权上述范围默认填入](explicit-approval.json)：LAN `192.168.21.0/24`、WireGuard `10.66.66.0/24`、服务自身`192.168.19.50`与loopback范围内，未登录访问者也可读取原owner账号密码。用户已知悉该读取范围。**已完成配置应用、原生来源负测与真实LAN浏览器默认填入/登录验收。**

## 现役基线与实现方式

[浏览器记忆方案已撤回](../penpot-browser-remember-20261110/README.md)，[16:05恢复回执](../penpot-browser-remember-20261110/restored-original.json)确认原overlay/lock、原UI恢复且11healthy。现役沿用Penpot核心`main/ff1783e7865af7aae571c985f03e057631b7af63`中原有的`frontend/selfhost/login-defaults.js`；不修改该helper、表单结构或按钮，不新增checkbox/forget/localStorage逻辑，不build或换11镜像，也不取Git新码。

原helper读取同源`/js/selfhost-login.json`，补齐原表单空字段；仍需用户按原“继续/登录”按钮，不自动提交。公开JS不嵌密码；运行JSON按新授权向上述来源提供原owner账号和密码，`Cache-Control: no-store`。CF `192.168.19.5`与其它非白名单来源拒绝；仅信任loopback的X-Real-IP、禁止递归信任，不能用远端转发头扩大来源。实际LAN/WG/CF通路是否测试须以对应回执为准，配置允许/拒绝不冒充逐路径实测。

## 运行配置与秘密边界

公开源为[approved-worker.py](../../infra/penpot/login-prefill/approved-worker.py)和[NGINX精确location](../../infra/penpot/login-prefill/selfhost-login.conf)。现役runtime目录`/opt/dell/penpot/runtime/login-prefill-approved/`，只增加一个frontend只读NGINX挂载；沿用既有`/run/secrets/login-defaults`挂载并将来源换为guest私有`/etc/penpot/browser-login-defaults.json`（UID/GID1001、0600，父目录root0700）。Compose、监督overlay、deployment lock同步登记公开配置SHA与精确mount，不输出密码内容或其hash。

现有账号`owner@dell.local`与密码原样保持，原owner/MCP身份及设计数据不改。密码原来源只引用Mac `private/credentials/penpot-owner-20261110.json`、guest `/etc/penpot/new-identities.json`，本次运行副本仅guest上述私有文件，不进Git。虽然文件权限保护服务器磁盘读取，授权来源仍可通过未登录HTTP读取密码；这正是用户本次明确授权的默认填入范围。

不重跑`fresh-target.py init`、旧共享方案worker、早期prepared或PG整库覆盖；本次使用新授权下受审查的精确runtime变更。此前自动审批拒绝记录保留为当时历史，不等同当前仍未授权；[explicit-approval.json](explicit-approval.json)覆盖本次暴露范围。fork Git更新仍等待用户推两条既有改造到main后通知的独立任务，本次不替用户push、pull或构建。

## 已完成证据与限制

| 证据 | 含义 |
| --- | --- |
| [explicit-approval.json](explicit-approval.json) | 16:06用户明确授权原UI预填及未登录来源范围 |
| [approved-prepared.json](approved-prepared.json) | 新候选原生parser与精确11服务配置通过，原owner登录验证、未改Git/镜像、未输出密码 |
| [review.md](review.md) | 有界方案审查及验收条件，不能代替实际运行/浏览器通过 |
| [approved-applied.json](approved-applied.json) | 16:13已应用；11healthy、原owner密码及身份文件保持、JSON匹配、Git ff clean、镜像保持、监督检查通过 |
| [native-postcheck.json](native-postcheck.json) | 16:19最终原生后检；11healthy/镜像匹配lock、secret UID/GID1001与0600、无remember挂载；未授权Docker来源无头/伪造X-Real-IP/伪造X-Forwarded-For/两头同时伪造均403 |
| [browser-acceptance.json](browser-acceptance.json) | 真实LAN浏览器原表单；端点200/no-store、账号密码与原owner匹配且密码框masked，原Continue可用、无新增控件，点击原按钮进入已认证dashboard；测试cookies/localStorage已清、session已关闭 |

应用回执中的浏览器pending是16:13阶段状态，已由随后浏览器证据补齐；不据此回写历史文件。当前验收只覆盖上述真实路径与原生负测，**未签当前WG端到端或CF端到端**。CF拒绝来自配置白名单，不冒称本次真实CF请求已测；设计写入、MCP内容或完整恢复未重验。使用方式见[手册](usage-manual.md)。
