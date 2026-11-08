# 2026-11-08 媒体与工具基础服务只读恢复检查

采集结束：2026-11-08T12:19:39.230515+00:00。范围VM220/221/250/260，严格复用已核SSH info，无known_hosts写入；只读元数据和原匿名GET。用户本轮不迁移、不合并Nexus，不启动Java业务。

| VM | 本次观察 | 结论 |
| --- | --- | --- |
| 220 | 4CPU/约4GiB，唯一19.30；build UUID正确，Docker active但无Nexus容器/active路径 | 原standby状态保持，未合并/未加31 |
| 221 | 独立19.31、原UUID；原unit running/NRestarts0，2healthy/原镜像IDs，statusGET200 | 本范围基础健康通过 |
| 250 | 原UUID；notify最终running、11healthy/原镜像IDs；首页200、workerready200/state ready/activeTasks0，Gitff1783e clean | 自动开机启动完成，无更新或手动启动 |
| 260 | 原2TiB UUID/ext4；OMV/nginx/SMB/Docker/JF原unit运行，JFhealthy；OMV200/JFhealth200 | 本范围基础健康通过 |

首轮220/260尚未可达、Penpot后端/worker为starting(9healthy)；按root提供的onboot次序有界等待后再次只读，最终上述全部就绪。首轮记录保留在JSON prior_observations，没有将开机队列判故障，也没有手动启机。

NAS三share21/19/127+10.66.66/24白名单及writer/reader/guest策略保持，3个原合成共享fixture和原MP4仅stat元数据均存在；未读文件内容或密码，未发认证/写请求。publisher原source30/target45/受限profile保持；新发布私钥仅stat为UID999/600/419B，未读/导出。fenced实际目标240策略不在本次机器范围，因此未独立重测，不以profile正常声称发布功能通过。

**本次未观察到需要补齐的具体项。** 所有UUID/FS、预期容器健康/镜像和原匿名GET均合本范围；不因此签硬件长期稳定、全部业务或灾备。root报告本bootCE/UE0与RAIDOptl、用户报告已重新插拔/更换并过诊断，物理维修细节与长期观察仍由root/用户记录。

限制：Nexus仅健康/运行数据，未认证查EULA/GAV或重建/导入；Penpot未MCP/设计内容复验，未按main文档更新历史ff1783e；NAS未读取内容/密码或执行SMB矩阵/真实设备验收。没有任何stop/start/install/migration/backup操作，不访问CF，不备份220。

所有命令类别：findmnt固定挂载、systemctl show固定unit、Docker显式字段inspect(无Env/Cmd/healthlog)、git只读HEAD/status、匿名GET原健康路径、testparm三share精确字段、原fixture/发布key stat；不保存HTTP响应正文。机器可读证据见[media-tools-audit.json](media-tools-audit.json)。
