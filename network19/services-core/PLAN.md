> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# network19 Core当前执行合同

最新用户范围：不部署任何Java业务程序，仅root另指派单一验收模板。该范围覆盖此前Java stage/上线计划。240五应用已stop/disable、cgroup空，active监控仅base3/HTTP0，Publisher始终baselinefalse；新release/fresh Nacos私有candidate仅held备份，未publish/activate/E2E。

Data20019.10/mysql healthy与原auto.cnf身份保持；Data20119.11/nacos-redis-rabbit healthy且实际nacos_prod连接来源19.11到200 ownDB；Data21019.20四基础容器healthy/auto.cnf身份保持，MYSQL_HOST=mysql/DockerCIDR17218不改。Nacos两@%与ownDB权限/password/namespace/vhost保留。3条Java19.45 Host同认证和18逐表DML预增已完成但未使用、不伪造CURRENT_USER连接验证、旧Host保留、无retire。

22019.30/24019.45只迁实际installed-derived公开program/profile/policy/from，privatekey仅220、publickey/keyalias保持，policy baselinefalse。原不可变release和Root600配置不修改，未启业务。错误sudoers路径native check失败保留，实际dell-publisher-test240及全局visudo/sshd、新SHA/policy/from随后只读验证全过。

12role基线由Core统一准备，完成的actual monitoring：200/201/210/220/221/230/231/232/240/260，新IP9100精确listen、collector新鲜采样及本机metrics200；正式App一直未启动。230/232 root计划内临时shutdown/reboot及QGA可信hostkey更正不当故障。250仅standby stage，270仍旧IP运行，均等root明确窗口。

Ops270 active census证实只有env SERVICE_IP、guest-node targets及基线health/listen有旧privateIP；long-lived manage/marker/policy/bridge/unit无旧10.63字面量。AM17218.0.1:19093/native只接受.3、固定四container地址/secrets/active mode不改。amtool/promtool及现役bridge synthetic64+syntheticURL check-only全0，无真实Webhook/token读取或外发。PVE文本指标通过QGA VMID270与固定textfile路径，无IP字面量，host实际核对归root。

剩余Ops流程：root给窗口→Core仅quiesce四容器（native Lark不stop）→root OScommit19.70→Core在quiesced下atomic12targets+exact private-env→原supervisor4healthy→270monitor→新地址Prometheus targetsUP/textfile/Grafana/native bridge只读验证。Site maintenance silence保持，最后root确认解除，禁止验收firing/resolved消息。

可复用helper入口、Root600收据/备份/回退限制见RUNBOOK与STAGE-230。OS/PVE/OW始终root负责；Core不blind改known_hosts。source同步副本prepared/source-commonprofile由root全12完成后统一同步，初始inventory/旧evidence保持不可变。
