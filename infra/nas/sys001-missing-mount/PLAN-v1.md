> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# SYS001：专用NAS实例挂载缺失负测方案（仅准备）

**尚未执行。** 当前仅只读检查VM260，未mount/mkfs、未创建QA容器或unit、未停启任何真实服务；不触碰250、PVE或源环境。

推荐在260建立一次性QA Jellyfin实例，复用**已安装的同一挂载守卫原文件和实际unit/compose模板**。无需修改真实2TiB盘、真实unit/UUID、OMV配置或旧生成器。唯一需主AI明确选择的边界是：systemd可能自动修复可用的临时挂载，因此“只卸载”与“卷本身不可用”分别记录，不能把自动重挂当作失败保护通过。

## 已核实的可行性

- 真实守卫 `/usr/local/libexec/dell-nas-check-data` SHA256 `5ba9fd7cfc37d1e7398a454dff0151c516b15a15b93b3c37061f0486d01120fc`，与staged源码一致。
- 它已经支持 `--mountpoint`、`--uuid`、`--minimum-gib`；顺序检查canonical非根路径、真实ismount、唯一findmnt、UUID、st_dev不同于根盘、ext4和容量。QA使用 `--minimum-gib 1`，其余检查完全相同；真实NAS默认1800GiB不改。不复制、替换、mock守卫。
- 实际真实unit SHA `847a0492…ed017ff`，其ExecStartPre调用上述文件，BindsTo真实mount。**现有deploy-jellyfin.sh硬编码真实unit/目录/project并调用默认容量门禁，因此绝不运行它来创建QA。** QA renderer只读取当前unit作为模板并做下述显式身份/路径替换。
- 真实compose SHA `f57289cc…34d86a7`，现有Jellyfin固定digest镜像已缓存、amd64，`create_host_path:false`，restart=no；QA复用这个原compose再合并一个专用override。
- 只读采集时MemAvailable约3.045GiB，根盘可用约25.959GiB；4GiB来宾当前有足够余量容纳最多512MiB QA。执行时必须重测，不能把旧值当保证。
- PID1、dockerd、真实NAS unit主进程的mount namespace相同。QA保持同一宿主mount namespace，**不使用unshare/PrivateMounts/RootDirectory等让守卫和Docker看到不同挂载的方式**。

数据详见 `preflight.json`，参数锁草稿见 `qa-contract.json`。本计划不把检查通过写成SYS001已通过。

## 精确QA对象与唯一允许的变更

新nonce为32位小写hex，每个执行对象都由该nonce派生并登记manifest：

| 对象 | 位置或参数 |
| --- | --- |
| 控制目录 | `/var/lib/dell-nas-sys001/<nonce>`，root/0700 |
| backing file | 同目录 `scratch.ext4`，新建O_EXCL regular文件、4GiB、root/0600 |
| 唯一loop | `losetup --find --show`返回且BACK-FILE精确等于该新文件；只能是loop类型，不接受任何磁盘/分区/by-id |
| QA mountpoint | `/srv/dell-nas-sys001/<nonce>/mount`；先证明其父目录在根文件系统，且不位于真实媒体盘 |
| 新UUID | 显式新生成、与根盘及真实媒体UUID不同的ext4 UUID |
| QA unit | `/run/systemd/system/dell-nas-sys001-<nonce>.service`，仅手动启动，不enable |
| QA compose project | `dell-nas-sys001-<nonce>`，与真实dell-nas严格不同 |
| HTTP | 只发布 `127.0.0.1:18097:8096`；先查端口空闲，不接管已有listener |
| 容器资源 | CPU0.25、memory512MiB、memory-swap512MiB、pids128，restart=no |
| 网络/权限 | 新QA-only internal bridge、非root2000:2000、cap-drop ALL、no-new-privileges，不加入真实NAS网络、不挂docker.sock/真实媒体/config |

使用当前已缓存 `jellyfin/jellyfin@sha256:fea863d0cd9ec445985d9c75fc6ed64e38a1d2766cf0c250a33d553f4fc1b771`，`--pull never --no-build`。全新空配置，不复制真实Jellyfin账号/数据库或任何SMB/OMV秘密，不下载媒体/插件。只用 `/health` 验证临时实例进程ready，不初始化用户，初始wizard仅在localhost临时端口可达。

QA env只包含新mount/UUID、127.0.0.1、固定镜像、现有UID/GID和localhost公开URL。复用真实compose时，override明确覆盖CPU/内存/PIDs，并用当前Compose支持的 `ports: !override` 替换端口列表，**不能普通append导致继承真实8096映射**；CLI `--project-name`强制QA project覆盖base name。合并配置必须私有读取并核对恰好一个QA服务、只有QA挂载和localhost临时端口，才允许启动。

QA unit从实际unit文本render，保持Type=simple、ExecStartPre在Docker启动前、Requires Docker/RequiresMountsFor及BindsTo对应QA mount。仅替换Description、WorkingDirectory、mount/UUID/minimum参数、独立compose/project/env路径；QA驱动期间Restart=no、不含Install/WantedBy，不污染开机。真实unit和旧生成器保持原字节。

ExecStartPre精确为：

```text
/usr/local/libexec/dell-nas-check-data --mountpoint /srv/dell-nas-sys001/<nonce>/mount --uuid <QA_UUID> --minimum-gib 1
```

Compose配置/cache都放loop文件系统内。Jellyfin12.4曾明确要求cache可用空间至少2GiB，因此loop用4GiB，不用过小tmpfs；1GiB是本轮容量门禁参数，不降低真实2TiB门槛。512MiB下能否启动尚未实测，若ready失败绝不加大资源或算通过，停止QA并报告，由主AI选专用QA VM。

## 执行前与连续性证据

每次再确认hostname nas-media、IP10.63.40.10、非PVE、本地Docker、实际守卫/unit/compose SHA；MemAvailable≥1.5GiB、根盘可用≥8GiB，主AI确认其底层datastore可容纳新4GiB。执行中MemAvailable低于1GiB、真实服务健康变化或真实PID变化即停止QA并报告，不重启真实服务。

记录真实OMV engined、smbd、NAS unit MainPID；真实Jellyfin容器完整ID、PID、StartedAt、image ID、Health；真实2TiB mount UUID/源保持。对三share既有专用样本记录SHA并逐阶段比对，不使用真实家庭文件：

```text
<REAL_MOUNT>/media/dell-permission-5193233d83fe453eb9aa1290e404b1bc.bin
<REAL_MOUNT>/games/dell-permission-5193233d83fe453eb9aa1290e404b1bc.bin
<REAL_MOUNT>/incoming/dell-permission-5193233d83fe453eb9aa1290e404b1bc.bin
```

这些是NAS002已保留的65597B合成样本，预期SHA `8f106c67b7b0f9ba8fc55ca569989fd955237e2c480ab3d36b63db7229dae35d`。缺失或不符就停，不重建/覆盖它们。真实guard/unit/compose/.env/OMV配置可仅取SHA比对，不输出秘密内容。

这里“根盘无写”精确指缺失挂载后暴露的同名appdata目录/根盘canary不产生应用回落写入；预先声明的4GiB backing file、QA控制元数据和正常systemd journal不属于该断言。loop文件物理位于根盘是一次性测试夹具，不能据此声称真实NAS已获得物理独立介质或实际2TiB离线验证。

## 正例、缺失、恢复三阶段

**A：真实独立scratch挂载与ready。** 在新根盘QA目录创建可丢弃文件，映射唯一loop前后核对BACK-FILE与loop类型；无signature/已挂载/其他用途，才允许 `mkfs.ext4 -U <QA_UUID> <QA_LOOP>`。不使用强制格式化、wipefs -a、真实scsi盘或分区。手动mount到唯一QA路径，不写fstab或持久.mount/automount。

mount之前在根盘同名目录放独立rootfs-canary，并记录完整目录树/文件SHA，随后被loop mount遮住。挂好后先调用**原安装守卫**，必须exit0并报告QA UUID；只有此时才在loop内创建config/cache/media目录和QA-volume-canary。启动QA unit，核对实际CPU≤0.25/内存≤512MiB/PIDs128/只有127 listener/只有QA绑定，`GET /health`真实200后才算正例。真实NAS连续性字段与三样本必须保持。

**B1：只卸载scratch的守卫负例。** 先仅停止QA unit，等QA容器PID消失，正常umount该唯一scratch；不force/lazy、不动真实mount。证明findmnt无该mount、路径st_dev回到根盘。直接调用同一个已安装守卫，要求exit1、明确“data filesystem is not mounted”；记录根盘canary/目录树完全不变，config/cache/media未出现在根盘。此阶段只有scratch被卸载，守卫原代码已实测，而不是mock。

**B2：QA启动链的缺失卷负例（推荐需主AI认可的明确附加动作）。** 不创建fstab或持久.mount定义，但systemd可能记住动态mount并尝试重挂；因此不能假定“umount后start”一定失败。先检查该QA mount unit的FragmentPath/SourcePath/LoadState及有无可重激活定义。若可自动重挂，推荐在已停止QA/正常umount后**只detach这个已核对BACK-FILE的QA loop**，保留原文件/UUID，制造明确不可用的QA卷，再对QA unit发一次有界start。

这个附加detach不是“只umount”的同义词，证据必须单列，不能掩盖自动重挂。要求systemctl start非零或明确job failure，unit非active、QA HTTP不可达、无新运行QA容器；同时保留B1守卫真实exit1。失败可能由挂载依赖先拦截，不能伪称ExecStartPre在本次unit start必然执行；守卫自身由B1独立证明。

若主AI只允许umount、不允许detach，则尝试一次原模板启动；若systemd真的重新挂载，记录为“自动修复，负例未成立”，不接受SYS001、不mask/改生产unit或伪造失败。交主AI决定改用detached QA loop或专用QA VM。

QA启动job必须有≤20秒的管理超时；超时先取消/停止**QA** job，确认无残留等待任务，才能进入恢复。不要让旧pending job在恢复后意外启动；不通过mask真实unit/mount隐藏结果。

**C：恢复同一UUID并重新ready。** 如已detach，仅把同一个仍存在的backing file重新losetup；loop编号可变化，但blkid必须仍是原QA UUID。正常mount，原守卫exit0、QA-volume-canary SHA保持；同QA unit再次ready200。根盘隐藏canary从未改变、真实NAS原PID/容器/3样本全程不变。

## 清理与验收边界

只清理manifest中的QA对象：停止QA unit、删除唯一QA容器/专用network（不prune、不动真实project）、正常umount QA scratch、detach核对后的QA loop，再删/run中的QA unit和新nonce目录/loopfile。确认无active mounts/loop引用后才删文件；任何busy/资源身份不一致保留现场报告，不force清理。daemon-reload只加载/移除QA定义，不restart Docker。

普通evidence只含时间、对象/UUID/SHA、资源、退出码/失败类别、before/during/after不变布尔和清理结果，不包含Jellyfin/SMB/OMV凭据或HTTP正文。当前所有执行项pending，不能把本计划保存当SYS001通过。

本试验可证明“同一已部署挂载守卫 + 专用NAS实例的启动链”在测试profile缺挂载/卷时不向根盘写；它不会证明真实2TiB被卸载时SMB/OMV的行为，因为真实媒体盘、服务和身份始终不动。若512MiB Jellyfin不能ready、namespace不一致、dynamic mount无法安全控制或资源余量不足，停止本路径；由主AI创建/分配专用QA VM再复用同一守卫/模板，子AI不执行PVE power或创建。
