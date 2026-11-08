# 当前实施进展

更新：2026-11-08（Asia/Shanghai）。用户报告内存已重新插拔/更换且诊断通过；本boot EDAC CE/UE0、RAIDOptl。既有基础服务现已恢复并分范围核验，**不再按11/07 POST停机状态描述当前现场**。未独立收集完整物理诊断报告或证明单条DIMM/物理关机唯一根因，长期稳定性仍不能仅凭一次开机保证。

当前用户范围：补齐既有基础服务、盘点可确认多余项；明确不迁移，不合并Nexus/退役221，不启动Java业务。Mac外部探针明确不需要，移出当前及后续待办，保持停用。

## 本次实际观察

| 领域 | 11/08基础运行证据 | 限制 |
| --- | --- | --- |
| 宿主/实例 | 12实例运行、3模板保留；failed units空、RAIDOptl | 当前boot计数正常不等于独立硬件根因确认 |
| 宿主网络 | 带IP桥forwarding被ifupdown2置1，3owned guard恢复双栈全0；仅原bridge ACL表 | interfaces/routes/ACL不变，无network reload或guest restart；新guard未借重启扩验 |
| 数据200/201/210 | UUID/ext4/rw匹配，8容器全部healthy/RestartCount0 | 未重新登录DB或核namespace/内容/权限全量一致性 |
| Java230/240 | JDK21.0.13可用、finger账号存在、无Java进程，旧五业务不自启 | 未重新完成finger身份编译烟测；不部署业务 |
| 220/221 | 220原standby、无31或Nexus栈；221原UUID/独立31、2容器healthy | 未查全部GAV/EULA或执行迁移、冷备、回退 |
| Penpot250 | 原UUID、11healthy/原镜像、worker ready/idle、Gitff1783e clean | 未重新MCP/设计内容/全部素材复验 |
| NAS260 | 原2TiB UUID/ext4，OMV/nginx/SMB/Jellyfin运行，原共享策略与样本stat存在 | 未读文件字节或做SMB权限矩阵、播放/真实设备测试 |
| Ops270 | 4healthy、systemrunning/failed[]，15/15targets UP、Prom/AM alerts空，textfile更新，Lark原unit active | 没有发送Lark测试或开启Mac探针；15UP不是应用全验 |
| HTTP入口 | PVE/Nexus/Penpot/OMV/Jellyfin/Grafana共6入口200 | PVE自签TLS探测只证可达，非证书认证通过 |

主证据：[核心服务](recovery/20261108/core-services-audit.json)、[媒体工具](recovery/20261108/media-tools-audit.json)、[Ops](recovery/20261108/ops-audit.json)、[网络后检](recovery/20261108/host-network-postcheck.json)、[forwarding修复](recovery/20261108/host-forwarding-restored.json)、[清理盘点](recovery/20261108/pve-cleanup-audit.json)。

首轮尚未轮到的240/260等曾no-route，Penpot部分starting；随后自然onboot完成而健康，没有为此更改网络或重启。原首轮记录保留，不追改为始终全绿。本次未发现必须额外安装/重部署的基础缺项，清理建议只做依赖核对，不盲删资源。

## 保留的历史和未验收项

11/07 02:35:01完整验收、02:44:29最后PVE操作、UEFI0058/B1 SEL事故按历史保留。旧38项26历史passed/12pending不改变；原严格6REC保留pending并逐项说明部分证据或用户延期，不把本次基础恢复当全量数据/硬件/灾备验收。

Nexus待办原因现为用户明确暂缓迁移，不是再次等待短停授权或当前硬件不可达。真实电视/PS4/PS5/4K HDR/GPU、混合负载、独立长期备份/RPO/RTO和业务SLO仍未验。机内监控与T630同故障域；Mac外部探针用户不需要，不作为故障或未来承诺。
