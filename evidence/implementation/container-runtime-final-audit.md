# Docker 来宾最终只读运行审计

采集完成：2026-11-06T04:38:44.785395+00:00。范围200/201/210/221/250/260/270，26容器。状态为 **completed-with-findings**，没有把全部容器运行中视为全部验收通过。

| VM | 容器 | healthy / 无health | CPU上限和 / vCPU | 内存上限和 / VM GiB | systemd |
| --- | ---: | --- | --- | --- | --- |
| 200 | 1 | 1 / 0 | 5.0 / 6 | 12.0 / 16 | running / on-failure |
| 201 | 3 | 3 / 0 | 4.0 / 4 | 5.0 / 8 | running / on-failure |
| 210 | 4 | 4 / 0 | 2.5 / 2 | 2.625 / 4 | running / on-failure |
| 221 | 2 | 2 / 0 | 2.0 / 2 | 3.0625 / 4 | running / on-failure |
| 250 | 11 | 5 / 6 | 12.5 / 6 | 11.9375 / 16 | exited / no |
| 260 | 1 | 1 / 0 | 2.0 / 4 | 1.5 / 4 | running / on-failure |
| 270 | 4 | 4 / 0 | 2.0 / 2 | 2.625 / 4 | running / on-failure |

26个容器均running、实际linux/amd64；23个运行引用固定digest，3个Penpot自建镜像以tag引用且记录实际image ID。全部具有CPU/内存上限、local日志10m×3；全部数据挂载UUID与plan一致，无Mac或docker.sock挂载、无privileged容器。镜像ID/ref/Arch、重启计数、CPU/内存/PIDs/log/ports/mount RW/caps/networks和systemd挂载关系见同名JSON。

必须保留的差异：

- Penpot frontend/backend/admin-console/exporter/dns/mcp六服务没有Docker Health状态。外部功能验收不由本次“running”代替。
- 除NAS Jellyfin明确PidsLimit=256，其余25容器PidsLimit=null，未配置显式容器级PIDs上限；这不等于已证明整个来宾不存在继承限制。
- Penpot的dell-penpot.service实际Type=oneshot、RemainAfterExit=yes、active/exited、Restart=no，11容器也restart=no；实际相关unit文件只有该服务。当前有挂载门禁和开机拉起，但不能证明持续监督和故障自动恢复。
- 210与250 CPU上限和超过VM vCPU。这些是共享上限而非预留；不能承诺各容器同时达到上限。所有角色单容器CPU/内存与内存上限总和均在VM预算内。
- Penpot worker/import当前image ID匹配此前preload证据；frontend为后续commit-tag新ID，已捕获，不能拿旧frontend preload ID作为本次来源证明。tag不是不可变digest引用。
- NAS BindsTo包含媒体mount，Docker仅在Requires内；与其他持续监督栈的Docker BindsTo不同。没有为验证这个差异重启Docker。

所有来宾只执行格式化白名单info/inspect、systemctl show和findmnt；没有请求Env、Cmd、健康检查test/log、labels任意值或日志。没有来宾/PVE/模板写入，没有修改known_hosts，没有启停或额外负载测试。Nexus源导入与240发布演练未触碰。
