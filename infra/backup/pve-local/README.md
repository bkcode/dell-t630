# 已退役：旧11来宾全机自动备份

更新：2026-11-09。**本目录是历史方案与代码，旧`dell-local-nightly` job已disabled，旧whole-VM告警组退役；不可重跑install/start/enable或据本页重新启用。** 用户最新仅自动备份正式数据库/Nacos配置，实际方案和状态见[新中央入口](../../../completion/20261109-prod-db-scope/README.md)。

## 保留的历史事实

原方案曾对100/190/200/201/210/221/230/240/250/260/270固定11来宾做snapshot，排除220；[首轮成功](../../../completion/20261109/backup-first-success.json)全部zstd/native验证、原生OK/退出0，共19,747,582,801 bytes。15:56曾启用03:30与3/7/4保留，**随后被用户最新范围取代并停用**，见[停job回执](../../../completion/20261109-prod-db-scope/whole-vm-job-disabled.json)、[旧规则退役](../../../completion/20261109-prod-db-scope/whole-vm-rules-retired.json)。不要把历史enabled当当前状态。

原storage `dell-local-backup`、归档 `/mnt/pve/store/dell-artifacts/scheduled-backups/dump`及root700/600边界保留；原11档及原21清理回退档均不自动删除。CF历史档可能含token，只留PVE，禁止导出Mac/Git/Nexus；220发布私钥一直只留220，没有整机备份许可。

历史完整性检查、权限修正、LXC暂存0711/UMask兼容与失败/取消记录保留在[早前交付记录](../../../completion/20261109/README.md)。VM snapshot不等于应用逻辑/跨来宾事务一致，原全机档没有因此完成恢复演练或异机灾备。

## 当前取代方案

[新首轮与timer](../../../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)只导出VM200 `nacos_prod`（唯一非系统库、12表、正式业务schema尚未创建），3301B逻辑SQL gzip通过CRC/SHA，锁已释放，timer enabled、下一次2026-11-10 03:30，GFS最近3/每日7/每周4。新目的地`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600。

新增未列白名单的数据库会拒绝告警，需显式更新；其他VM/OS、测试、Redis/Rabbit、Nexus/Penpot/NAS/Ops/CF及发布私钥不纳入自动。新`dell_prod_db_backup_*`三规则[已热载](../../../completion/20261109-prod-db-scope/alerts-installed.json)，原Prom身份/三名/接收对象保持，无testsend。本轮无restore、迁移或Java业务，不签独立DR/RPO；Mac探针不需要。

## 历史代码入口（禁止直接重跑）

[policy.json](policy.json)、[hook.py](hook.py)、[install.py](install.py)、[首轮启动器](start-first-run.py)、[指标审核](metrics-review.md)、[告警审核](review.md)只作历史实现与回退分析；不存在从本目录自动恢复旧计划的当前任务。归档处置或未来恢复必须新鲜核准对象/依赖/完整性，不通配删除旧档、不覆盖现役数据。
