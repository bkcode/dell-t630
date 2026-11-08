> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../../11-live-handoff.md)；旧初始化器不得重跑。

# ops-service 轻量监控部署准备

状态：`deployed-components-health-and-persistence-verified`（2026-11-06）。最新运行证据见`evidence/implementation/ops-health.json`及`ops-pve-metrics-live-query.json`。下面准备阶段说明为设计历史；当前VM270四组件和12来宾9100已激活，宿主采集经QGA推送，外部通知仍未配置。

准备阶段原文：目标是 plan.json 中已有的 VM270 / ops-service / 10.63.30.40 / 2 vCPU / 4 GiB，不增加角色或整机内存预算。地址目前仅为配置与已分配候选，不表示网络已启用。Ops容器仍只准备文件；附属guest基线包已按主AI精确授权在12个新来宾完成install-only停放。没有修改PVE/网络、启动本机源业务、安装Mac后台任务或发送通知。

## 组件与资源

| 组件 | 固定官方版本 | CPU 上限 | 内存上限 | 持久化 |
| --- | --- | ---: | ---: | --- |
| Prometheus | 3.16.0 | 1 | 1536 MiB | TSDB，14 天且约 8 GB 保留上限 |
| Grafana OSS | 13.3.0 | 0.5 | 768 MiB | SQLite、账号与仪表盘状态 |
| Alertmanager | 0.34.2 | 0.25 | 256 MiB | 静默与通知去重状态 |
| Blackbox Exporter | 0.29.1 | 0.25 | 128 MiB | 无业务数据，配置只读 |
| **合计** | **全部 linux/amd64 digest 固定** | **2** | **2688 MiB / 2.625 GiB** | |

为 4 GiB 来宾保留约 1.375 GiB OS、Docker 与波动空间。实际启动/RSS/磁盘增长仍需目标验证；Prometheus 的保留参数不是底层磁盘配额，WAL/压缩过程需要额外余量。锁文件记录官方发布来源、查询时间和 AMD64 子 manifest，未使用浮动 latest。

## 监控范围与候选目标

`prepare.py` 只读读取根 plan.json，生成 `config/candidates/catalog.json`，完整列出 13 个角色、VMID、候选 IP、部署状态和监控限制。配置已有地址的 12 个 VM 候选 node_exporter `:9100`；CT100 未分配本轮目标 IP，明确保留 pending，不猜测地址。

- guest 9100：CPU、内存、文件系统等来宾 OS 指标。node_exporter 的安装、绑定地址和 ACL 由主 AI 在来宾配置后验证，本包不在源主机安装它。
- HTTP：候选 Nacos readiness、Nexus status、Penpot 前端 root、Jellyfin health、Grafana health。HTTP 200 只证明该入口响应，不能代替认证、交易、协作、MQ 或完整业务验收。
- Prometheus/Blackbox 自监控，以及内部 Grafana、Prometheus、Alertmanager HTTP 探测默认配置。
- Java 应用业务/JVM、MySQL/RabbitMQ 深度指标、备份结果、PVE/RAID/SMART 尚未接入，不能宣称已有全链路监控。

默认 `active_guest_roles=[]`，来宾候选指标/HTTP不自动激活，避免将停止的 VM、未安装的 exporter 或尚未批准的跨区规则当成已接入。确认某个角色 IP、exporter 和访问规则后，用重复 `--activate-role` 按角色启用；无需更改角色或内存数量。`--activate-role` 只启用9100，跨来宾HTTP必须另行显式 `--activate-http-role` 并取得所需ACL授权；优先采用来宾本机textfile collector。

```bash
python3 infra/ops/prepare.py
# 仅在对应来宾已部署、ACL已批准且实际验证后：
python3 infra/ops/prepare.py --activate-role data-prod-db --activate-role ops-service
python3 infra/ops/validate.py
```

生成文件中候选状态不等于探测结果。激活配置也不等于网络已获授权或指标验收通过。

## PVE 宿主指标边界

PVE 管理主机 192.168.21.22 **不在本包 Prometheus 抓取目标里**。本包不在宿主安装 exporter、不监听新宿主端口、不创建路由/nft/转发规则、不读取 API token。

后续可由主 AI 选择：经单独批准的只读 PVE 8006 API/监控账号与可信 CA，或宿主主动向工具区的受控推送方案。须明确最小权限、传输通道和采集调度后再实施，不能为了监控绕开仍待批准的宿主网络变更。当前没有安装 pushgateway 或宿主后台采集任务。

来宾跨区抓取同样依赖精确 ACL：仅从 ops-service 到获准来宾的 TCP9100及已确认的 HTTP 健康端口。不将工具区广泛放行到生产数据库或管理面；本包不负责打开这些权限。

## 告警与外部探测

Prometheus 已定义候选基础规则：exporter 失联、HTTP 探测失败、来宾可用内存低于初始10%、文件系统空闲低于初始20%。阈值是初始运维规则，尚未由业务压测验证，不是 SLA。

Alertmanager 只有一个没有邮件、Webhook、Slack、短信集成的 `local-only` 接收器。它可在界面显示活动告警/静默，但不投递任何外部消息。Grafana SMTP 与自身 unified alerting 关闭，匿名访问/自助注册关闭。**外部告警送达保持 not-configured-not-tested，不能标记验收通过。**

`scripts/external-probe.py` 是可选的 Mac/其他局域网机器单次只读探测候选：

```bash
python3 infra/ops/scripts/external-probe.py --config infra/ops/config/external-probes.json
```

本次没有执行此网络探测，也没有创建 launchd/cron/常驻进程。默认仅检查 PVE 已有 SSH/UI TCP 端口；TCP 可连接不证明应用、TLS或登录健康。Grafana 私网 HTTP 地址为 disabled 候选，需批准路由或操作者明确建立 SSH 转发后调整配置再测试；`--include-candidates` 是显式选择。

探测只执行 TCP connect 或无凭据 GET；拒绝 URL 中账号密码、query、fragment、公共地址和业务操作路径，不跟随重定向、不关闭 TLS 验证、不记录响应正文、不发送通知。输出机器可读结果和失败退出码；`--output` 可保存到私有文件。Mac 睡眠/关机后无法持续探测，因此它本身不是独立24小时告警服务。

## 私有设置与挂载门禁

公开部署定义在本目录；私有包在 `dell/private/ops/bundle`，初始 Grafana 管理密码另存 `private/ops/grafana-admin-password`，均600且目录700。密码随机生成，重复 prepare 复用，不输出实际值。Compose 使用 `GF_SECURITY_ADMIN_PASSWORD__FILE`，不把密码放入 Compose 环境值。首次登录用户为 `dell_admin`；若以后经授权在界面轮换密码，要同步受控秘密，脚本不会强制重置已有 Grafana 数据库密码。

默认安装目录 `/opt/dell/ops`，数据盘挂载点 `/srv/dell-ops`，数据目录 `/srv/dell-ops/data`。三个持久化子目录分别归 Prometheus、Grafana、Alertmanager 的实际镜像 UID/GID，配置目录只读挂载。数据路径拒绝 `..`、非规范路径、符号链接以及嵌套盘逃逸。

来宾数据盘 UUID 尚未实测时保持 pending，部署会拒绝运行。取得 VM270 数据盘真实 UUID 后：

```bash
python3 infra/ops/prepare.py --data-uuid '<VM270实际文件系统UUID>'
```

可用 `--data-mountpoint`、`--data-root`、`--install-dir` 调整已分配路径。`--public-uri` 设置真实管理入口；默认是私网 HTTP。若用 SSH 转发访问，需将 root URL 设置成实际浏览器入口；公网/HTTPS入口需另行配置可信证书、代理和 secure cookie，不因本包存在就算完成。

## 主 AI 后续部署

1. 等待明确宿主网络授权并完成来宾网络、数据盘挂载和 ub 登录验收。
2. 实测并登记 VM270 的数据盘 UUID，重新 prepare，保留初始秘密与700/600权限，将完整私有 bundle复制到其 INSTALL_DIR。
3. 在该来宾 root 执行：

```bash
python3 /opt/dell/ops/scripts/manage.py check
python3 /opt/dell/ops/scripts/manage.py deploy
python3 /opt/dell/ops/scripts/manage.py health
```

脚本拒绝 PVE 宿主、非 Linux AMD64、错误来宾 IP/安装路径和远程 Docker endpoint，始终固定本地 Unix socket。首次部署拉取固定镜像，按镜像 UID准备目录，先运行目标 promtool/amtool/Blackbox 静态校验，再启动服务；目标来宾的这些检查当前尚未运行。

全部容器 restart=no、bind create_host_path=false。`dell-ops.service` 使用 RequiresMountsFor、BindsTo、精确 UUID/source/mountpoint 校验，统一负责开机和异常恢复，避免数据盘缺失时 Docker 自动向根盘建目录。运行期约每5秒检查完整4服务集合及健康；异常停止整组后由 systemd 限频重试。挂载或 Docker 服务消失后，修复完成由管理员核对后显式恢复单元。停止路径不依赖数据盘或业务 IP仍可用。

health只输出脱敏组件状态、HTTP readiness、Grafana登录与目标数量，不打印凭据或响应体；跨来宾指标、业务健康、外部送达另行验收。数据盘掉线、虚拟机重启、持久化恢复和真实告警测试仍待目标环境验证。

## 已验证与未验证

`validation.json` 记录静态结果：4服务、固定AMD64、2.625GiB限额、600秘密、空外发接收器、13角色候选、57个离线安全测试。测试覆盖缺服务/缺盘/错误UUID/只读/嵌套挂载/路径逃逸、探针拒绝凭据和业务路径、不记录正文等。

已补充 config-only 二进制验证：在本机Docker使用已缓存的官方AMD64 digest，执行 promtool check config、promtool check rules、amtool check-config，及经 Blackbox help 确认的 --config.check；全部退出0。工具容器均 pull=never、network=none、read-only、限CPU/内存、无端口，仅挂公开配置，没有秘密或源卷。17个源容器的ID、状态和运行标志前后保持不变。证据见 `evidence/native-config-check.json`；`validation.json` 按输入SHA256保留校验结果，配置改变后标记需重验。Blackbox的布尔帮助格式为 --[no-]config.check，脚本已识别并有回归用例。

未执行：目标 pull/start、目标来宾 native 校验、来宾9100与HTTP网络探测、PVE指标接入、真实负载、故障演练、Mac后台调度、外部通知送达。config-only 通过不证明监控目标或告警送达已通过，源 Docker 服务原样保留。

## 官方依据

- [Prometheus 3.16.0](https://github.com/prometheus/prometheus/releases/tag/v3.16.0)
- [Grafana 13.3.0](https://github.com/grafana/grafana/releases/tag/v13.3.0)
- [Alertmanager 0.34.2](https://github.com/prometheus/alertmanager/releases/tag/v0.34.2)
- [Blackbox Exporter 0.29.1](https://github.com/prometheus/blackbox_exporter/releases/tag/v0.29.1)
- [Prometheus 配置](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Alertmanager 配置](https://prometheus.io/docs/alerting/latest/configuration/)
- [Grafana Docker 配置](https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker/)

## 来宾基线脚本

[guest-baseline/README.md](../../guest-baseline/README.md) 说明12个新Debian13来宾的install-only停放、可恢复policy-rc.d、私网激活门禁和本机只读health textfile；PVE/CT100/源Mac不在安装范围。33项新增离线回归通过，并已按授权在12个新来宾真实执行install-only停放；没有激活exporter或collector。实际证据见根evidence/implementation/guest-monitoring-install.json。
