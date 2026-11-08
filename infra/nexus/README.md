> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# Nexus 新实例与 hosted 应用数据迁移

更新：2026-11-06。VM221 `artifact-service` / `10.63.30.20` 运行固定AMD64 Nexus **3.84.0-03**。用户已明确同意新实例EULA，主AI接受并GET确认；不是通过扩大权限或跳过许可解决上传403。

目标使用独立admin、reader、publisher。应用制品通过REST导出/导入，**没有旧H2、旧用户、旧密码、旧上游认证或proxy配置迁移**。Mac源保持运行。当前数据导入、权限与仅两容器重建/来宾重启持久化验证均已完成。

## 实例与入口

- 数据：`/srv/nexus/data`，UID/GID200；独立ext4 `/srv/nexus` UUID `239dc45a-b1f3-408b-a8ef-7afa77b52204`。
- Docker：本机rootful/classic overlay2；分配IP、hostname、UUID逐次门禁，拒PVE和远端Docker。
- LAN入口：`http://192.168.21.22:8081/`，由已批准宿主规则映射；容器内部Nexus不直接发布端口。
- 新管理凭据由目标本机API读取 `/root/dell-nexus-secrets/admin-password`，0600；不放argv、普通日志或证据，不为本次导入回传Mac。用户账号密码没有被导入过程改变。
- `dell-nexus.service`健康监督完整Nexus/gateway两服务，RequiresMountsFor/BindsTo和UUID门禁；两个容器restart=no；pids_limit=1024（实测Nexus73/gateway3），内存/CPU与既定预算未扩张。不要用裸Compose绕过。

## 应用级数据范围与摘要

源通过Mac loopback **匿名GET hosted**仓库清单/组件/资产，没有调用proxy/group内容或任何旧外域。源有5个hosted，数据仅在本地 `imnull-releases`；它不是外部nexus.imnull服务器。

| 范围 | 数量/策略 | 结果 |
| --- | --- | --- |
| Maven组件 | 49，15种版本均非SNAPSHOT | 目标GAV集合完全相同 |
| POM/JAR/module主制品 | 234 | 逐项实际SHA256与源相同 |
| Maven元数据 | 35 | Nexus服务原生manual task再生，坐标/版本集合全部相同 |
| 校验文件 | 1076 | 全部验证为目标实际资源摘要；936主制品派生文件字节相同，140元数据派生文件因再生不同 |
| 全量源资产 | 1345，13,586,516 bytes | API摘要、实际SHA256、GAV/maven2分类/扩展逐项保留 |

源应用数据包为 `private/nexus/application-export/hosted-assets-export.tar.gz`，11,955,089 bytes，SHA256 `51489673546e903e6af02b28c93d1e370c32252d1e70f7a9265c8bc9751c416d`；不含H2、用户或认证。

目标创建同名 `imnull-releases`，版本策略 **RELEASE**、写策略 **ALLOW_ONCE**。仅上传234 primary，任何已存在不同SHA都拒绝覆盖。源清单SHA `1157b5a425d1ec0a35bbca8ca3fe65413473a00db7d3bd4eaa6da6e7326679cc` 同时作为请求ID；相同请求第二次实测 **added=0 / already_matching=234**。

## 元数据再生的明确差异

直接REST PUT主制品不会自动维护全部Maven客户端元数据。使用已安装官方UI API核实任务类型/字段后创建manual、严格限定 `imnull-releases` 的 `repository.maven.rebuild-metadata` 服务任务，读回持久scope再执行；唯一缺项另以精确 `com.sargia.finger:gradle-conventions` GA任务处理。两个任务均lastRunResult=OK，没有修其他仓库。

35份metadata的字节/lastUpdated不同，不能宣称逐字节迁移。完整版本集合相等；另有3个服务再生latest/release变化：

| GA | 源latest/release | 目标服务再生 |
| --- | --- | --- |
| `com.sargia.finger:ums-api` | 1.0.0 | 1.0.1-omva |
| `com.sargia.finger:auds-api` | 1.0.0 | 1.0.2-omva |
| `com.sargia.finger:broker-api` | 1.0.0 | 1.0.2-omva |

固定版本主制品字节不变；动态LATEST/RELEASE消费按这些已记录差异解释。元数据及派生checksum不从源直接覆写来伪装一致。

官方依据：[Sonatype Tasks](https://help.sonatype.com/en/tasks.html)、[Maven Metadata](https://maven.apache.org/repositories/metadata.html)。任务schema、配置和结果以目标实际Nexus3.84随附UI/readTypes与收据为准。

## 组、角色与阶段权限

`finger-public` 仅包含本地hosted，优先顺序：

1. `finger-releases`
2. `finger-snapshots`
3. `imnull-releases`

没有加入任何proxy。reader和publisher对legacy `imnull-releases`只追加browse/read，实际GET摘要正确，PUT/DELETE均403。

当前用户决定正式Java只交付运行基础，因此 `dell-publisher` 是**测试发布身份**：

| 资源 | reader | publisher |
| --- | --- | --- |
| `finger-releases` | browse/read | browse/read，无add/edit/delete |
| `finger-snapshots` | browse/read | browse/read/add/edit，无delete |
| `dell-acceptance` | browse/read | browse/read/add/edit，无delete |
| `finger-public`、`imnull-releases` | browse/read | browse/read，无legacy写/删 |

没有创建正式写账号或更改账号密码。`bootstrap-new.py`预期权限已同步，后续重跑不能恢复正式release写权限；release格式测试版本应走MIXED的dell-acceptance，不能为方便测试扩正式权限。正式release negative由主AI在220专用坐标独立留证。

## 网络与秘密边界

Nexus只接internal backend，默认无外网路由；gateway只连接ingress和backend、挂载只读固定上游配置，没有秘密/数据/Docker socket。REST管理和所有上传校验仅在221本机loopback，新admin只在Authorization header内存中使用。

新实例默认公共proxy即使存在，也不表示已授权使用；它们不进入managed group，本次所有动作external/proxy请求数为0。不要解除internal网络来让旧proxy可用。

## 当前脚本与证据

- `fresh-instance.py`：真正空目录与新实例identity marker，不伪造restore receipt。
- `bootstrap-new.py`：独立账号/新仓库及当前阶段最小角色，不扩大正式写权限。
- `application-import.py`：hosted主制品导入、同源摘要验证、最小组/角色更新、服务元数据/校验/权限验收；所有秘密本机0600。
- `rebuild-import-metadata.py`、`rebuild-specific-metadata.py`：官方UI-native服务任务，manual且scope读回校验。
- `acceptance-publish.py`：220专用合成制品发布/读取/拒绝验证，由主AI控制。
- `manage.py`、`install-mount-gate.py`：持久化门禁与健康监督。
- 早期 `backup-source.py` / `restore-target.py` 是已退役的冷恢复迁移方案，本次未运行。

[导入汇总](application-import-summary.json) 与 [逐项证据](application-import-result.json) 包含234主制品新asset ID、35再生差异、1076校验、初始上传与同request重试、当前最小角色。目标私有收据存 `/root/dell-nexus-import`；没有密码值。

源旧数据、账号和进程保留。HTTP只LAN阶段；域名/HTTPS及独立长期备份目的地由主AI按用户后续安排，不以同机副本冒充灾备。

## 重建与来宾重启持久性

主AI确认220所有写入结束后，仅停止dell-nexus unit，以已审base+mount overlay、pull=never、force-recreate重建Nexus/gateway，**未删除卷/数据目录**；随后仅来宾221正常重启。

旧boot ID `340fcd0f-da9b-42ee-95a9-e94408076e61` → 新 `ca932a9c-6293-414d-a0b2-b0bbe73a3730`，两个容器ID改变且重建后ID在boot后保持。systemd active、两个容器healthy，classic overlay2及新数据UUID保持；新身份文件、EULA accepted、仓库/组/角色配置保持。

重建/重启后再次49 GAV、234主制品SHA、35元数据语义和1076目标资源checksum全部通过，旧库写/删403与finger-public本地读取正常。主AI的dell-acceptance合成制品 `com.dell.acceptance:repo-persistence:20261106041801` 的JAR SHA仍为 `baa80d112a9a144b7ffbb3e71bc202b0e231eb71c9a0ef0154dcc55b2865ea59`，没有删除或覆盖该库数据。

初次post检查在HTTP已200但Docker健康探针仍starting时过早失败，验证程序已改为有界等待两服务healthy，随后完整复验通过；没有通过修改数据/权限掩盖问题。证据：[重建重启结果](rebuild-acceptance-result.json)。
