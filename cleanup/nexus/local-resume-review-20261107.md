# 本轮本地恢复复核（无远程窗口）

2026-11-07：用户已表示22开机并要求重启合并；但root10:14:54实测PVE22/GW23管理仍不可达。硬件/DIMM_B1事件由root评估。停机合并授权有效，当前不能据“已开机”跳过可信管理/硬件稳定检查。本轮没有远程连接或写入，也未修改既有工具。

## 复核结论与guard注意

1. target.py/relocate.py/verify220.py AST通过，原6纯转换测试通过。target当前本地SHA09b87a31...36756，先前已上传220版本SHA c7839413...1cab；恢复后必须fresh读回并精确CAS同步本地新增的source30路由guard，不能假定远端已新。
2. stage只接受220物理MAC上的唯一30/24；final接受同MAC恰好30+31/24、6CPU/实际MemTotal>=7.5GiB、classic-overlay2、原2image IDs，并检查到19.45的prefsrc/src=30。**现有nonce已prepared，不应重跑stage；root加alias后stage guard正常拒绝不是故障。**
3. mount只在原UUID盘真正移到220之后执行。若写fstab成功但mount失败，再跑会因已存在条目拒绝；必须先只读检查UUID唯一设备、fstab与挂载事实，不能删guard/盲追加第二条。保留build盘UUID16dc…；无mkfs/chown数据树。
4. commit全量候选SHA预检后才写，但中途验证失败可能留下部分新安装且journal仍prepared；再次commit会拒已有路径。这是需要root按精确manifest评审恢复的边界，不能以rm整个目录或放宽存在检查绕过。此轮未改工具。
5. start600秒内等待完整2healthy/原image IDs；短暂缺名会返回空帧重试。若超时/断连但真实unit已active，先读实际阶段，不重新移盘或重新初始化。
6. verify220强制HTTP GET-only，含原身份/EULA/角色/group、匿名401/403及publisher不入docker组/socket拒绝。调用的现役m.verify预期49GAV/234主件；如果源新增合法数据，冻结新全量基线并评审预期，**不得删回49来凑通过**。
7. quiesce221.py当前不存在：此前含创建+执行的整条命令被自动审批在CreateProcess前拒绝，不能把历史计划当已部署工具。新维护窗应先准备/审核source基线停止驱动，或由root在冻结只读基线后显式执行原unit stop，不能调用不存在的文件。

## 窗口开放后的顺序（现在不执行）

- root硬件/存储/可信SSH/QGA恢复并明确新窗。只读fresh220/221 OS/MAC/IP/bootID/实际服务、原UUID/数据树、source两images/GET基线、targetDocker/standby13项及发布key**仅stat**。旧receipt不是断电后的新事实。
- 明确只读窗后可运行本地协调器 `python3 -B -I dell/cleanup/nexus/collect.py` 与 `python3 -B -I dell/cleanup/nexus/preparation-readback.py`；这些会远程读取，所以当前不可运行。source/standby私有hash仅同owner600记录/受控内存比对，不打印。
- 新维护窗内冻结source全量repo/identity基线，然后原221正常 `sudo systemctl stop dell-nexus.service`，确认2容器停止后交root冷备/关机。不能以此文档本身扩大当前执行权限。
- root完成221受保护冷备+vma/源off、220正常停机6CPU8G、唯一盘221scsi1→220scsi2、MAC/IP31所有权转移与多IPstrict管理支持，再通知应用窗。

应用窗内root220命令，原nonce不变：

```sh
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py mount --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py commit --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
sudo /usr/bin/python3 -I -B /opt/dell/cleanup/nexus/target.py start --nonce cb01b8582f544381b0461001dfa3ccb4 --root-source221-off-and-disk-handover-complete
```

新应用实际healthy后才运行本地协调器 `python3 -B -I dell/cleanup/nexus/verify220.py`（同样会远程连接，当前不可运行）。hostkeys不复制、管理用220/30、服务URI31保持；publisher私钥仅220，不wholebackup220。

## 监控配套

以最新ten-role/future-merge-contract fresh重核：当前10 exporter /12物理角色/15targets仍含221；合并验证并root确认退役后，才转9 exporter+5Ops=14targets、11物理角色。220保留primary30 role/三基础unit并增加Nexusunit+本机alias31健康URL，不整份覆盖成artifact-service/31角色；collector已按所有local_addresses允许本机alias，无需扩大远端URL。9份runtime与source catalog/installer/ROLES成对更新，不能沿旧12→9 SHA。当前没有执行该配套或删221target。
