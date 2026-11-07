> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# Dell Ops → Lark 通知桥

当前状态（2026-11-06）：**270实际安装、双阶段真实Lark验收和active白名单路由均已通过**。主AI先批准Ops维护窗口，再确认维护结束后独立批准active。Mac外部探测按用户决定保持停用，本通知路径独立运行在270。

## 结构与秘密边界

既有Alertmanager → `http://172.18.0.1:19093/v1/alertmanager` → native Python桥 → Lark。只监听已核对的dell-ops_default网关，入站源只接受现有Alertmanager `172.18.0.3`，还需Bearer认证；不监听0.0.0.0、10.63地址，不新增PVE端口。Compose明确保留172.18.0.0/16、gateway .1，并将既有四服务固定为Prometheus .2、Alertmanager .3、Blackbox .4、Grafana .5（依据ops-bridge-network-metadata.json）。installer同时核对实际IP与IPAMConfig静态声明，不假设动态重建回原地址。

- Webhook：源仅`private/notifications/lark-webhook`文件600；部署时只经SSH STDIN交到270 `/etc/dell-lark-notify/secrets/lark-webhook`，root目录700/文件600。native服务经`LoadCredential=lark-webhook:...`读取。真实地址不会进入argv、env、Alertmanager配置、普通证据或日志。这里不包含真实地址或其摘要。
- Bridge token：`private/ops/lark-bridge-token`及私有bundle稳定保留，目标host文件`/opt/dell/ops/secrets/lark-bridge-token`为UID/GID65534、600；既有Compose secrets挂到Alertmanager `/run/secrets/lark-bridge-token`，native通过LoadCredential读取同一host文件。token不在公共config目录，避免递归chmod和Grafana配置备份夹带。
- `prepare.py`在任何重写前检测通知状态/非默认AM配置，拒绝通用重新准备；稳定token重复生成调用只保留原值，冲突/坏格式/symlink拒绝。`manage.py`将token权限固定65534/600，未来native amtool配置检查也只读挂载此secret。
- 主AI先受控更新Ops Compose secret挂载；本目录installer不重建容器。安装guard要求既有AM健康、固定image、UID65534、read-only secret mount已存在。Compose只有该secret增量，原4服务、CPU/内存、ports和pids1024保持。

## 接收与外发限制

`bridge.py`只使用Python标准库。DynamicUser、NoNewPrivileges、ProtectSystem=strict等systemd限制；内存96MiB（包含发送子进程）、TasksMax32、CPUQuota10%。原容器总限额2.625GiB，加桥0.09375GiB后约2.71875GiB，仍在Ops4GiB内，约1.28125GiB给OS/runtime；所有进程仍共享既有2vCPU，CPU配额是上限，不增加VM资源。

入站限制64KiB、精确JSON、最大16条告警、禁止重复键/重复Content-Length/Transfer-Encoding；连接总25秒截止，最多2个请求线程。只转预定告警名和`alertname/role/severity/check/unit/service/dell_acceptance/acceptance_run`标签，值经过字符/长度和枚举约束。中文说明由固定映射生成；忽略annotations、generatorURL、externalURL及原始body，不支持@人或任意URL。AM最多每组16条，未来超过时会被AM截断；本期不承诺转发任意新增告警。

外发严格限定https、主机open.larksuite.com、单一规范hook路径（由credential固定），无userinfo/port/query/fragment、无redirect、无代理，使用系统CA与hostname校验。每次发送通过固定native Python子进程，15秒硬截止覆盖DNS/TLS；最多2个子进程，无新容器/服务依赖。每分钟最多30次尝试，超限503交AM重试。只有HTTP200且Lark JSON **整数code=0**才向AM200确认；非零码、TLS/网络/解析失败均503，不输出上游msg/body/URL。只记录状态、整数码、验收run与转换后消息SHA，去重用受验证startsAt（UTC规范化/纳秒）、16hex fingerprint、alert/分组phase及转换消息SHA形成独立事件key；不转发原时间/指纹。成功事件缓存10分钟，同次retry抑制，firing→resolved后同labels新startsAt的新firing仍发送；服务重启后缓存消失，因此是至少一次交付，不能承诺绝不重复。

## 文件与执行顺序

| 文件 | 作用 |
| --- | --- |
| bridge.py | 认证、受限格式转换、Lark发送、超时/限流/脱敏回执 |
| configuration.py | JSON格式的合法AM YAML；acceptance-only与active白名单两模式 |
| dell-lark-notify.service | 固定私网监听的DynamicUser/LoadCredential/resource约束 |
| rebuild270-network.py | 首次270精确4端点/UUID/model预检，同网静态地址与secret事务；无-v/noorphans，失败回旧Compose |
| install270.py | 固定270/网络/镜像/挂载guard，原生amtool+systemd校验，AM HUP及新reload时间戳核对；不重建Ops |
| acceptance270.py | 向AM注入明确“验收”的单个firing，见Lark code0回执后resolved，再见code0；失败尽力结束合成告警 |
| manager.py | 审核后显式调用；公开工具与真实Webhook分开STDIN传输；将通知配置/归属同步私有bundle，阻止generic prepare覆盖 |
| validate-local.py/test_bridge.py | 本地mock/loopback、秘密生命周期回归、固定AMD64 native配置检查，无真实Webhook/外发 |

执行窗口顺序：

1. 主AI审查后开放270窗口，运行manager `rebuild-ops-network --parent-reviewed-270-window`：先核对精确4个自有端点/角色/IP/数据UUID/四healthy17up/Grafana，再模型比对只允许既有CIDR/gateway静态地址和AM secret增量，CPU/内存/ports/pids1024/所有bind不变。stop supervisor→compose down（无-v、无remove-orphans）→新Compose/稳定token→启动supervisor同网重建4服务；核对静态IPAMConfig、secret挂载与四healthy17up/Grafana admin。失败恢复旧Compose/manager、同bind启动并验证健康。不写PVE、不改10.63路由/端口、不删数据。
2. 主AI给本子任务窗口后，运行manager `install-acceptance-only --parent-reviewed-270-window`。installer只启native桥，AM更新配置并HUP，不重建容器。先只匹配`DellLarkNotificationAcceptance`与`dell_acceptance=lark-notify`；真实告警仍local-only。失败恢复AM原配置、停止本次桥，秘密保留私有600。
3. 主AI允许实际两条测试消息后，运行manager `send-acceptance-pair --parent-reviewed-270-window`。消息明确含“验收”，合成故障不影响实际业务服务。只在两个阶段各见Lark code0的脱敏journal回执后写root600 acceptance-proof。
4. **主AI确认维护结束**后，运行manager `enable-live-after-maintenance --parent-reviewed-270-window --maintenance-complete`。要求本boot的双阶段真实proof；桥切active、AM只对白名单warning/critical发送。只重启native桥和HUP AM，实际AM容器ID/PID/StartedAt须保持。

本轮manager三阶段和live启用已真实执行并留证。未来变更仍需明确维护窗口；validation.json只说明本地/config-only检查，实际送达由独立live证据证明。若Lark机器人额外关键词/IP/签名校验导致非零码，以真实结果为准，由主AI集中确认，不猜测签名秘密或放宽URL/TLS。

## 验收标准

| ID | 前置条件 | 步骤 | 可观察通过条件 | 证据 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| LARK-00 | 已审270独占窗口、原数据UUID与精确4端点 | 同网4静态地址/secret受控重建，无-v/noorphans，失败回旧配置 | CIDR/gateway/bind/预算/ports/pids保持；前后4healthy17up/Grafana admin | lark-notify-rebuild-ops-network.json | 通过 |
| LARK-01 | 本地合成数据，未读取真实Webhook | mock/loopback协议/认证/大小/标签/并发/错误码测试 | 不认证不外发；只转白名单；非整数0不确认；上限生效 | validation.json | 仅本地测试通过 |
| LARK-02 | source本机缓存固定AMD64 AM镜像 | network=none、read-only、synthetic secret的amtool check-config | acceptance/active均exit0；源容器身份/状态不变 | validation.json | 仅native config-only通过 |
| LARK-03 | 270受控secret挂载重建完成、主AI窗口 | 安装native桥和acceptance-only配置，原生校验 | bind仅172.18.0.1:19093；DynamicUser/LoadCredential；AM secret UID65534/600；新成功reload timestamp；安装不重建AM | lark-notify-install-acceptance-only.json | 通过 |
| LARK-04 | 测试专用路由、明确两条通知授权 | AM firing → code0回执 → resolved → code0回执 | 两条消息均“验收”；正确状态及run；root600双阶段proof；AM进程不变；无秘密输出 | lark-notify-send-acceptance-pair.json | 通过，真实firing/resolved均code0 |
| LARK-05 | LARK-04通过、维护结束 | 切active白名单路由 | 本boot双阶段proof门禁；真实warning/critical白名单生效；无PVE/其他来宾变更 | lark-notify-enable-live-after-maintenance.json | 通过，当前active |
| LARK-06 | 已配置通知/稳定token | generic prepare重跑/坏token/权限回归 | 已配置拒覆盖；token不轮换；目标600/65534；公共config无秘密 | test_bridge.py、compose-change-evidence.json | 本地与target元数据审计通过 |
| LARK-07 | native bridge实际active | 仅270本机services追加通知unit并采一次 | 全部URL/其它字段不变；unprivileged check、textfile和Prometheus service=1 | lark-notify-collector270.json | 通过 |

## 官方规范来源

[Lark自定义机器人指南](https://open.larksuite.com/document/uAjLw4CM/ukTMukTMukTM/bot-v3/use-custom-bots-in-a-group)规定text消息信封、code=0成功及20KB上限；本实现只发送小于18KB的text，不依赖历史StatusCode字段。[Alertmanager官方配置](https://prometheus.io/docs/alerting/latest/configuration/)规定authorization.credentials_file、v4通用Webhook、send_resolved、max_alerts与HUP热加载；本实现使用这些接口，不直接把AM原始body发送Lark。

## 本轮实际结果

- `lark-notify-rebuild-ops-network.json`：受控四服务静态同网与secret挂载通过，前后4healthy、17/17 targets UP、Grafana DB/admin通过，原UUID/bind/预算/ports/pids保持；旧配置仅备份在270 root私有目录。
- `lark-notify-send-acceptance-pair.json`：run `f20465caddac4d0db4a035da5aaf155f`，06:20:52Z firing code0后才注入resolved，06:21:07Z resolved code0。两条均明确“验收”，没有注入真实业务故障。API接受不代表用户已读。
- `lark-notify-before-active-alerts.json`：active前Prometheus/AM alerts均为空；主AI确认维护结束后才启真实白名单route。
- `lark-notify-final-audit.json`：当前policy active、AM配置与白名单renderer一致、fresh成功reload、DynamicUser/资源/唯一bind/固定argv、root700/secret600、当前boot proof和source SHA通过，4healthy17up/Grafana admin，native NRestarts0。
- `lark-notify-collector270.json`：270仅新增本机dell-lark-notify.service状态采集，原URL及其余字段不变；Prometheus已读到service active=1。未增ACL或外部探测。

证据均位于dell/evidence/implementation。此路径依赖270正常运行；本期Mac外部探测保持停用。事件缓存只抑制短期同次重试，重启丢失缓存的至少一次交付边界保留，不能据此承诺通知绝不重复或主机断电时仍能由同机发送。

## 当前metadata与校验入口

`infra/ops/validate.py`现在保留无marker只能local-only的旧边界；合法通知marker必须owner/schema/mode准确、AM配置完全等于renderer、Compose secret挂载准确且两份稳定token均600且值一致。伪active、错renderer/挂载、错权限或轮换值均拒绝。35项本地回归（含5项新反例）及原Ops13安全测试通过；全Ops静态入口另外执行57项原回归。

270 manage.health只根据合法root状态和native unit active报告lark-active，不重新外发或探测Lark；供应商可达性需要真实发送回执。PVE collector新鲜度从当前Prometheus只读查询，缺失/过旧/负年龄/查询失败不假称fresh。`lark-notify-ops-metadata-health.json`证明public/private/target manager元数据同步后，只执行一次health，四容器及Ops/通知/exporter PID/启动时间不变；历史notconfigured已归档。
