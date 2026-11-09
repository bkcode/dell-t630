# 核心基础服务fresh审计 · 2026-11-09

采集：2026-11-09 14:42:56–14:43:40（Asia/Shanghai）。使用既有严格SSH target经PVE连接VM200/201/210/230/240，未重新trust、未修改known_hosts。完整脱敏数据及逐项结果见[core-audit.json](core-audit.json)。只写本地两份证据，没有服务器变更。

## 当前运行基础

| VM | 网络与基础 | 持久化/业务边界 | 结果 |
| --- | --- | --- | --- |
| 200 data-prod-db | hostname/19.10/GW与DNS19.1正确，NTP同步，exporter19.10:9100 | `/srv/dell-data`原UUID/ext4/rw，监督active，1容器healthy/RestartCount0 | 基础通过 |
| 201 data-prod-infra | hostname/19.11/GW与DNS19.1正确，NTP同步，exporter19.11:9100 | `/srv/dell-data`原UUID/ext4/rw，监督active，3容器healthy/RestartCount0 | 基础通过 |
| 210 data-test | hostname/19.20/GW与DNS19.1正确，NTP同步，exporter19.20:9100 | `/srv/dell-data`原UUID/ext4/rw，监督active，4容器healthy/RestartCount0 | 基础通过 |
| 230 java-prod-01 | hostname/19.40/GW与DNS19.1正确，NTP同步，JDK21.0.13 | finger存在、Java进程0；旧五unit not-found/inactive且非enabled | 运行基础通过，无业务部署 |
| 240 java-test-01 | hostname/19.45/GW与DNS19.1正确，NTP同步，JDK21.0.13 | finger存在、Java进程0；旧五unit not-found/inactive且非enabled | 运行基础通过，无业务部署 |

五台failed units均空，fish4.0.2、root/ub默认Bash；exporter与collector timer正常。oneshot collector可在采样时inactive或短暂activating，不等于故障。五台`NTPSynchronized=yes`、`NTP=yes`；数据节点systemd-timesyncd未加载不能据此当作没有时间同步，实际替代daemon本轮未盘点。首次合并属性的timedatectl探针输出为空，已改逐属性只读复核并保留限制说明，没有更改时间或服务。

## 真实搭建缺口：应用自动备份

| VM | 已观察到的工具/目录 | 定时器 |
| --- | --- | --- |
| 200 | `/root/dell-application-backup.py`；`/srv/dell-data/_app_backups`700、root属主；旧隔离恢复工具目录存在 | 只有`dpkg-db-backup.timer`匹配，无应用备份timer |
| 201 | 同上 | 同上 |
| 210 | 扫描路径中无匹配备份脚本、无上述应用备份目录 | 同上 |
| 230/240 | 无应用备份脚本匹配，符合无业务基础角色 | 仅dpkg定时器；不为无业务节点凑数据库备份 |

`dpkg-db-backup`是Debian包管理数据库备份，不能作为MySQL/Nacos/Redis/Rabbit的数据备份。200/201有手动工具和旧目录不等于已建立自动备份、保留、独立目的地、失败通知或恢复保证。该缺口应保留为P2待补齐，不能写“基础搭建全部完成”。

这是有界盘点：查看了全部loaded/installed systemd单元中backup/restic/borg/duplicity/rclone匹配项、`/opt/dell`等指定根下的脚本路径名和cron目录匹配文件名；没有读取cron内容、外部调度或每个自定义名字任务，不能排除别处存在不匹配命名的调度。具体扫描根/深度在JSON中。没有读取脚本或归档内容，也没有执行备份工具。

## 交主AI的受控补齐建议

1. 为200/201/210明确应用一致性范围、19网角色与精确挂载UUID门禁，保持正式/测试目录、身份和输出分离。先审核200/201已装工具是否与当前公开代码及19网配置匹配；210需要单独测试角色支持，不能直接复制只支持正式hostname的旧脚本。
2. 约定目标容量/权限、锁、磁盘余量、保留策略与失败观测后，准备guest-only systemd service/timer；MySQL/Nacos、Redis和Rabbit消息/拓扑分别按一致性边界处理。Rabbit definitions不含消息，不把配置备份称为全量恢复。
3. 避免把秘密、整个private目录、CF资料或220发布私钥夹带到备份；不增加迁移/Nexus合并/Java业务范围。本轮不执行真实导出，定时调度实际成功与隔离恢复需后续精确窗口留证；独立目的地及真实RPO/RTO另验。
4. 已健康基础组件不重装、不重跑prepare/deploy/fixture。LLMNR5355监听保留作可选精简项，未证明妨碍当前使用，不以此扩大本轮网络变更。

## 验收限制

本轮没有读DB认证/业务schema内容、Nacos配置或消息，正式空业务与测试隔离是保留合同，不是本轮数据审计结论。没有备份、恢复、数据迁移、Java业务、Nacos发布、容器重启、软件安装或PVE写入。Docker只采ID/State/Health/RestartCount，不读Env/Cmd/healthlog。现有基础健康通过和自动备份缺口分别保留，不用历史fixture或旧备份目录代替本轮完成证明。
