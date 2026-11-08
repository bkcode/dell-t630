> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 多余实例/旧模板清理：只读磁盘依赖审计

审计生成：2026-11-07T01:17:44.585912+08:00。状态：**仅完成只读审计，没有删除、停机或备份。** 当前Java各保留1的范围仍由主AI确认；本文件不授权立即删除。

## 结论

- 全量30对象、68个PVE image、69卷引用，34个目录镜像头已核；官方current config/snapshot/pendingdisk、qemu backing、LVMorigin均读取成功，未见隐藏args/透传/hook字段。
- 没有保留的核心9001/9010/9011或业务盘依赖候选base；没有真实PVE快照或qcow内部快照。`current`只是当前态，不是备份。
- **103→104为真实依赖，必须先处理104。** 103scsi1的100Gqcowbase被104scsi1overlay必需引用；104root32G另是103root32G的LVMthin origin谱系。两种关系不能混同。
- 231/232目前running、各32G独立根盘；仅挂载元数据不证明绝对空盘。等待范围确认、正常停机和备份后才可由主AI退役。
- 100/220不在清理对象；220含仅限本机的publisher私钥，**不得wholebackup/整机快照220**。221仍保留，只有合并220的数据/权限/消费者验证通过后才另开清理。

## 每个候选

| VMID | 名称 | 状态/模板 | 磁盘依赖结论 | 次序/备份前置 |
| --- | --- | --- | --- | --- |
| 101 | data-docker-base-tpl | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 104 | publish | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 102 | data-docker-tpl2 | stopped / 模板 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 103 | publish-base-tpl | stopped / 模板 | 104依赖本base | 先104删除/保留替代再103；当前不可直接删 |
| 105 | java-running-base-tpl | stopped / 模板 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 106 | windoge-template | stopped / 模板 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9000 | dell-template-inspect | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9002 | dell-linux-clone-test | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9003 | dell-docker-clone-test | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9004 | dell-docker-clone-a | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9005 | dell-linux-clone-b | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9006 | dell-docker-clone-b | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 9020 | dell-restore-baseline | stopped / 实例 | 无保留实例依赖 | 依赖检查清；先PVE-only备份验证，再主AI准确VMID操作 |
| 231 | java-prod-02 | running / 实例 | 无保留实例依赖 | 仍running；先确认各1范围、停机、PVE-only备份 |
| 232 | java-prod-03 | running / 实例 | 无保留实例依赖 | 仍running；先确认各1范围、停机、PVE-only备份 |

所有候选`can_delete_now=false`，因为本agent不执行写操作、本轮未创建或核验候选完整备份且231/232还待确认。不是发现其它保留盘依赖。

## 103/104两条关系

| 组件 | 证据 | 对删除的含义 |
| --- | --- | --- |
| 104100Gqcow2overlay →103100Gqcow2base | 有效配置特殊volid、pvesm parent、qemu实际backing header三者一致 | 硬依赖；删103base会破坏104，必须先备份并处理104 |
| vm-104-disk-0 →base-103-disk-0，均pve/data thin | lvs origin=base-103-disk-0，同thinpool、segtype thin | 普通thin snapshot谱系，不等同外部qcow文件硬依赖；本组仍保守子先父 |

104特殊PVE volid为`store:103/base-103-disk-0.qcow2/104/vm-104-disk-0.qcow2`，但实际child文件在`/mnt/pve/store/images/104/`、owner VMID104；不能按volid103前缀批删。普通thin snapshot与origin可独立存在，外部origin是另一种结构，不能一概而论。[LVM上游thin手册](https://raw.githubusercontent.com/lvmteam/lvm2/main/man/lvmthin.7_main)；qemu只读info与-U的用途见[QEMU官方工具文档](https://www.qemu.org/docs/master/tools/qemu-img.html)。

## 保护对象与共享介质

保护VMID：100, 190, 200, 201, 210, 220, 221, 230, 240, 250, 260, 270, 9001, 9010, 9011。当前所有保留卷到候选base的required路径为0，核心模板及实际数据盘无需靠这些旧base存活。LVMthinpool pve/data、root/swap/PV、store宿主文件系统是基础设施，不是清理对象。

- 共享介质`store:iso/dell-artifacts-20261106.iso`仍被200,201,210,220,221,230,231,232,240,250,260,270引用，不随231/232或其它候选删除；不手工删除ISO。

## 当前容量与回收口径

| 存储 | total GiB | used GiB | avail GiB |
| --- | ---: | ---: | ---: |
| local (dir) | 93.935 | 10.199 | 78.92 |
| local-lvm (lvmthin) | 319.109 | 62.322 | 256.787 |
| store (dir) | 7391.162 | 91.22 | 6927.376 |

候选逻辑已分配容量合计约 **672.055GiB**（包括模板+子盘各自逻辑容量）；可见目录文件物理allocated合计约 **5.905GiB**。不能把逻辑容量当成实际可回收量；thin的共享块/未激活LV data_percent空值使本轮无法精确计算SSD回收。未做thin_dump、trim或激活LV。

备份压缩后实际大小没有测量；保守以全部候选逻辑容量作非压缩上界预留，store当前余量足以容纳该上界，但真正备份时仍需复核可用量并验证archive，而不是仅凭命令exit0认为可恢复。

## 备份与操作顺序（主AI执行，本轮不执行）

1. 冻结/确认候选VMID与用户prod/test各1范围，按最新元数据重核DAG和lock。停止的对象不启动检查内容；231/232由主AI正常停止，避免强制power-off。
2. 建议受控PVE-only目录`/mnt/pve/store/dell-cleanup-backups/YYYYMMDDTHHMMSS`，root:root0700；每个候选的nativePVE备份、配置/依赖manifest和日志均root0600。对候选做PVE-native完整备份并核archive可读/完成，必要restore验收另用root批准QA；不将100/220加入任何批量backup，不导出CF材料到Mac。
3. 先叶实例：9000、9002–9006、9020、101、104；尤其先确保104的含backing数据在native备份中可恢复，再处理103。
4. 再旧模板：102、103、105、106。保留9001/9010/9011，禁止`rm -rf`、`lvremove base-*`、按目录/volid前缀通配清理；只让主AI用准确VMID的PVE对象生命周期处理其拥有卷。
5. 231/232属于独立确认门：当前running不删除。确认保留230/240并备份、正常停机后再退役；随后清理其监控/ACL/IP注册与计划预算，不把旧告警当新的故障。
6. 221当前不删。Nexus合并220须先做数据/SHA/身份权限/新入口与消费者验证，再另开221清理；220本身不做含publisher私钥的wholeVM备份，备份Nexus时只能限定应用数据/导出范围。
7. 每批后核保留卷仍在、核心模板可克隆、保留业务dataUUID/服务保持，记录存储实际变化和新DAG。PVE-only备份与生产同主机，不当独立灾备。

## FSUUID与限制

运行13个QEMU的findmnt元数据已采成功，未执行CF100 guest命令、未启动停止实例，详见running-filesystems.json。多个克隆根盘UUID同为2d5cddec…，它不是VM唯一身份；数据盘UUID单独记录，不能用这个重复rootUUID匹配删除对象。停止候选/模板内部FSUUID未读取，不因此推断数据为空。

所有disk/header/FSUUID数据仅说明本时点引用和身份，未读任何盘内用户文件。备份不在本轮授权动作中，任何删除前均须主AI再核刚产生的新快照、挂盘或迁移引用。

证据：pve-storage-inventory.json、qemu-image-headers.json、running-filesystems.json、opaque-config-flags.json、disk-dependency-dag.json。
