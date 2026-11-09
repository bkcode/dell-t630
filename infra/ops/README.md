> 文档状态（2026-11-09）：当前运行入口如下；旧实施工具和证据保留原时点，不可重放初始化。本轮补齐基础与PVE本机备份，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# ops-service 当前运行与维护入口

VM270 / `ops-service` / `192.168.19.70`。11月9日[实际审计](../../completion/20261109/ops-audit.json)为四个Ops容器健康、15/15监控目标UP（10个guest node＋5个Ops目标）。PVE元数据经既有QGA受控链进入Prometheus。本轮未重做Grafana管理员登录或全量内容恢复；那些是历史验收。

**内网Alertmanager → native桥 → Lark已启用active白名单告警。** 2026-11-06真实“验收”firing/resolved两条均取得Lark整数code0回执；主AI确认维护结束、且Prom/AM告警为空后才启active。Mac外部探测按用户决定保持停用。

主要实际证据为`evidence/implementation/lark-notify-implementation-summary.json`、`lark-notify-final-audit.json`及`lark-notify-ops-metadata-health.json`。原准备阶段说明和not-configured状态保存在[lark-notify/archives](lark-notify/archives/)，不能当作当前运行状态。

## 组件、资源与地址

| 组件 | 固定官方版本 | CPU上限 | 内存上限 | 持久化/网络 |
| --- | --- | ---: | ---: | --- |
| Prometheus | 3.16.0 | 1 | 1536MiB | TSDB；Docker 172.18.0.2 |
| Grafana OSS | 13.3.0 | 0.5 | 768MiB | SQLite；Docker 172.18.0.5 |
| Alertmanager | 0.34.2 | 0.25 | 256MiB | 静默/通知日志；Docker 172.18.0.3 |
| Blackbox Exporter | 0.29.1 | 0.25 | 128MiB | 公共配置；Docker 172.18.0.4 |
| native Lark桥 | Python标准库/已审代码 | 0.1 | 96MiB，包含发送子进程 | 仅172.18.0.1:19093；无新容器 |

四容器合计2.625GiB，加桥后上限约2.71875GiB，Ops既有4GiB预算内约剩1.28125GiB给OS/runtime。所有进程仍共享原2vCPU；上述CPU配额是上限，不是额外预留。镜像AMD64 digest见[images.lock.json](images.lock.json)，四服务ports/pids1024与数据bind保持。Docker default网络明确保留172.18.0.0/16、gateway .1，四地址静态声明并实际核验，AM来源不会依赖动态分配偶然回到.3。

管理目录为`/opt/dell/ops`，数据盘挂载`/srv/dell-data`，数据根`/srv/dell-data/ops`，实测UUID为`01b1f302-27be-4fbd-b4af-b8e782d85dea`。持久数据的UUID/source/mountpoint校验和缺盘停止写入边界保持。四容器restart=no，由`dell-ops.service`统一负责恢复；不得跳过数据门禁直接让Docker在根盘创建目录。

来宾直接入口为Prometheus `192.168.19.70:9090`、Alertmanager `:9093`、Grafana `:3000`；通过独立网关190访问，不经PVE应用端口转发。本通知桥只绑定Docker内部172.18.0.1，不新增PVE端口。

## 当前安全维护入口

以下是历史初装bundle的静态校验器，含旧10.63地址和13角色断言，**不能当作当前19网完整校验或直接重跑的维护入口**。本轮验证清单和新鲜结果见[当日交付](../../completion/20261109/README.md)。历史命令：

```bash
python3 infra/ops/validate.py
```

该校验不启动服务、不重新验证供应商送达；无通知marker仍只允许local-only，有合法通知归属marker时必须与已审renderer完全相等，并检查稳定token600与Compose secret挂载。35项通知桥/契约回归及两模式原生config-only证据见[lark-notify/validation.json](lark-notify/validation.json)；原Ops回归57项由上述入口执行。历史通用native检查若标stale，只说明其旧输入不代表当前配置，不会被改写成新检查通过。

以下命令只在270来宾执行：

```bash
sudo python3 /opt/dell/ops/scripts/manage.py check
sudo python3 /opt/dell/ops/scripts/manage.py health
```

health报告完整四组件、Grafana登录和目标数量。通知字段只根据合法root归属状态与实际native unit active报告`lark-active`或`acceptance-only`；**health不发送通知，也不保证此刻Lark可达**。PVE字段通过只读Prometheus查询collector年龄：0..180秒为fresh，缺失、过旧、时钟倒退、多个序列或查询错误均如实报告。旧notconfigured health保存在270 `/opt/dell/ops/health-history`，元数据更新没有重启服务。

当前已配置通知，通用`prepare.py`会拒绝重置receiver/归属状态；稳定token不自动轮换。不得用通用prepare或整包覆盖消除这个保护。`deploy`会受控停启Ops，属于维护动作；日常只读检查用check/health。

## 通知、秘密与恢复边界

完整协议、执行窗口与LARK验收ID见[lark-notify/README.md](lark-notify/README.md)。真实告警只接收已审告警名、warning/critical等级及白名单标签；静态中文说明替代原annotations，不外发generatorURL/原body/任意地址。Lark HTTPS、CA/hostname验证、无redirect/代理，最多两发送进程、15秒硬截止；只有HTTP200且整数code0才确认。

- Webhook只存本机受控私有源文件和270 native root700目录/600文件，经LoadCredential读取，不在AM配置/环境/命令行/普通日志。
- bridge token位于Compose secrets，目标UID/GID65534、600，AM只读挂到`/run/secrets/lark-bridge-token`，native也经LoadCredential读取；不放公共config目录。
- Grafana SQLite或配置备份不包含完整通知恢复集。通知恢复还需要受控Webhook文件、稳定bridge token、已审unit/代码、AM配置/归属marker及固定网络声明；早于本次安装的备份不能被当作含有这些文件。
- 恢复或更换通知组件时先进入单独维护窗口，保持local-only/acceptance路由，再恢复权限/静态来源/本机unit；新的验收必须经AM firing→code0→resolved→code0，并在当前boot取得proof，主AI确认维护结束后才启真实route。不要将旧proof当作新恢复验收，或自动轮换/公开Webhook。
- 本桥没有持久消息队列，成功事件缓存仅内存10分钟；重启可能重复，恢复不保证重播完整故障历史。Lark API code0证明接受请求，不证明用户已读。通知依赖270正常运行；Mac外部探针用户明确不需要，不列为后续任务。

只有role/IP/本地Unix Docker、镜像、完整服务集合、数据UUID/source/mountpoint和secret边界均通过才继续维护。全局PVE网络及其他来宾的变更仍由主AI集中授权与执行。

## 本机备份监控增量（2026-11-09）

原PVE collector增加`dell_pve_local_backup_*`只读状态指标，既有QGA通道与原指标保持，不新增外部探针或listener。三条备份告警沿既有机内Lark接收对象，通知桥/AM白名单已配套；实际规则加载与计划启用结果以[当日交付](../../completion/20261109/README.md)为准。范围见[备份合同](../backup/pve-local/README.md)和[规则审核](../backup/pve-local/review.md)。本轮无人工通知外发，不把配置/合成路由通过当成新的真实送达验收。
