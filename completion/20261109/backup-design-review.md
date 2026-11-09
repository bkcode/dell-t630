# PVE本机自动备份最小设计只读复核

复核时间：2026-11-09T14:52:31.158500+08:00。本机实际PVE `8.4.0/ec58e45e1bcdf2ac`、kernel6.8.12-9。只读取已安装源码/CLI schema、参数帮助及默认配置中键是否存在；没有新增storage/job/hook、没有执行备份/prune、没有通知或服务动作。用户明确先用PVE本机自动备份，独立目的地后续，不再把独立设备选择作为当前阻塞。

## 结论与必要修正

方案可落地，但必须把以下语义写入实现后再运行：

1. **挂载保护在job-init就执行**，不能只job-start。设置dir storage `is_mountpoint=/mnt/pve/store`，不是`yes`（计划path只是子目录、不是独立挂载点）；再核实际mountpoint/source/UUID `75e5b438-5ff3-4139-83d6-b6a6847aedac`、路径无symlink/越界、可用容量与root0700。storage激活可能早于job-start，job-init位于构造器激活storage前。job-start/每backup-start再次检查空间与固定目标。
2. **不能把job-end当11个全部成功**。本机按taskforeach顺序运行，单VM错误累计errcount仍可能走job-end；只有外层异常走job-abort。hook需记录backup-end/backup-abort、log-end，job-end统计预期11个终态；失败保留JSON/log并非虚报success。
3. **关闭通知用`notification-mode=legacy-sendmail`且effective mailto为空**。`auto`在无mailto时会改走PVE notification-system。`notification-policy=never`虽schema还接受，但标Deprecated且当前send_notification并不读取它，不能靠它保证静默。空mailto用本机实际PVE::JSONSchema::validate(instance,schema)已确认接受；创建后仍要读回effectivejob/default，确认没有继承非空收件人。当前/etc/vzdump.conf无mailto/mailnotification/notification-mode等显式键；不要修改全局PVE通知或Lark来实现静默。
4. **free>=100GiB是地板，不是NAS备份空间充足证明**。首轮前按includedvolumes与实际已用/首备大小估算，加新归档/校验scratch保底；每个guest再次检查。2TiB逻辑NAS即使稀疏也不能承诺小归档/短时间；同HDD阵列源盘读+归档写+验证会叠加IO。后续保留策略不限制总bytes，需观察增长/低空间失败状态。

## 建议固定合同（未创建）

- storage ID `dell-local-backup`，type dir，node pve，content仅backup，path `/mnt/pve/store/dell-artifacts/scheduled-backups`。默认实际归档落子目录`dump/`，它与旧`cleanup-backups-20261107`、CFprotected目录不得重叠/alias。PVE同filesystem容量会与store重复展示，不能把两个storage的avail相加当双倍容量。
- 禁止store未挂时自动在根盘创建备份。已确认API支持`is_mountpoint`指定其它真实挂载路径，以及`create-base-path`/`create-subdirs`；子目录root0700，归档/日志root0600。根私有metadatajournal不要进Git或外发，GUI保留PVE原生tasklog。
- 单job每天本机时区03:30，`node=pve`、固定ID **100,190,200,201,210,221,230,240,250,260,270**，all=0、不使用pool动态选择。**220明确排除**（publisher私钥仅本机，禁止整机备份/快照导出），9001/9010/9011模板排除，21protected旧档保持。CF100备份只在此PVE本机，不导出Mac。
- `mode=snapshot`、compress=zstd、`zstd=2`（**两线程，非压缩level2**）、`bwlimit=51200`（KiB/s=50MiB/s）、`performance=max-workers=1`。本机schema不接受bwlimit带K后缀。max-workers是单VM QEMU备份IO worker上限，不是job并发VM数；11任务源码foreach本来顺序执行，插件在QEMU不支持时会警告忽略。
- 显式jobretention `keep-last=3,keep-daily=7,keep-weekly=4`、remove=1；仅新storage backupgroup。各周期按规则选择可能重叠，不应简单宣称严格14份/VM，更不是容量上限。原21protected档与新目录隔离，绝不对store全部backup做globalprune。
- 不给所有新备份设置protected，否则nativeprune无法正常回收。本机protected/notes-template都requiresstorage；使用registeredstorage满足语义，dumpdir-only不能带protected并假装生效。现有21旧档仍按目录保护保留，不在新prune集合。
- 通知按上节legacy+empty，不测试Lark/发送邮件；GUI日志和rootJSON为当前观察面。

## 本机hook参数与环境

已安装`PVE/VZDump.pm:826–853`：globalphase只有argv `$1=phase`；taskphase追加`$2=mode,$3=VMID`。它先`local %ENV`，只显式提供STOREID、DUMPDIR（若已确定），task时VMTYPE/HOSTNAME/TARGET/LOGFILE。**没有VMIDS/JOBID/原始joboptions自动传入**，不要dump整个env或猜测读到列表；不读CF/220单位或env。

- job-init：尽早mount/UUID/namespaceguard，可依赖固定rootownedcontract，不假定此时DUMPDIR已解析。路径检查失败非零退出，阻止创建root盘替代目录。
- job-start：核storeid/path与fresh指定nativejob配置固定11且不含220/template；若手动首run与job同hook，不能只凭ENV声称验证了CLI全列表，需明确首run参数/契约签收，并在每task继续拒绝未知ID。
- backup-start MODE VMID：要求snapshot、固定白名单、精确挂载UUID/free，记录taskstarted；不能根据phase名字去停应用或改modefallback。
- **pre-stop/pre-restart/post-restart同样会在snapshot分支调用**，并不代表用户授权停服。hook这些阶段只记录安全元数据，绝不systemctlstop/QMpower操作。LXC多卷snapshot可能短暂freeze，不能保证绝对零IO暂停。
- backup-end：新TARGET归档已完成且nativeprune已执行；校验路径为新dump下安全regularfile、无symlink，再chmod0600/记录size，目标/日志只允许固定模式；不要扫描并chmod旧21档/CF目录/其它owner。TARGET未设置的globalphase不要误取空路径。
- backup-abort/log-end：失败也记录，不输出可能含秘密的guestcfg正文。log-end在原log关闭后，适合确保LOGFILE0600；hook本身异常要标hookfailure，不能抹掉原taskfailure。可以job-end合并固定11条安全metadata，正常与错误状态分开。

未知phase应failclosed或显式安全no-op白名单，不能把不认识的argv当shell命令。使用绝对可执行路径；由于ENV被清，不依赖自定义shell变量/PATH或交互用户shell。JSON使用临时inode/fsync/replace与root0600；坏的symlink/hardlink/外部路径拒绝，成功失败都留独立runID，防并发/重放覆盖。

## 一致性与不迁移边界

QEMU快照备份插件会在agent开启/运行且freeze-fs-on-backup未禁用时发QGA fs-freeze并thaw；agent不运行会跳过而非自动变成DB逻辑一致。它备份运行态磁盘，不是全机内存checkpoint；跨11guest不是共同时间点。MySQL/Redis/Rabbit/Nacos/Nexus/PG等要按crash-consistent可恢复语义说明，不能宣称应用logicaldump/交易一致性或已恢复演练。

snapshot不等于先创建用户长期snapshot；QEMU块备份与LXC存储snapshot分别走原生插件。LXC本机源码在卷不支持snapshot时明确报modefailure，不应自动改stop/suspend去凑成功。首轮要核每个data/root盘 included状态（backup=0/bindmount排除也要列清），不可只看VMID进job就声称数据盘已保全。

**不执行Nexus合并/退221，不移动源盘，不启Java业务，不整备220或导出CF。** 不复制私钥、hook、凭据到普通仓库；本地rootJSON/metadata归档可能含敏感配置，应受控，Git只放脱敏收据。

## 首轮完整性验收建议

1. 先配置disabledjob并readback schema/固定11/notification/retention/includedvolumes，再由root显式首run开启同样选项。首次与03:30定时不要重叠；仍运行的首轮不另外触发第二次。GUI task UPID/日志应可查。
2. 每个taskbackup成功后zstd --test，再做VMA或CTtar全遍历验证和归档SHA256。首次要求all11完成，不以单个VM样本替代；backupjob成功与完整性success分两层记录。
3. VMA本机help显示`vma verify <filename>`，本audit未证明`-`stdin支持；若选stream核验必须先用已核安全sample验证原生支持，否则用root0600稀疏临时VMA并确认空间，验证完只删自有scratch。**不能把NAS2TiB raw解压到普通临时文件而只留100GiB空间**；也不能因为zstd测试过就冒充VMA全verify。
4. Tar只做完整列举/readthrough且弃输出，不能extract到hostroot或恢复覆盖原CT；可能包含token的payload只在PVE受控盘上，临时tar目录和文件同样700/600且清理自有文件。
5. 持续监控backup进度、CPU/IO/memory、可用量、最近成功/失败状态和日志；bwlimit不是归档压缩后写入严格50MiB/s承诺，NAS可能数小时。预计2TiB非稀疏50MiB/s单遍约11.7小时只是上界场景估算，不是完成SLO；QEMU零块/压缩/验证行为按实际。
6. 全11归档完整性+SHA齐、mode真snapshot、所有原业务服务/VM仍健康、220未纳入、旧21档未变后，才签首轮成功并enable03:30任务。未实际restore，RPO/RTO/数据库逻辑恢复仍pending；同一T630/RAID故障域无法替代独立备份。

## 本机语义来源（只读安装源码）

- `/usr/share/perl5/PVE/VZDump.pm`，SHA256 `267e96f4d7189b550bd3c2f68f737b88e8ff74e514c793371736dd6e8b76d413`。
- `/usr/share/perl5/PVE/API2/Backup.pm`，SHA256 `071cf89ea79a2068aa4e939bd8fb901aaac94f648dee57945b41af4eb51757b8`。
- `/usr/share/perl5/PVE/API2/VZDump.pm`，SHA256 `2f93e0ed2a79966301dfade44801c9d508af85e4f60ae20780ea3139d8b3b03f`。
- `/usr/share/perl5/PVE/VZDump/QemuServer.pm`，SHA256 `0d105d9f8270dbea5d5fd9d967fd0fe826adf491f66a74db84707452abf30f53`。
- `/usr/share/perl5/PVE/VZDump/LXC.pm`，SHA256 `808227f815a02917cbc1e7c831ead9532b95b5cecb094d5a6b304faf443d2782`。
- `/usr/share/perl5/PVE/Storage.pm`，SHA256 `11de8e4f0b8c95efa1dd17a230592ec73a7036259e07db68c59c7b96449f47e1`。
- `/usr/share/perl5/PVE/VZDump/Common.pm`，SHA256 `f3b542bc64c7f07d4f9e51e15ce4da1d2e40ed110f00c9649d16fe58765f73b5`。
- `/usr/share/perl5/PVE/Storage/DirPlugin.pm`，SHA256 `f23d7b54894476cb075153edb29bda5cf52573710bcd1872c4beb09432cf39df`。

CLI schema读取方式实际为`pvesh usage /cluster/backup --command create --verbose`与`pvesh usage /storage --command create --verbose`；只读usage没有创建API对象。Common schema明确zstdthreads/bwlimitKiB/maxworkers/notification枚举、protectedrequiresstorage；VZDump源码明确hookenv/prune在backupend之前与joberrcount语义。源码是本机8.4精确依据，不依赖更新版网上文档推断。

空mailto最终验证使用正确`PVE::JSONSchema::validate({mailto=>''}, {type=>'object',properties=>{mailto=>schema},additionalProperties=>0})`，实际输出accepted；早期参数顺序尝试不作结论。job序列化是否省略空字符串须创建后readback并确保effective参数不继承mailto，不能只看到命令行显示无收件人就认为永远静默。

## policy/hook/install候选代码复核补充

复核本地`infra/backup/pve-local/{policy.json,hook.py,install.py}`，没有执行安装/备份。当前实现的固定11排220、snapshot、root私有目录、job-init mountguard、pseudo-prestop安全no-op、全11ledger、disabledjob直到首轮成功的方向正确；安装API参数与本机8.4usage一致，protected没有误用dumpdir-only。

### vma stdin已实际证明

按主AI明确许可，在PVE `/tmp`随机root0700目录仅创建4MiB全零合成raw，nativevma create输出13824bytes；`vma verify -`从seekablestdin与**真实catpipe**分别exit0，pipeproducerexit0，临时fixture自动删除。未备份现役、未读任何真实归档/秘密、未改系统配置。因此hook的`zstd -dc | vma verify -`在本机有原生流式兼容依据，不需要先解出2TiB临时VMA。

### 可安装性与剩余建议

未发现当前policy/install必然失败的原生参数P1。mailto空字符串已用本机正确schema验证accepted；legacy模式源码不会在effective收件人为空时调用通知。install读回job无mailto并断言/etc/vzdump.conf无收件人是合适的本机保护。未来有人加全局收件人时可能被继承，所以应在每次job-init重新断言静默条件，不能仅安装时核一次。

剩余实现注意：

- hook.py:47/51固定每段1800秒可能让未来正常大NAS归档验证超时。建议policy显式设置大档有界窗口（例如首轮按24h级监控，而不是无限等待）或按实测大小/速率取上限；不能因超过30分钟就改称数据损坏。首轮若smallNAS确实小可记录实际耗时，但不要把30分钟当所有历史/未来容量保证。
- hook.py:58在load/preflight之后才进ledger，job-init挂载/权限失败仅stderr，无法保证rootJSONfailure已写。增加严格安全的rootstate-only失败记录路径，不向失挂store/rootfallback写备份；日志不得包含秘密/env。
- job-start只以policy固定11、逐task白名单与jobend全11保护，当前没有fresh读取nativejob确定全列表，若CLI误选子集会先做部分备份后jobend失败。主编排需先exactjobreadback/首run固定CLI；若要求第一task前拒绝错误集合，加明确原生job配置只读检查，不从不存在ENV VMIDS推断。
- 本机VZDump.pm1248–1284先nativeprune后backup-end hook。若zstd/VMA校验失败，新档已触发prune，不能宣称“仅verified归档才影响retention”。keep-last3至少保留多代仍是基础保护；如果未来要严格lastgood语义需另设计，不能默改native流程或把所有档protected。
- log-end在原tmplog拷贝到archiveLOGFILE后执行，hook当前dumpdir路径校验与时点适配本机；该阶段异常在PVE仅warning，宜把chmod/logfailure写ledger并让job-end据此失败，避免归档verified却日志权限检查失败仍被统计全成功。
- 安装新目录/O_EXCL与回退只新metadata合理，partialAPI成功而调用超时仍需root核实际job/storage是否创建，勿盲重跑或删非空目录。

这些建议不要求DB停写/迁移/停服、替换业务密码或导出CF。本轮只可静态签设计兼容与合成stdin兼容，首轮11VM备份完整性/调度/prune保留/恢复能力仍必须用实际新receipt签收。
