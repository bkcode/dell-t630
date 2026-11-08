> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

> 当前生产式运行入口（2026-11-06）：使用`dell-penpot.service`及[runtime/health-supervision](runtime/health-supervision/README.md)的notify持续监督、11健康检查/镜像ID锁/PIDs；旧fresh-target只作为初始化bootstrap，不是持续管理入口。真实frontend故障自动恢复和guest重启已验证，原数据/Git/身份保持。

# Penpot：Git 改造版与应用级迁移

> 当前源码合同：使用 **[bkcode/penpot](https://github.com/bkcode/penpot) 的 main 分支**，固定仓库`git@github.com:bkcode/penpot.git`或`https://github.com/bkcode/penpot.git`。后续直接从该仓库显式取main并锁定审核commit，不跟随默认分支。详见[VM250源码与更新](../../machines/vm250-penpot-service/SOURCE-AND-UPDATES.md)。本页初次迁移的bundle、旧IP及版本数字保留历史意义；11月8日基础服务已恢复，未执行程序更新，PAT自动认证另行处理。

最后验收状态：**VM250 的完整11服务、3个活动设计官方`.penpot`包导出/导入、新身份、素材与结构均已有通过记录；11月8日已复验11服务健康，但本轮未重新验证全部设计内容。** Mac 源保持运行，未改源设计；没有复制旧部署密钥、密码、cookie、session 或 MCP key。

这是当前执行入口。旧准备流程保存在 [HISTORY-preparation.md](HISTORY-preparation.md)，其中源身份复制、PG 全库恢复、旧安全 frontend 归档仅作历史审核，不再作为本次迁移路线。

## Git 与运行版本

- 原项目：`/Users/yangzhaohui/work/www/harness/penpot`，origin `git@github.com:bkcode/penpot.git`、branch main。
- 精确部署 HEAD：`ff1783e7865af7aae571c985f03e057631b7af63`，包含 remote/main `9aedbb011cd803eb615225ca21f7f47cb8c2fa09` 之后的两个本地已提交改造。原 worktree clean；只 fetch 原 origin，没有 pull/checkout/commit/push 或丢弃改造。
- 通过 Git bundle、原 shallow 边界、目标 `git fetch/checkout` 获取到 `/opt/dell/penpot/source`，目标 HEAD 精确、worktree clean、connectivity fsck 通过。客户端私钥不复制，SSH agent 不转发。
- bundle 为 207,748,597 bytes，SHA256 `08030657199cee422117936efdec2d64f0da2fd1d9c2b8af9112d1ff69331782`。四个真实身份文件在可达 Git 历史均未跟踪。
- frontend 从目标 Git `frontend/selfhost` 上下文构建新唯一标签 `dell-penpot-frontend:2.18.5-ff1783e-amd64`，镜像 ID `sha256:bd020fb6bddfd77449c26f76ee04ca7b2b50a0ffe8562ebc7b9e294bfcd38b89`；sidebar 与登录辅助完整保留。
- 登录辅助仅挂载 Git 的空值 example JSON；实际 LAN 返回的 CSS/JS SHA 与该 HEAD 完全一致，浏览器默认密码为空，不能注入任何真实密码。
- worker/import 已编译制品的 17/10 个代码、包、锁与配置文件逐个 SHA 与目标 Git 一致。未变的编译制品可复用，source Git 改造未丢。
- 后端及官方依赖保持已核实的 2.18.5-RC1 / PostgreSQL15.19，不因当前 Git 中存在 2.19 源码而无计划升级全部 Penpot。

证据：[Git事实](git-source-facts.json)、[运行来源](application/git-runtime-provenance.json)、[LAN改造验证](application/lan-frontend.json)。

## 目标与身份

- 当前配置：VM250 `penpot-service` / `192.168.19.50`，LAN入口 `http://192.168.19.50:9001/`；故障后在线状态未复验。旧10.63.30.30与21.22:9001仅属初装阶段，已不作为访问入口。
- 管理登录：ub + 客户端密钥，使用主AI已验证的控制通道；不关闭host key验证。
- 应用包：`/opt/dell/penpot`；Git源码单独在 `source/`，部署适配不修改tracked源码。
- 新 owner：`owner@dell.local`；新 worker：`mcp-worker@dell.local`。密码由目标本机随机生成，保存在 `/etc/penpot/new-identities.json`（root/0600），不写普通文档或聊天。
- 新部署/数据库秘密在 `/etc/penpot/.env`；新MCP身份在 `/etc/penpot/worker-credentials.json`，worker/import分别使用UID1001/1000的0600副本。没有跨设备复制旧身份。
- 数据根：`/srv/penpot/docker`，classic overlay2；独立 `/srv/penpot` UUID `ccccda03-bffd-4054-afd3-e0e22f0c607e`。
- `dell-penpot.service` 与 Docker daemon 都有数据mount依赖；容器restart=no，避免磁盘未挂载时Docker自行启动写根盘。

`compose.fresh.core.yaml` 为新身份引导的9核心服务，`compose.fresh.yaml` 为最终11服务。初次初始化由`application/fresh-target.py`完成；持续运行通过`dell-penpot.service`及`runtime/health-supervision`的notify监督管理，不重跑fresh初始化，不使用旧restore receipt或伪造恢复成功标记。

## 已完成的官方数据迁移

源账号只在Mac loopback认证；Cookie只留Mac。通过2.18.5真实 `export-binfile` SSE接口导出，使用 include-libraries=true、embed-assets=false（官方互斥选项），解析官方URI封装后从同源loopback下载。没有PG整库或旧账号复制。

源活动范围：2个团队、2个活动项目、3个活动文件、0库关系。API还返回2个可恢复软删测试项目；只读计数显示4个软删文件，这些未激活，仍保留在源。官方包不迁移旧账号、会话、访问token或完整审计/评论/版本历史。

| 源文件ID | 官方包bytes | SHA256 | 目标新ID |
| --- | ---: | --- | --- |
| `9eb8678d-764d-810b-8008-e237712e9048` | 65040315 | `341cc8ba8520d0cd6d7fd88c5955186aa04372ae277bde4c32343f396eb8e5c8` | `13a31dab-5204-818d-8008-e6fe8d7ec046` |
| `e519ae78-b5c8-81fe-8008-e32aa3221908` | 60118962 | `f4b94f853c8a658ec9f357b2f7de2a6793febd225359e6861586ec51355004a4` | `13a31dab-5204-818d-8008-e6feac0c763c` |
| `e519ae78-b5c8-81fe-8008-e32a81af5e27` | 2634445 | `375504af9348d06ec0c57ab98abd35bffc9e916a3af14d6419f46c3f1e8d665f` | `13a31dab-5204-818d-8008-e6febff84cd7` |

全部包传输后SHA匹配，团队/项目/文件新ID映射在目标 `/etc/penpot/application-id-map.json`。3文件结构统计逐项与源相等：共30页、52601形状、411组件，颜色/字体/库计数相等；971个导出唯一媒体SHA在目标971素材中全部找到。

证据：[结构比较](application/content-comparison.json)、[媒体比较](application/media-comparison.json)、[真实运行](application/live-target.json)。原始导出包和清单仅存Mac私有 `dell/private/penpot/application-export`，不含源身份。

## 验收结果

- 11服务running；有健康探针的PG、Valkey、worker、import、Mailpit均healthy，验证时0重启。
- 新MCP身份先执行high_level_overview，再只读执行上下文，匹配专用验收file/page；无key握手可公开200，但随后设计读取被拒。未把握手HTTP200误判为越权。
- 经主AI审阅并在250独占窗口内，仅对独立空验收页`Page.name`执行临时nonce→读回→恢复`Page 1`→读回。每次校验file/page IDs、文件名、空页与selection；独立owner后端API确认nonce保存为revn1（3.315秒）、恢复保存为revn2（3.161秒）。3迁入原设计统计、新身份与IDmap文件摘要保持不变；只触及验收页，保留这两次验收修订。
- 仅在专用副本编辑页名，官方导出后再次导入，再导出仍保留编辑；原导入设计统计/版本未变，Mac源设计未改。
- 用固定官方公开小样本真实异步导入，completed；相同requestId仅一个job/文件；idle重启import服务后状态与文件ID保持，相同requestId不重复导入。进行中的强制中断场景尚未执行，单独not-run。
- 250在worker/import idle后受控来宾重启，boot ID改变；新身份/IDmap文件、数据UUID、DockerRootDir保持，11服务回起、worker ready200。没有重启源或PVE。
- 查询安全runtime模板保持只读：access记录method/path/protocol，去Referer；仅MCP location禁用敏感error日志，状态/耗时仍保留。真实新MCP key未在前端日志出现。

证据：[MCP读取与拒绝](application/mcp-acceptance.json)、[MCP写入与恢复落库](application/mcp-name-roundtrip-result.json)、[副本再导入](application/acceptance-roundtrip.json)、[异步重试恢复](application/acceptance-async-import.json)、[受控重启](application/reboot-acceptance.json)、[日志补丁](runtime/logging/README.md)。

## 后续运维与限制

- 停/启通过 `systemctl stop/start/restart dell-penpot`，不绕过mount门禁裸启动Compose。
- 后续代码从`bkcode/penpot`显式取`main`并锁定审核commit；Git bundle只解释初次历史移交，不作为后续默认更新来源。先确认历史两条本地改造在选定远端main中可达，不在源擅自push，不复制客户端私钥/agent。
- 数据继续走官方包和应用级导入；不能重启旧.env/worker身份传输或整库迁移路线。
- 暂无域名，HTTP LAN是已选阶段；HTTPS/正式SMTP仍pending。Mailpit只内部接邮件，无公开管理端口。
- 独立设备备份目的地仍待主AI统一处理；本机源保留是当前回退现场，不等于已完成长期灾备。
- 老预审三镜像归档SHA仍保持 `6d27b16c5bd9e9cecbd4c825734ac2e1bc9cee2d10a8f38d5f26da32bd7036d1`，其中frontend移除了辅助代码，**不是当前Git最终frontend**；不得用旧包覆盖当前版本。
- 原生curl --noproxy已验证LAN。Mac Python socket执行面出现errno65不能单独据此判定PVE路由故障，引用主AI `LAN-entrypoint-cli-probes.json`。

`application/mcp-name-preflight.mjs`与`mcp-name-member.json`记录实际API：`Page.name`可写、`File.name`只读。`mcp-name-roundtrip.py/.mjs`是已执行验收的审计脚本，写运行需再次取得主AI目标窗口；不要自动重跑或对真实设计使用。新owner会话仅在来宾内用于后端只读确认，MCP密钥始终在worker受控秘密挂载中，未写入证据。
