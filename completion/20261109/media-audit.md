# 2026-11-09 媒体/工具基础服务 fresh 只读检查

采集时间：2026-11-09T06:43:07.842606+00:00。范围220/221/250/260；本轮用户不迁移、不合并Nexus、不退役221，Java业务不启、Mac外部探针不需要。所有远程命令只读，已核control.guest(info=...)严格SSH，不修改known_hosts，不读密钥或秘密。

| VM | 实测 | 本轮需要修复 |
| --- | --- | --- |
| 220 | 原构建盘UUID/ext4正确；4CPU/约4GiB、仅19.30；Docker29.9.3 overlay2、0容器；无activeNexus路径；exporter/health timer运行 | 无观察到的运行缺项；旧Nexusstandby仅惰性保留 |
| 221 | 原/srv/nexus UUID239dc…/ext4；dell-nexus.service正常，2healthy/原镜像ID，statusGET200 | 无运行缺项；仍独立19.31 |
| 250 | 原/srv/penpot UUIDcccc…/ext4，DockerRootDir正确；notify正常、11healthy，首页GET200；实际Gitff1783e clean | 无运行缺项；不fetch/build/checkout或升级main应用 |
| 260 | 原2TiB UUID5b198…/ext4；原OMV/nginx/SMB/JF单元running，JFhealthy；OMV200/JFhealth200 | 无运行缺项；driver仍原overlayfs，不转存储后端 |

四台failed units均空、被检查单元NRestarts0；14应用容器全healthy/原镜像ID、restartcount0，container IDs与11月8日记录相同。资源/卷/health读回不是完整业务、身份重认证或灾备验收。publisher不在docker组，私钥仅stat为UID999/600，无内容读取/复制或wholebackup220。

## 部署来源与依赖

JSON逐项记录现役公开manage/guard/compose/health helper路径、root归属/权限及SHA；没有读取.env/Config.Env/Config.Cmd/healthlog或凭据。221/250原mount/Docker BindsTo与RequiresMountsFor保持；NAS原专盘guard/Compose/官方OMV helper存在。Penpot来自既有Gitff1783e（clean），而不是把主仓main文档合同当升级指令；其11栈/数据不变。没有对任何source做fetch/build/checkout。

## 可补齐候选，尚未实施

1. **应用备份调度与覆盖**：匹配backup/snapshot/nexus/penpot/nas名称的systemd timer只有Debian `dpkg-db-backup.timer`，它备份的是包数据库，不是Nexus/Penpot/NAS应用数据。在明确已核路径未发现dell-nexus-backup.timer、dell-penpot-backup.timer、dell-nas-backup.timer及对应命名工具；已有application-import/acceptance目录不是持续备份。建议主AI先确定每role数据范围、目标、保留、权限和一致性/隔离恢复，再批准最小工具与窗口。Nexus不能在线拷H2称冷备，Penpot需PG/assets一致性，NAS家庭媒体按实际容量安排；不备份220/不夹带发布key、不接触CF归档。**本检查只覆盖已知路径与systemd命名，不排除外部编排或未知cron，不能宣称全系统绝无备份。**
2. **220惰性standby清理候选**：/root/dell-nexus-merge、Docker准备记录及公开合并executor仍存在，当前不迁移，不能执行它们。仅建议以后按精确manifest核是否可确认重复、是否唯一恢复证据，再由root批准定点清理；本轮未删、未读其私有内容，不能因“看似多余”删除。

本次未发现需要立即启停/安装的基础服务故障，不建议为凑完成项重启或安装。实际补齐由主AI统一缺口并给明确写窗口；本子任务只保存报告。

## 范围与限制

- 没有认证GET EULA/账户/GAV或原设计/素材内容；没有导入、重建、迁盘、账号或配置更改。
- 没有读取密码、Webhook、密钥、Env/Cmd/health日志；备份路径仅stat，不导出归档，不递归private/home。
- 没有触OW规则或推送本地完整规则；没有Java业务/Macprobe动作。
- 证据见[media-audit.json](media-audit.json)；失败/依赖均按采样时点解释，不能推广成长期SLO/RPO或物理内存维修证明。
