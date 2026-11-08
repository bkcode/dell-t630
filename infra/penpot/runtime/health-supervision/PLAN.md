> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../../11-live-handoff.md)；旧初始化器不得重跑。

# Penpot250 持续健康监督与最小部署加固方案

状态：**主AI已批准并完成250实施窗口；新监督器上线、一次精确frontend故障自动恢复及一次正常guest reboot均已实测通过。当前事实以runtime-status.json为准，下文保留方案与执行边界。** 只负责VM250；不改源Mac、PVE、模板、其他来宾、tracked Git业务源码、现有三项迁入设计或新身份。当前11服务未停、未重建、未修改Health/PIDs配置。

## 已确认的当前事实

实际 `/opt/dell/penpot` 的 fresh-target、guard、两份fresh compose、runtime logging和两份NGINX模板共7文件SHA全部与本地一致；`source/HEAD=ff1783e7865af7aae571c985f03e057631b7af63`，worktree clean。保留该HEAD相对origin/main已有的两个本地提交，不pull/checkout/commit/reset，不触碰新身份文件。部署适配始终在tracked source之外。

实际unit为Type=oneshot、RemainAfterExit=yes、active/exited、Restart=no，11容器也restart=no。这是挂载门禁和开机启动，不是持续故障监督。当前11容器正常运行，已有5个Docker Health healthy；其余6组件的原生探针已分别调查和只读实测。

新代码独占 `infra/penpot/runtime/health-supervision`，目标新增于 `/opt/dell/penpot/runtime/health-supervision`。原包文件不改；**目标包之外仅新增** `/etc/systemd/system/dell-penpot.service.d/20-health-supervision.conf`。既有unit、Docker数据盘drop-in、fresh compose和fresh-target.py字节不变。不会重新调用fresh-target init或创建身份。

## 六个无Health组件的真实探针

| 组件 | 原生探针 | 已实测与含义 |
| --- | --- | --- |
| frontend | 已有NGINX `127.0.0.1:8082/stub_status`；现有bash `/dev/tcp` 加timeout4秒 | HTTP200且 `Active connections:` 标志，确实测试NGINX响应。不是仅nginx -t，也不依赖镜像内缺失的curl/wget |
| backend | 现有curl `127.0.0.1:6060/readyz` | HTTP200、正文精确OK；当前源码health-handler会检查数据库，并在offline/DB异常返回503 |
| exporter | 现有curl `127.0.0.1:6061/readyz` | HTTP200、正文精确OK；源码wrap-health明确支持。是HTTP进程就绪，不冒充一次真实导出/Chromium渲染完成 |
| admin-console | 现有Node fetch `127.0.0.1:3000/admin-console/`，redirect manual | 实际无凭据路由返回307到既定LAN登录；严格验证origin/path/login route/唯一callback-url为当前admin-console URL。它没有专用health端点，此项仅证明其HTTP/auth路由可用，结合PG与backend探针，不声称已执行有权限管理操作 |
| mcp | 现有Node对 `127.0.0.1:4401/mcp` 发无凭据JSON-RPC initialize | HTTP200且有效serverInfo/protocolVersion；真实临时MCP session DELETE200。每次探针都清理会话，不调用tools/读取设计、不输出session值；该公开握手不是业务授权验收，worker现有readyz和最后的受权只读验收另行覆盖 |
| dns | 镜像原生hosts-file静态记录；busybox查询dell-penpot-health.invalid到127.0.0.1，校验192.0.2.53 | 不依赖公网或上游健康。network-none同镜像/不可达上游下，精确helper正例通过、未配置域名反例失败；此项只证明本地DNS协议/静态解析可用，不声称公网解析成功 |

MCP根路径实际404已记录且明确排除。管理台的307不是任意重定向通过：首次原生helper因fragment中的真实callback参数而失败，随后按实际固定origin/route/callback严格核对，结果在 `native-helper-validation.json`。不猜 `/healthz`，不以HTTP404当健康。

新增只读helper为 `frontend-health.sh`、`ready-health.sh`、`node-health.mjs`，root-owned且不可被容器改写；通过新增compose overlay只读bind至容器。MCP helper所有响应/会话只留进程内，退出码之外无stdout/stderr；DNS用busybox shell重定向掉普通回答。现有5个healthcheck保持。

## 镜像ID与PIDs overlay

`deployment-lock.json` 固定目标IP/hostname/AMD64、数据mount UUID、DockerRootDir、Git HEAD、旧包SHA、精确11服务/容器名、11个实际image ID。三个自建镜像的overlay直接使用已验证 `sha256:<config-ID>`，guard再复核image ID、linux/amd64、原引用解析ID一致；任何mutable tag变化都不能悄悄改变部署代码。官方8镜像仍保持已批准digest引用。

三个ID分别为frontend `bd020fb6…cd38b89`、worker `c0bead67…70dadee5`、import `d4414e3f…005b1261`，完整值在lock。frontend是Git ff1783e最终镜像，禁止拿旧无辅助代码frontend归档回退。

PIDs按6次短时只读stats采样留余量，**观察到的当前最大值不代表业务峰值**：

| 服务 | 观察最大PIDs | 拟定PIDs上限 |
| --- | ---: | ---: |
| worker | 74 | 1024 |
| postgres | 66 | 512 |
| backend | 51 | 512 |
| admin-console | 19 | 256 |
| import | 18 | 512 |
| valkey | 13 | 128 |
| mcp | 12 | 256 |
| exporter | 11 | 256 |
| frontend | 8 | 128 |
| mailpit | 8 | 128 |
| dns | 7 | 128 |

既有CPU/内存、端口、数据volume、新身份secret挂载、日志保护均保持。CPU上限总和12.5、VM6vCPU，明确是共享上限，不是预留；不改plan预算，不承诺所有容器同时达到CPU上限。当前内存上限总和11.9375GiB/VM16GiB保持。

## 持续supervisor最小契约

本地已实现 `supervisor.py`（标准库，无新增来宾包），目标尚未安装。与新的systemd drop-in一起使用：

1. 启动前固定VM250 hostname/IP/AMD64、root guest非PVE、严格本地Docker socket；`/srv/penpot`必须真实mount且UUID精确，DockerRootDir必须 `/srv/penpot/docker`、classic overlay2，不能回退根盘。校验root锁文件/部署代码不可被非root写、旧包SHA、clean Git ff1783e、fresh-instance和automation-ready marker存在；不读取或打印身份值。
2. 要求配置服务集合精确11个且镜像/资源/只读helper符合lock，禁止build/pull。固定 `compose --env-file /etc/penpot/.env -f compose.fresh.yaml -f runtime/health-supervision/compose.health-supervision.yaml up -d --no-build --pull never`；不记录可能含secret的config JSON或stdout。
3. 启动宽限最多600秒，等11服务集合齐全、全部running、Docker Health healthy、实际image ID/architecture/PIDs和持久路径匹配，才向systemd发送READY=1。Type=notify防止未健康时被记为ready。
4. 每5秒白名单读取11服务状态/Health；运行中缺服务、exit/dead/OOM、wrong image/mount直接失败，unhealthy/就绪探针连续3轮失败则失败。正常轮次不进行设计读写，不循环执行真实业务操作。Docker健康检查约30秒一次，启动时保留合适start_period，worker/导入任务busy但ready不视为失败。
5. 失败先停止**固定11服务整组**再退出非零；只停止已核对名称/ID对象，不删除容器/卷或运行prune。停止路径不要求数据mount仍在、不依赖读取该盘上的compose才安全，不操作Docker daemon；若daemon已不可达，记录受控失败而不向根盘创建任何目录。
6. systemd Restart=on-failure、RestartSec=30、StartLimitIntervalSec=900、StartLimitBurst=3；超过阈值留failed给管理员，不无限重启。既有BindsTo Docker+mount/RequiresMountsFor/PartOf关系保留。SIGTERM显式停止时清理整组并正常退出，不把管理员stop当故障重启。
7. 日志/状态仅输出组件名、阶段、布尔和错误类别；不输出Env/Cmd/credentials/HTTP正文、MCP session或查询参数。组锁串行start/stop/安装。运行状态写 `/run/dell-penpot-supervision-state.json`，仅无秘密元数据。

drop-in草稿为 `20-health-supervision.conf`；overlay草稿为 `compose.health-supervision.yaml`。14项Python和8项Node纯本地测试已通过，覆盖：错UUID/RootDir/image ID/服务集合拒绝、tag重指拒绝、healthy阈值状态机、启动未齐不READY、404/任意重定向/MCP错误result不通过、SIGTERM只停一次、停止不删除卷。

## 待批准的目标变更窗口与回退

批准后先确认worker/import idle、无正在执行的导入/设计编辑；保存当前unit/11容器ID与image ID/挂载/资源、3迁入设计只读基线。旧unit/原compose/身份字节SHA和数据UUID留本机私有证据，不复制身份秘密。

仅安装新目录和drop-in，验证脚本/锁/合并配置（私有处理、无secret输出）与systemd语法。必要的一次整组受控重建只应用PIDs/health/helper/明确image ID，使用原数据卷和原身份；不重建镜像、不升级版本、不重新导入设计。健康全部通过并READY后再开始故障验收。

专用故障对象仅 `penpot-penpot-frontend-1`：记录其ID/启动时间，然后在已批准窗口对这个精确容器发KILL，真实观察supervisor发现失败→停止整组→systemd限频拉起→11服务全部healthy且unit running/ready。不杀PG/worker/import，不在业务任务活动时做演练。

恢复后只读重验：数据UUID/DockerRootDir/Git clean及SHA、新身份文件SHA、原3设计ID/结构计数和971媒体hash基线保持；MCP新会话先high_level_overview，再受权只读读取专用验收file/page，无业务写入，公开无key握手仍不能读取设计。LAN前端静态改造/空默认口令和worker/import healthy也复查。任何一项未通过不得签收自动恢复完成。

回退只撤回新drop-in/overlay路径，恢复旧unit元数据，使用原fresh compose与已核实当前镜像ID受控启动；不恢复旧源码包、不改数据库、不删除volume、不再生成账户。若失败保留真实错误阶段，停止进一步改动交主AI处理。回退期间原恢复缺口重新标open，不能伪称旧方式已受监督。

当前已完成调查、supervisor/overlay/锁/helpers本地实现、22项本地测试及无公网DNS隔离验证；**目标变更窗口尚未开放，没有执行任何现役11服务安装、重建、停止、故障注入或持续监督上线。**

## DNS修订与本地测试收尾

DNS原公网one.one.one.one查询已从overlay删除。新增只读 `dns-health.hosts` 只声明TEST-NET保留地址192.0.2.53和保留域名dell-penpot-health.invalid，通过v0.86.0已证实的 --hosts-file-enabled/--hosts-files启用；其他既有上游参数保持，但上游可用性不再作为整组重启条件。

精确同镜像临时容器network=none、非root65532、只读、无发布端口，上游仅127.0.0.1:9不可达，仍返回正确静态A；精确无输出health helper通过，错名被拒，临时容器/scratch已清理，原11容器ID/启动状态未变。公开dnsproxy binary具有NET_BIND_SERVICE文件cap，完全剥离会exec EPERM；隔离验证仅加入与现役相同的NET_BIND_SERVICE这一项能力，未扩大网络权限。失败诊断保留。

停止改用主进程SIGTERM的finally清理；unit ExecStopPost再做仅限仍运行的固定组幂等清理，避免原oneshot ExecStop与监督循环竞争。不使用compose stop读取可能已不可用的数据盘。Type=notify只在11服务齐全健康后READY，源码/Git检查通过 --no-optional-locks执行；900秒最多3次重启，启动总体由systemd600秒限制。

本地验证：Python14项、Node8项全部通过，且AST/JSON/YAML/三份shell语法通过；未以本地通过代替实际故障恢复签收。运行与frontend故障注入、3设计/媒体/MCP只读复验仍待统一250窗口。

## 已执行结果

新监督器已上线并在新boot6229b125-13ea-470a-9044-83974f3a3f16下自动notify ready，11/11 running+healthy，systemd running且failed清单为空。仅精确frontend发过一次KILL，实际观察11全部停止、30秒退避和自动恢复，未人工start；之后仅250正常guest reboot一次，严格SSH及开机11 ready通过。三原文件完整data SHA/stats/revn/vern、原971媒体、当前973逐路径字节、新身份/分配hash、Git ff1783e clean和原base unit/7包文件均保持。额外2媒体已精确归因此前专用副本export/reexport，未删除。MCP只读与无key拒绝、LAN改造静态SHA/空默认口令通过。详见README和runtime-status，不能把准备artifact中的历史标签误作当前服务状态。
