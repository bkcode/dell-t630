> 当前实施状态：通知白名单已按[实际收据](../../../completion/20261109/backup-notify-whitelist-result.json)更新；原生AM校验通过，仅native桥重启、原AM容器HUP，未测试外发。以下为候选准备时点的审核记录；Prom规则已在首11verified/原生OK/计划enabled之后[原生校验并SIGHUP加载](../../../completion/20261109/backup-alerts-installed.json)，[后验](../../../completion/20261109/final-verification.json)三条healthOK/inactive。未人工发送通知。

# PVE本机备份告警：仅本地准备审查

2026-11-09。当前只新增backup-alerts.yml、alerts-install.py与本审查说明。**尚未向270上传/安装规则，没有reload、recreate、外发验收或新接收人。root已明确选择固定原容器SIGHUP作为未来具体reload方案。** 首轮11个备份对象验证及job启用由root独立完成；本地测试不代替它。

## 实际270只读前置

- Prometheus现役config bind：host `/opt/dell/ops/config/prometheus` → container `/etc/prometheus`，type=bind、RW=false；数据为 `/srv/dell-data/ops/prometheus` → `/prometheus`，RW=true。仅inspect Mounts，未读取Env/Cmd/healthlog。
- 配置及rules目录root:root0755，prometheus.yml0644；真实rule_files为`/etc/prometheus/rules/*.yml`，目前owned公开规则文件只有infra.yml。
- 真实prometheus.yml SHA256：`35b0a682e8cef2802cd871982e442614e67ae3313f39945ace2591879f508c04`。不拿旧10.63配置覆写此文件，只追加新`rules/pve-local-backup.yml`。
- 现役promtool3.16.0/linux-amd64；container内`/bin/promtool check config /etc/prometheus/prometheus.yml`退出0。
- **实际web.enable-lifecycle=false**，本机公开GET runtimeinfo有reloadConfigSuccess=true/lastConfigTime2026-11-09T06:30:41Z。HTTP `/-/reload`未启用，root已明确批准改用Prometheus官方SIGHUP。installer锁定原container ID/imageID/PID/StartedAt/restarts，native校验后只对精确ID发`docker kill --signal=HUP <ID>`；不启flag、不restart/recreate。失败仅移除本次新owned文件，再对同IDHUP回退并确认新group已撤回。

这些检查只请求公开配置的rule_files、目录、SHA和selected flags，不读AM secret或通知凭据。

## 指标与规则

与collector角色已对齐`dell_pve_local_backup_{enabled,last_success_timestamp_seconds,last_run_success,running,state_valid,verified_guest_count}`。collector另有current_run_state（verified0/running1/failed2/unknown3）等；运行时last_run_success继承最近已完成结果，较新failure可置0。verified_guest_count是当前run进度，新run可0..11，所以**只在启用前要求11，运行中不因count不足11告警**。

三条规则固定site=dell-t630、role=pve、severity=warning、for10m：

| alert | 触发范围 |
| --- | --- |
| PveLocalBackupFailed | jobenabled/statevalid、running0、最近run失败或currentstatefailed；不把首轮running当失败 |
| PveLocalBackupStale | jobenabled/statevalid且最近verified成功距今超过36h |
| PveLocalBackupStateInvalid | jobdisabled、stateinvalid，或六项required telemetry缺失 |

输入由同一PVE采集series提供，无新身份label或archive路径。规则max消除scrape附带重复标签，输出site/role/severity固定，不包含路径/凭据。若站点以后有多个独立PVE，应先审scope，不能扩用此单机max表达式。

现有Lark桥及AM路由是告警名白名单，需root在其owned模块纳入上述3名并原生验证，**不能只装Prom规则就声称Lark可送达**。本目录不改receiver、不读hook/token、不发测试消息，也不转发业务日志/注释URL。

## 安装器门禁与范围

默认不带execute只本地SHA计划，不联网。真正执行需root明确270窗口、 reviewed候选SHA及`--lark-whitelist-reviewed-ready`，后者是人工checkpoint，不会替代实际白名单验收。

1. assigned270 root、hostname/19.70实际IP、数据UUID01b1f302-27be-4fbd-b4af-b8e782d85dea、roottrusted路径、原RO configbind与原configSHA必须匹配。
2. 写前通过Prom查询得到唯一六个series：enabled1/statevalid1/lastsuccess1/running0/verifiedcount11、成功时间非未来且<36h。由此首11verified且jobenabled后才安装，避免初始人工测试触发通知。
3. 固定目标`/opt/dell/ops/config/prometheus/rules/pve-local-backup.yml`必须不存在；候选<=16KiB，SHA精确。新文件同目录临时inode+fsync+replace、root644，不覆盖infra.yml或prometheus.yml。
4. 原container内执行`promtool check rules`与整`promtool check config`；然后固定原容器ID发SIGHUP；轮询本机/-/ready、runtimeinfo的freshlastConfigTime/reloadsuccess及exact新group3names出现。容器ID/imageID/PID/StartedAt/restarts必须前后相同，不Compose/recreate。
5. 失败仅在新文件SHA仍为本候选时删除这个文件，整config复验后对同原ID发HUP并确认group撤回及原PID等不变；第三方漂移拒绝覆盖/清理。原规则/secret配置不读写，不声称自动修未知故障。

未来SIGHUP方案的调用样例（**现在不可执行，尚未270写窗口且必须等first11verified/jobenabled/collector与白名单前置通过**）：

```sh
python3 -I -B alerts-install.py --candidate backup-alerts.yml --sha256 <已审规则SHA> --execute-reviewed-270-window --lark-whitelist-reviewed-ready
```

## 本地验证与失败记录

- alerts-install.py AST/本地plan模式通过，plan没有target/network动作。另5个mock测试通过：精确IDHUP、信号前身份漂移拒绝、信号后PID变化不能通过、回退同ID且group必须消失、首11/jobenabled/running门禁。
- 用本机已缓存官方AMD64 prom/prometheus3.16.0 digest，network=none、read-only、1CPU/256MiB、仅公开候选/合成测试挂载，promtool test rules：**8组通过**。覆盖healthy不触失败、真实failed触发、running继承failure不触发、首轮running0verified不触Failed、jobdisabled、stateinvalid、metricmissing及超过36h。
- 第一次本地sandbox无法访问Docker socket；获准后第一次只读容器因promtool测试需/tmp TSDB拒绝，未产生目标变更。随后仅给/tmp96MiB tmpfs，原read-only/networknone边界保持，8组成功。不以关闭测试凑通过。
- 完整现役config只在270执行原生只读check；候选与整config组合必须在未来安装窗口再由同版本promtool检查，不能用本地旧文件替代。

当前待root：首11verified+jobenabled+指标collector入Prom；三告警名既有Lark白名单；明确270窗口。SIGHUP已获具体方案认可，但本目录仍未实际投递信号或写270。没有远程写，不扩张用户通知目标或备份/外部灾备承诺。

## 通知白名单增量候选（仍未写270）

新增候选：`notify-bridge.candidate.py`、`notify-whitelist-install.py`。前者只在原bridge.ALERTS字典增加3个固定中文说明：PVE本机备份失败、PVE本机备份成功已超过36小时、PVE本机备份任务关闭或状态无效。原LABELS/ROLES/receiver/auth/超时/重试/事件去重等其余源码字节完全不变；原infra/ops/lark-notify/bridge.py和configuration.py未改。

2026-11-09T07:11:23Z实际只读核对：

- 270实际`/usr/local/libexec/dell-lark-notify/bridge.py` SHA=`e4b251653d0ae9822351928d3f04b6d4a0833edbe50ce3e6057edc7de7182f80`，与原本地source一致。
- 实际AMsource `/opt/dell/ops/config/alertmanager/alertmanager.yml` SHA=`ace6e36ff16e86b487523d141859f0bd150883d9e73e05a86c06d0d38a38cd53`，JSON精确等于原本地configuration.render(active)。本地renderer SHA=`18217358ee2c81f0f3a6404ebd95c6e6a4d5a982587175596f73b698e493fb20`。
- configuration.py本来不作为runtime文件安装，部署只需bridge.py；此前按同目录读取不存在configuration.py的预检未完成，没有远程写。后用已审公开renderer在guest内存和现役AM比对，不复制或执行任意source，也不把模块未安装误当业务故障。
- AM activealerts0/groups0、Prom alerts0；nativeunitactive/running、MainPID1457/NRestarts0、TasksCurrent1，19093 established入站连接0。bridge只有内存attempts/delivered/inflight，没有持久待发队列或public状态API；AM未暴露额外queue gauge。**不会读取processmemory或消息内容**；安装器以两次相隔2秒空告警/组+单任务+无连接作为无在途发送门禁，不声称有不存在的可靠队列API。实际window前会fresh再验。

安装器默认plan不联网；真正执行需明确`--execute-reviewed-270-window`和exact candidateSHA、assigned270 root/IP/UUID、source两个SHA和RO AMbind。现AM必须等原renderer(active)，新AM仅一个live alertname regex增加3名，receivers/auth-token路径/grouping/retry等语义完全相同。只备份公开bridge和不含secretvalue的AMsource到root700/600目录；不备份/打开hook/token/LoadCredential值。

部署流程候选：

1. 全部delta与sourceSHA、空告警/在途门禁通过后，CAS原bridge及AMsource（各自原子文件替换；不是跨两文件瞬间原子）。如果第一文件写完第二文件失败，回退允许old/new已知混合态，全部预检后恢复两原文件；未知第三方SHA拒绝覆盖。
2. 锁定原AM containerID/imageID/PID/StartedAt/restarts，执行原容器`amtool check-config`及3组`amtool config routes test --verify.receivers=lark-live`合成标签（无HTTPsend）。
3. 再次空队列门禁，必要重启**仅**dell-lark-notify.service，使新字典生效；原LoadCredential照常，不改unit/secret。要求原私网唯一172.18.0.1:19093及active。native MainPID会改变，不能冒称native进程不变。
4. 对固定原AM containerID发HUP，不recreate；ready及原生reload metrics的新成功时间必须通过，AM identity/PID/restarts保持。新代码SHA/AMsource/接收人不变条件再验，并确认仍无活动告警组。
5. 失败仅对仍属本次old/newSHA的这两文件恢复原bytes，原amtoolconfig验证、必要nativeunitrestart、同AMIDHUP回退。无新receiver、无测试告警/外发请求。回退未实演，实际动作等root窗口。

本地5项测试通过：候选精确3行增量与LABELS/ROLES保持、AM只有regex变化、其它AM字段改动拒绝、3新名active固定中文render、acceptance模式/未知名仍拒。另用官方缓存AMD64 amtool0.34.2，networknone/read-only/1CPU128MiB/合成token，原生check-config及3条synthetic route test全部exit0且只解析到原lark-live，没有网络投递。source/helper/defaultplan AST与SHA计划通过。

顺序：先root审核并落此通知白名单，确认receipt后才装新Prom规则；Prom安装还须首11verified/jobenabled/指标valid门禁。当前首备运行中/计划disabled不代表可以提前启规则。只准备、测试和只读核对已经完成，**尚未上传任何通知候选/写规则/重启native桥/对AM或Prom发HUP**。
