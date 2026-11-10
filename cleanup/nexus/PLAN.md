> 2026-11-10状态覆盖：用户已明确恢复Nexus合并及独立221退役，当前合并完成，执行与最终回执统一见[本次交付](../../completion/20261110-nexus-merge/README.md)和[现行操作手册](../../completion/20261110-nexus-merge/usage-manual.md)。下文为此前准备/暂缓过程的历史，不再是当前许可或现场状态；不得重放其中stage/mount/commit/start。新220还承载导航与deploy-public，须保留其私有设置/keys与原build卷。真实scsi2先有旧安装ISO，须仅卸CDROM配置再唯一移盘，ISO文件保留。最终数据/身份/网络/监控与退役以新回执为准。

> 当前范围（2026-11-08）：用户已确认内存重插/更换并诊断通过，服务器恢复基础检查/补齐与清理。**用户明确暂不迁移、不合并Nexus、不退役221**；当前不执行此计划的stop、冷备关机、move-disk、alias31或target commit/start。root本轮复核12运行实例、15targets UP及6HTTP200，并补齐宿主forward启动守卫；恢复连通不是自动继续历史合并的触发条件。

> 历史记录：11月7日source停服曾被自动审批在执行前拒绝，随后用户“授权短时停机合并”已满足当时知情许可。DIMM_B1/UEFI0058故障和许可均保留为历史；11月8日新的不迁移范围优先。将来仅在用户明确恢复Nexus迁移任务后fresh复核并开具体窗口，不把许可仍缺失或硬件仍唯一阻塞写成当前结论。人工流程见[19操作手册](../../19-manual-operations.md)。

# Nexus并入发布机220：实际准备与切换计划

[17合并架构](../../17-publish-artifact-consolidation.md)仅保留未来目标：在将来明确恢复迁移并验收后才由VM220承担发布与Nexus。本轮220/221独立，本文技术操作均不执行。

最后成功准备状态：**220仅完成Docker/Compose、原2镜像离线导入和私有standby候选；Nexus归属仍为221，合并未开始。未绑定19.31、未迁数据盘、未启动220 Nexus。** 这是已有准备与11月8日恢复读回一致的事实：221原unit/2容器healthy，220仍4CPU/4GiB、无active Nexus或31。本文仅未来窗口参考，不能把准备当切换完成。

## 已选拓扑与资源

主AI已选220主地址`192.168.19.30`，保留`192.168.19.31`作为同一NIC上的Nexus服务alias。OS hostname仍publish-service，PVE显示名保持；管理用220/19.30与原hostkey，31是服务地址，不伪装成原VM221，也不复制SSH hostkeys。

220计划6vCPU/8GiB，来自原220(4vCPU/4GiB)+221(2vCPU/4GiB)的合并分配，不声称额外释放4GiB RAM给其它服务。原Nexus100GiB独立卷移到220 scsi2，挂载/srv/nexus，保留原ext4 UUID239dc45a-b1f3-408b-a8ef-7afa77b52204；build盘/srv/dell-build UUID16dc6067-56ef-4687-a314-edc6421f9ed4保持。不要让两VM同时挂同盘RW。

实际只读结果：二者都是Debian13 AMD64；220原4GiB当前无Java/Node/Gradle构建，系统盘约26.9GiB空闲、build100GiB基本空；221Nexus数据38,490,112B、当前进程内存约1.246GiB/3GiB、gateway约3.6MiB/64MiB。空闲采样不是构建峰值证明。合并后6CPU为共享调度，建议首期一构建并发并限制其内存，Nexus原1.75+.25CPU/3GiB+64MiB caps不扩大；8GiB不代表当前供应商cloud-native XS吞吐档位或性能SLO。

[Sonatype内存说明](https://help.sonatype.com/en/nexus-repository-memory-overview.html)区分heap/direct/OS内存；[现行规模建议](https://help.sonatype.com/en/sonatype-nexus-repository-system-requirements.html)按请求负载给profile。本次只原样搬现有小规模固定3.84.0-03实例，不伴随版本/数据库升级或重调JVM。容器原限额继续，若后续并行构建/仓库增长需另测。

## 两种地址方案比较与已定选择

| 方案 | 优点 | 实际代价 |
| --- | --- | --- |
| 已选：220 primary30+Nexus alias31 | 既有Mac开发配置、Maven URL/书签和下载链接保持，改动服务端可界定 | root须把31的L2源IP归属从221MAC转220MAC，单guest多IP元数据/strict管理helper支持；SourceIP30发布链仍需核对 |
| 未选：仅220/19.30:8081 | 每VM单管理IP，通用helper和IPAM最简单 | 外部开发者/所有active consumer需精确更新；不能盲sed源码/历史/私有备份，旧31客户端会失败 |

实际220白名单Maven/Gradle配置路径目前未发现19.31；只有其fenced client-test240 profile，source19.30/target19.45。不能据此宣称所有外部Mac/开发项目不存在31引用。因此保留alias符合root避免用户端全改的选择。

## 220准备已实际完成

- DockerCE/CLI29.9.3、containerd2.4.2、Compose5.7.0与source221一致，APT模拟拒升级/删除已有包，实际无升级删除；安装期间policy-rc.d临时101抑制autostart并原样恢复。needrestart仅列表，不自动restart其它服务。
- 首次Docker启动前daemon已features.containerd-snapshotter=false、storage-driveroverlay2、live-restorefalse、local10m×3；实际publish-service/classic-overlay2、containers0。
- publisher UID999/GID989组完全不变，不加入docker组，不能写socket；其私钥只stat元数据一致，不读取、不拷贝或wholebackup220。ub本来就是sudo管理账号。
- 原两个公开AMD64镜像以实际image config SHA-ID从221只读save→220load，strictSSH直管道，无pull/tag漂移、不含容器运行数据/密码。legacyload可能不保RepoDigest索引，所以target compose只把2行image改为原实际SHA-ID（不可变、实际OS/Arch复核）。
- 最小13项代码/env/原初始化marker及三新Nexus凭据从221经双strictSSH stdout→stdin直接落220 root700/600 standby，Mac不生成含秘密归档，不复制publisher/SSH identity或运行态DB。
- nonce `cb01b8582f544381b0461001dfa3ccb4`，目录`/root/dell-nexus-merge/<nonce>/{incoming,prepared}`。候选只改assignment/fresh marker的expected_hostname artifact-service→publish-service（IP31/UUID/历史初装事实不变），以及compose两image引用。env/三凭据字节保持，unit内容保持。没有run fresh-init/bootstrap/eula/import。
- 公开目标执行器在220 `/opt/dell/cleanup/nexus/{target.py,relocate.py}`；仅stage已执行。未写active /opt/dell/nexus、未安装unit、未绑定31。

证据：live-inventory.json、consumer-url-locations.json、docker220-prepare-result.json、image-import-result.json、standby-transfer-result.json、target-stage-result.json。

## root接管：冷备、唯一磁盘所有权、alias和资源

root已直接核对现役Qemu.pm源码：target-vmid分支为rename_volume+移除source配置再挂target；**不是保留原盘拷贝**，storage参数不能同时传。实际计划命令：

`qm move-disk 221 scsi1 --target-vmid 220 --target-disk scsi2`

不传store，不加不适用的delete0选项。root执行顺序固定为：**先正常stop源221原dell-nexus.service并确认两容器停止 → 221正常关机并确认stopped → 对已停止的221做vzdump --mode stop → 完成SHA/zstd/VMA校验并再次确认221仍off → 220正常关机并确认stopped → 应用6CPU8GiB与原盘唯一所有权移交**。不能先对运行中的源做stop模式备份、再假定它没有自动恢复运行。原221/220 scsi0与source备份保留，221目标验证后才退役，不立即删。root可用反向move做回退。官方[Proxmox盘重分配说明](https://github.com/proxmox/pve-docs/blob/master/qm.adoc)也说明重分配会移除source条目并重命名匹配新owner；以root已核本机8.4源码为具体语义依据。

Nexus数据库与blob在同一完整原盘中移动，EULA/用户/仓库/加密配置沿用，不能把在线目录复制称一致备份。软件/凭据standby包已提前传好，源停机前root仍需确认source文件未被其它管理动作修改。原数据盘只在一侧挂载，禁止为快而并发启动两个实例。

root网络配套：

1. source221停机退31所有权；target220保留primary30并加alias31/24，默认路由/DNS19.1和默认source30保持。必要时显式route prefsrc30或审查publisher SSH -b30；不改from30受限授权或解除fenced策略。
2. PVE L2 MAC/IP集合220允许30+31，删除221 active归属；GW/bridge既有31HTTP权限移成220component事实，受信VPN10/24无NAT范围保持。child不改PVE/OW。
3. scripts/control.py trust_guest本地已实现additional_ips严格同NIC白名单支持，非待开发补丁；它不自行添加地址。将来用户明确恢复Nexus迁移任务并fresh核硬件/管理后，root按唯一角色所有权更新plan：220保留primary19.30并声明additional_ips=["192.168.19.31"]，221不得同时作为active角色claim31。随后fresh验证声明/实际同NIC地址与受信hostkey，未知地址、重复声明/实际重复和跨NIC仍拒；expected_ip和SSH管理固定primary19.30，不关闭strict检查。SSH31将呈现220自身key，这是机器所有权改变，不拷221key伪装；禁止用dell-vm221 alias连新220。
4. exporter220继续只在30:9100，Prom移除221物理节点target，不能用31再假造第二台节点。把dell-nexus及31:8081本地HTTP加入220实际collector，保留220原policy；更新backup/onboot/role/IPAM现行数据模型，不重复计算221预算。

## root完成handover后：应用精确命令

下列步骤尚未执行。target.py只允许assigned220/MACbc:24:11:2a:01:ad、双IP30/31、classicoverlay2及足够6CPU8GiB，且必须显式root handover确认。它不修改NIC/alias/PVE；当前阶段不要执行。

```sh
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py mount --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py commit --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py start --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
```

mount仅用已存在UUID，核原数据UID200/GID200与非空db/blobs树，不format/chown树，不踩build盘。新增fstab只该UUID/srv/nexus，nofail允许publisher在仓库盘缺失时仍管理，Nexus unit RequiresMountsFor/BindsTo与UUID门禁防根盘误写。commit先全量SHA校候选、拒已有active Nexus安装，安装3secret/env/marker600和公有code，仅unit enable不start，执行原manage check+unit原生验证；start有限等2healthy/原imageIDs与secret私有hash相同，不pull/build/init。

## 最终验收与回退

- 220新DataUUID239与UID200、原2imageID、classicRootDir、资源caps/日志/PIDs、mountgate监督；同31URL从LAN/VPN原用户可访问。
- GET-only验证当前全部repo与原49GAV/234主SHA、35metadata语义/1076checksum（新合法数据不能删回49）；EULA已accepted、原admin/reader/publisher credentials与roles/group同一实例，匿名拒绝。仅验证，不执行import/upload/rebuildMetadata或重置用户。
- publisher key只stat元数据一致，UID999不在docker组/不能触socket，target19.45/source30/forced命令和fenced状态保持；不发真实业务发布命令或启动Java业务。
- 物理220只有一套SSH身份与正确双IP元数据、221物理metrics已退役，Ops/backup/现行plan/docs一致，再由root签退役。source221OS盘/备份不立即删除。

如失败：停止220 Nexus并禁其自启；root先撤31 alias，正常停220，反向把scsi2原盘移动回221 scsi1，恢复source221原IP/metadata/监督；数据和身份使用原盘，不从旧初始空库重新导入。target220只保留待审新Nexus文件/软件，不能wholebackup它或清publisherkey；移除仅本次Nexus unit/路径应再用manifest界定。回退未执行，不能把计划当恢复证明。

当前源应用保持：Penpot历史ff1783e不升级、Java业务不部署；Mac外部探针用户明确不需要，现行和后续均不安排配置/恢复。此文不因硬件恢复而启动新的迁移。
