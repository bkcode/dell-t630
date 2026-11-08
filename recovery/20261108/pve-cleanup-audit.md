# 2026-11-08 PVE多余资源只读审计

分类时间：2026-11-08T20:27:09.403016+08:00。只写本报告/JSON；**未删除、停启、备份、迁盘、改网络或执行guest命令。** 用户当前明确暂不迁移，因此源221与发布机220边界保持。

## 结论

- Fresh全量仅12保留guest+3模板，最新状态12运行、3模板停止；无额外对象。初次20:15有恢复中尚停止来宾，后续root启动已刷新，不因停止态判多余。
- 37个image/rootdir卷均有配置引用；无unused槽、无真实PVE/qcow内部快照、无pending磁盘、无目录孤儿镜像/requiredbacking/LVMorigin边。
- 仅两份旧安装ISO在运行依赖层面可安全清理，合计3876812800bytes（3.611GiB）。没有按mtime作多余判断。
- Debian12 LXCcache虽无引用，但member元数据包含host-private-key/machine-id条目，**降为无法判定，暂保留**；未读任何成员正文，不能宣称不存在唯一身份。
- 共享artifactsISO仍10VM配置引用且10个kvm FD实际打开，必须保留。21protected档均存在且root0600，目录root0700，全部保留。

## 旧介质逐项（只由root在重核后处置）

| 分类 | volid / 绝对路径 | bytes / inode / mtime UTC | 格式与依据 |
| --- | --- | --- | --- |
| 可安全清理 | `store:iso/debian-12.10.0-amd64-netinst.iso`<br>`/mnt/pve/store/template/iso/debian-12.10.0-amd64-netinst.iso` | 663748608 / inode234094596<br>2025-05-10T07:35:03.987818+00:00 | ISO 9660 CD-ROM filesystem data (DOS/MBR boot sector) 'Debian 12.10.0 amd64 n' (bootable)；配置/快照/backing/FD均无引用 |
| 可安全清理 | `store:iso/ubuntu-24.04.2-live-server-amd64.iso`<br>`/mnt/pve/store/template/iso/ubuntu-24.04.2-live-server-amd64.iso` | 3213064192 / inode234094597<br>2025-05-12T10:50:32.445465+00:00 | ISO 9660 CD-ROM filesystem data (DOS/MBR boot sector) 'Ubuntu-Server 24.04.2 LTS amd64' (bootable)；配置/快照/backing/FD均无引用 |
| 无法判定 | `store:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst`<br>`/mnt/pve/store/template/cache/debian-12-standard_12.12-1_amd64.tar.zst` | 123731847 / inode234094598<br>2025-09-07T15:49:43+00:00 | Zstandard compressed data (v0.8+), Dictionary ID: None；配置/快照/backing/FD均无引用 |

两ISO卷标/根目录符合Debian12.10 netinst、UbuntuServer24.04.2原版布局，未见可见定制seed。随后主AI已分别计算整文件SHA256，并与Debian/Ubuntu发行商HTTPS官方清单一致，见[摘要收据](unused-ISO-digests.json)；本audit独立核其路径/size/脚本固定SHA吻合，因此这两份是发行商原样字节，不是自定义seed镜像。本audit不读取casper/squashfs/credential正文。root删除前仍须重查准确volid/path、size/inode/引用/FD，脚本只允许native pvesm free这两个精确volid。LXCcache没有此官方digest证明，仍保留。

LXCcache目录列表共22156项，存在标准Linux顶层及敏感身份文件名；它们可能是官方build占位或通用键，也可能定制，单靠文件名不能定性。没有提取、打开、输出credential；当前不建议清。

## 需保留

| 对象/路径 | size与用途 | 引用/保护理由 |
| --- | --- | --- |
| `/mnt/pve/store/template/iso/dell-artifacts-20261106.iso` | 13499936768bytes | VM200/201/210/220/221/230/240/250/260/270 scsi2引用；10kvm FD打开，不得删 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/` | 21archives / 32096582489bytes | root0700/archives0600；已删旧VM/原模板等恢复证据，用户明确保留 |
| `/root/dell-bootstrap/protected-cf-backups/` | 含244256662bytes旧CF归档与日志 | 只stat，CFtoken/backup不读不导出 |
| `/root/dell-bootstrap/pve-push-metrics.py` | 3558bytes | systemd metrics单位仍指向它；oneshot瞬间inactive不等于废弃 |
| `/root/dell-bootstrap/perccli-extracted/opt/MegaRAID/perccli/perccli64` | 7791416bytes | RAID查询及PVE metrics依赖，不清工具链 |
| `/mnt/pve/store/dell-artifacts/amd64/*.tar` | 5个离线镜像归档 | 恢复输入；未做内容去重，不因ISO中可能同份就删 |
| `/mnt/pve/store/dell-artifacts/java/*.jar` | 5个历史Java制品 | 业务停用不等于授权删回退制品，当前不部署它们 |
| `/mnt/pve/store/dell-artifacts/baseline-backup/` | 旧9002基线archive380475872bytes | 独立版本/恢复证据，不凭相同VMID视重复 |
| `/root/dell-bootstrap/network*`、`cleanup/`等历史小文件 | 逐路径/size见JSON | 回退/审计/规划材料；不能当活动加载器重跑，不作mtime清理 |

## 无法判定项

- `/mnt/pve/store/template/cache/debian-12-standard_12.12-1_amd64.tar.zst`：123731847bytes；Unreferenced Debian12 LXC template cache, but tar directory contains namedhost-private-key andmachine-id entries. They may be standardbuild placeholders/generickeys; sizes/content/sourceauthenticity not adjudicated. Do not assert uniqueidentityabsence fromfilename.
- `/root/dell-bootstrap/images/debian-13-genericcloud-amd64.qcow2`：117543992bytes；Possibly an oldpartialdownload (different size fromverifiedimage), but filename/mtime/size alone do not establish integrity or redundancy. No currentFD observed; no contents/digestverified.

本次匹配到的/tmp或/var/tmp临时文件为0；目录深度与文件名过滤有限，不是全盘垃圾清理证明。

## Protected21归档逐路径（全部保留）

| path | bytes | mode / uid |
| --- | ---: | --- |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-101-2026_11_07-01_25_47.vma.zst` | 2302789451 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-102-2026_11_07-01_27_14.vma.zst` | 2323625523 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-103-2026_11_07-01_24_14.vma.zst` | 2504249493 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-104-2026_11_07-01_21_27.vma.zst` | 2828948528 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-105-2026_11_07-01_28_38.vma.zst` | 2362340981 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-106-2026_11_07-01_30_14.vma.zst` | 9184521882 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-231-2026_11_07-01_41_08.vma.zst` | 622178785 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-232-2026_11_07-01_41_59.vma.zst` | 621356531 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9000-2026_11_07-01_33_47.vma.zst` | 4163041051 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9001-2026_11_07-01_53_49.vma.zst` | 462487736 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9002-2026_11_07-01_35_32.vma.zst` | 381624387 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9003-2026_11_07-01_36_30.vma.zst` | 506106351 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9004-2026_11_07-01_37_32.vma.zst` | 452492967 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9005-2026_11_07-01_38_28.vma.zst` | 338404440 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9006-2026_11_07-01_39_22.vma.zst` | 463773304 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9010-2026_11_07-01_54_33.vma.zst` | 336420275 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9011-2026_11_07-01_55_08.vma.zst` | 491156544 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9020-2026_11_07-01_40_21.vma.zst` | 372568134 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9040-2026_11_07-02_04_28.vma.zst` | 372585360 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9041-2026_11_07-02_05_06.vma.zst` | 506724842 | 0o600 / 0 |
| `/mnt/pve/store/dell-artifacts/cleanup-backups-20261107/vzdump-qemu-9042-2026_11_07-02_05_52.vma.zst` | 499185924 | 0o600 / 0 |

## 当前保留对象（刷新时点）

原始配置采集：2026-11-08T12:15:23.762910+00:00；状态刷新：2026-11-08T12:25:59.744211+00:00。

| VMID | 名称 | 状态 | 身份 |
| --- | --- | --- | --- |
| 100 | cf-tunnel | running | retainedguest |
| 190 | network-gateway | running | retainedguest |
| 200 | data-prod-db | running | retainedguest |
| 201 | data-prod-infra | running | retainedguest |
| 210 | data-test | running | retainedguest |
| 220 | publish-service | running | retainedguest |
| 221 | artifact-service | running | retainedguest |
| 230 | java-prod-01 | running | retainedguest |
| 240 | java-test-01 | running | retainedguest |
| 250 | penpot-service | running | retainedguest |
| 260 | nas-media | running | retainedguest |
| 270 | ops-service | running | retainedguest |
| 9001 | tpl-docker-base | stopped | template |
| 9010 | tpl-linux-base | stopped | template |
| 9011 | tpl-java-acceptance | stopped | template |

## 证据与范围

- JSON保留官方有效配置白名单、卷路径/size、snapshot/pending、26镜像头、LVM原点、hostFSUUID、209已知artifact文件stat、FD/单位路径与3介质inode/格式元数据。没有env/CI密码/args/token值或盘内用户文件。
- Protected归档只元数据，没有重做SHA/解压/恢复；cache只列member-name元数据，未extract成员。
- 本次可达不证明内存已确诊修复；硬件维修方式/新错误仍由root另行核实。本报告不重做RAID操作或新增压力。
- 本轮只输出清理依赖判断，不备份220、不动CF/源221，不迁Nexus，不生成删除命令。root实际清理后应另记准确删除回执与复验。

## root精确两ISO清理脚本只读review

`clean-unused-install-ISOs.py`已只读/AST复核，当前无P1：硬编码2volid/path/size/官方SHA；全cfg所有节freshref检查覆盖snapshot/pending，原生pvesmpath/regularroot/noSymlink、inode/mtime_ns/device/sizeCAS、FD否定后准确pvesmfree，前后资源状态/共享ISO及21档名字核对。未执行脚本或删除。3模板ID未单独assert为非阻断建议（本次fresh盘点已确认9001/9010/9011）；21档保护不是payload再次校验。LXCcache不在删除列表，源221/220/100和全部guest磁盘不动。
