> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../../11-live-handoff.md)；旧初始化器不得重跑。

# Penpot250 持续健康监督

当前已上线并完成真实验收：**11服务全部running/healthy，systemd notify active/running/enabled，系统running且无failed unit。** 唯一事实汇总为 `runtime-status.json`；`PLAN.md`保留方案与执行边界。`deployment-lock.json`保留批准时原始合同字节，其准备标签不表示当前服务未安装。

目标VM250 `10.63.30.30`，LAN `http://192.168.21.22:9001`。只新增 `/opt/dell/penpot/runtime/health-supervision` 与 `/etc/systemd/system/dell-penpot.service.d/20-health-supervision.conf`，原7个部署/guard/compose/logging文件和base unit字节保持，未改tracked source Git、身份或设计。源Git仍精确ff1783e且clean，两个本地改造提交完整保留。

## 运行方式

`supervisor.py`启动前验证固定来宾、真实UUID mount、DockerRootDir `/srv/penpot/docker`、classic overlay2、Git/旧包SHA、镜像实际ID/AMD64和精确11服务。合并既有fresh compose与本目录overlay，固定 `--no-build --pull never`，全11健康后才发READY。

运行中每5秒检查服务集合、状态/健康、实际image ID、PIDs/CPU/内存和挂载合同；存储/Daemon身份同时受门禁约束。异常先停止固定整组再退出，systemd间隔30秒恢复，900秒最多3次。停止仅操作已知正在运行的固定对象，不依赖数据盘上compose可读，不删除volume。SIGTERM清理与ExecStopPost幂等后备，管理员stop不会被当作应自动重启的故障。

三个自建镜像的配置直接引用实际SHA image ID，guard还核对源引用解析ID，不能仅信mutabletag。11容器均有明确PIDs上限；CPU/内存保持既有预算：CPU上限总和12.5/VM6vCPU、内存11.9375/VM16GiB。上限不是预留，也不是并发SLO承诺。

## 健康探针边界

frontend使用现有NGINX stub_status 200+标志；backend/exporter各自readyz要求200/OK。管理台没有专用health端点，严格核对已实测的无凭据307登录origin/route/唯一callback；它证明auth路由可用，不能冒充授权管理操作。MCP使用公开initialize有效结构并立即DELETE临时session，实际授权只读另行验收，HTTP404一律不能通过。

DNS启用原生hosts-file，为保留域名dell-penpot-health.invalid配置TEST-NET地址192.0.2.53。探针只验证本地静态记录，不让公网故障触发整组恢复。固定同镜像在network=none、不可达上游、非root只读临时容器中正例/错名反例及精确helper均通过；自有临时容器/scratch已清理。其NET_BIND_SERVICE是公开binary所需、与现役相同的最小能力；未开放临时网络。

## 实际验收

- 本地14项Python guard/状态机/停止边界和8项Node协议/错误响应/重定向/session清理测试通过。
- 新监督器首次完整11健康、notify ready后，仅精确frontend容器发过一次KILL。05:29:42Z故障、05:30:20Z观察11全部停止与auto-restart、05:33:55Z观察自动恢复11健康，NRestarts0→1、监督进程/Invocation改变；没有人工恢复start。时间是观察记录，不是已批准RTO。
- 故障后完整内容/身份/MCP回归通过，再仅VM250正常guest reboot一次。boot ID从37a6e06d…变6229b125…，原hostkey严格SSH成功，05:43:27Z观察开机自动notify11 ready，没有人工start。
- 原3设计完整data SHA、stats/revn/vern保持；原971媒体SHA全部存在。当前存储973个文件逐路径每字节SHA保持；额外2个精确对应此前已批准的专用副本官方export/reexport（7436f90e…、864b68f5…），没有删除素材。
- 7份新身份/分配文件hash保持，身份文件0600和既有UID/GID保持，实际owner登录/MCP读取也通过。
- 重启后MCP新会话先high_level_overview再受权只读专用file/page；无key设计读取被拒。没有设计写，未输出key、session或HTTP正文。
- Mac原生curl五项LAN检查全200，HTML/改造JS/CSS/空默认口令JSON SHA与原Git部署验收一致；backend ready正文只在进程内核对OK。

## 证据入口

| 文件 | 证明内容 |
| --- | --- |
| evidence/final-runtime-contract.json | 当前11 Health/PIDs/image ID/AMD64/资源/挂载、unit、权限和systemd running/failed=[] |
| evidence/frontend-fault-issued.json | 唯一精确frontend KILL回执，防重复标记 |
| evidence/frontend-fault-recovery-proof.json | 停整组、自动恢复、同11对象重新启动及镜像不变 |
| evidence/post-reboot-snapshot-comparison.json | 3设计完整内容/修订、973与原971媒体、身份、Git、旧unit和新boot |
| evidence/media-extra-attribution.json | 原971保护与额外2的明确批准活动归因 |
| evidence/post-reboot-MCP-readonly.json | 受权只读上下文与无key设计读取拒绝 |
| evidence/post-reboot-LAN.json | 原生LAN200、Git改造静态SHA、空默认口令 |
| dns-local-network-none-validation.json | DNS不依赖上游的实际隔离正反例 |

第一次静态systemd verify因standalone默认路径遗漏既有fstab generator mount而停止，未带失败进入应用；使用现役Manager真实UnitPath后verify0/零诊断，不伪造mount、不运行generator。历史失败证据保留。

运维继续通过 `systemctl stop/start/restart dell-penpot`；不要绕过监督裸起原compose，不重新调用fresh init生成身份。升级必须显式审查并更新本目录image-ID/代码SHA合同与验证，不能只替换tag或改tracked业务源码。源Mac、PVE、模板、其他来宾未改，没有额外负载测试；独立设备灾备、正式SMTP/HTTPS、业务峰值与正式SLO/RPO/RTO仍是其他范围。
