# 整改后生产Docker运行时只读复扫

采集完成：2026-11-06T06:46:11.389936+00:00。范围仅七台指定来宾、旧审计中记录的26个生产容器名称；状态为 **completed-no-runtime-findings**。这是采集时点的运行事实，不替主AI签收验收用例，不代表全部38项通过。

| VM | 生产容器 | healthy | CPU共享上限和 / VM vCPU | 内存上限和 / VM GiB | 角色systemd |
| --- | ---: | ---: | --- | --- | --- |
| 200 | 1 | 1 | 5 / 6 | 12 / 16 | simple / running / on-failure |
| 201 | 3 | 3 | 4 / 4 | 5 / 8 | simple / running / on-failure |
| 210 | 4 | 4 | 2.5 / 2 | 2.625 / 4 | simple / running / on-failure |
| 221 | 2 | 2 | 2 / 2 | 3.0625 / 4 | simple / running / on-failure |
| 250 | 11 | 11 | 12.5 / 6 | 11.9375 / 16 | notify / running / on-failure |
| 260 | 1 | 1 | 2 / 4 | 1.5 / 4 | simple / running / on-failure |
| 270 | 4 | 4 | 2 / 2 | 2.625 / 4 | simple / running / on-failure |

## 复核结果

- 26/26生产容器running、healthy、未处于restarting/OOM状态，实际镜像全部linux/amd64。实际image ID均与旧审计或Penpot已审11服务contract一致；23个官方引用固定registry digest，3个自建Penpot镜像配置直接固定实际SHA image ID。
- 26/26拥有CPU、内存和明确PIDs上限；数据/Nexus/Ops为1024，NAS256，Penpot按已审服务contract逐项匹配。local日志均10m×3；无privileged、Mac目录或docker.sock挂载。
- 七个角色数据挂载点/实际文件系统UUID与当前plan精确一致，原持久数据绑定source/destination/RW保持。CPU/内存上限与旧批准预算保持，容器内存限额总和均不超角色VM预算；这些不代表实时可用内存或应用并发SLO。
- 七个角色unit均enabled、active/running、Restart=on-failure，使用持续进程类型，并BindsTo Docker及角色数据mount，RequiresMountsFor覆盖实际数据挂载点。Penpot已为Type=notify、11/11 healthy；NAS现在也明确BindsTo Docker。没有再次注入故障、停止Docker、重启或缺盘负测。
- Ops原生dell-lark-notify.service当前active/running、Restart=on-failure；此前已核实96MiB上限作为额外0.09375GiB计入Ops预算，容器2.625GiB加桥后约2.71875GiB，余1.28125GiB供OS/runtime共享。本次不读取其凭据/argv/env，不重发Lark；实际双phase code0/active静态IPAM证明仍引用既有独立证据。
- VM210容器CPU上限合计2.5而VM2vCPU；VM250合计12.5而VM6vCPU。这是同一VM上的共享最大上限，**不是CPU预留**，不承诺同时达到各容器上限。该边界与旧审计相同。

## NAS独立QA排除

NAS只读名称筛选发现1个`dell-nas-sys001-`前缀独立QA容器，名称在JSON `excluded_qa`。它不计入26生产容器，也未对它执行inspect、读取健康/状态/Env或清理。NAS唯一生产对象仍为`dell-nas-jellyfin-1`；其本次实际healthy和数据UUID已单独采集。

## 范围与证据边界

只读命令白名单：Docker本地Unix socket info（服务/OS/driver/root metadata）、固定旧生产name的格式化inspect（状态/资源/log/ports/security/mounts/networks）、实际image ID的image inspect（ID/OS/Arch/RepoDigests）、固定unit的systemctl show（状态/restart/type/mount dependencies）、固定挂载点findmnt。没有请求Env、Cmd、health test/log、任意labels、日志、私有文件内容；没有来宾/PVE/source/known_hosts写入。

旧[container-runtime-final-audit.json](container-runtime-final-audit.json)及MD原样保留，包含旧的真实发现。本次[JSON](container-runtime-post-remediation-audit.json)记录原审计SHA、collector SHA及每项检查；collector首次本地汇总遇旧Penpot服务别名`import`与contract `penpot-import`不一致，修正本地映射后完成，同一只读范围未扩大、无目标更改。

功能恢复/HTTP/源保留与安全负测不重复：Penpot引用`infra/penpot/runtime/health-supervision/evidence/final-runtime-contract.json`及原故障/重启证明，Ops/Lark引用`lark-notify-final-audit.json`与`lark-notify-send-acceptance-pair.json`；NAS隔离QA的最终结果由主AI独立签收。本期正式Java仍仅runtime，Mac外部探针仍按用户决定停用。
