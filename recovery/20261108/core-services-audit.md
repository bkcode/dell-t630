# 2026-11-08 核心来宾只读恢复检查

采集：2026-11-08 20:16:13–20:18:22（Asia/Shanghai）。五台均使用既有 `control.guest(..., info=原target)` 严格SSH，经PVE跳转成功；没有重新trust或修改known_hosts。

结论：本次检查未发现需要补装或重新部署的核心基础服务。数据三台8容器全部running/healthy、RestartCount0；Java两台保持运行基础，无Java进程，旧五业务停用且不自启。主AI20:18收到用户“内存重新插拔/更换并诊断通过”的确认；本子任务仅检查来宾，未独立验证物理修复，本次可达不单独作为硬件健康保证。

| 来宾 | 严格SSH与网络 | 数据/运行基础 | 服务结果 |
| --- | --- | --- | --- |
| 200 data-prod-db | hostname/IP19.10正确，GW/DNS19.1 | `/srv/dell-data` ext4/rw，UUID与plan精确一致 | 监督active/success，1容器running/healthy，RestartCount0 |
| 201 data-prod-infra | hostname/IP19.11正确，GW/DNS19.1 | `/srv/dell-data` ext4/rw，UUID与plan精确一致 | 监督active/success，3容器running/healthy，RestartCount0 |
| 210 data-test | hostname/IP19.20正确，GW/DNS19.1 | `/srv/dell-data` ext4/rw，UUID与plan精确一致 | 监督active/success，4容器running/healthy，RestartCount0 |
| 230 java-prod-01 | hostname/IP19.40正确，GW/DNS19.1 | OpenJDK21.0.13可执行、finger账号存在、Java进程0 | 五旧业务unit not-found/inactive/MainPID0且不enabled；基础监控正常 |
| 240 java-test-01 | hostname/IP19.45正确，GW/DNS19.1 | OpenJDK21.0.13可执行、finger账号存在、Java进程0 | 五旧业务unit not-found/inactive/MainPID0且不enabled；基础监控正常 |

五台均failed units空，fish4.0.2，root/ub默认Bash。SSH/QGA/exporter active，collector timer active、oneshot服务inactive/success为正常状态。数据三台Docker与对应监督单元active。exporter只绑定各自19地址9100；数据组件监听各自指定19地址。系统解析器127.0.0.53为systemd-resolved本地stub，networkctl上游DNS实际19.1，不是错误DNS。

230/240首轮20:15–20:16返回“No route to host”，随后一次只读重试成功。主AI20:18:21观察两台running uptime仅42s/24s，与顺序开机尚未完成相符；本任务未启动任何VM，没有为该暂时状态更改网络或服务。首轮失败保留在JSON，不再作为未修故障。

## 补齐与清理建议

- 不重跑prepare/deploy/初始化/fixture：已观察的基础元数据正常，重部署没有必要。
- 230/240保持JDK基础与无业务状态；历史五服务not-found不属于缺项，不恢复旧release、不修改Nacos。
- Java两台存在systemd-resolved LLMNR TCP5355 wildcard监听。这不是服务故障；是否多余需先核局域网名称解析要求，未来如确认不用再单独最小配置审核。本轮未停用。
- 当前不用迁移、合并或清理源221；原12实例+3模板与正式/测试隔离保留。Publisher冻结、Mac外部探针停用保持，未访问220/221/CF。

## 本轮证明范围

仅网络/挂载/既有systemd状态、容器健康元数据与Java基础检查，没有数据库登录、namespace权限、业务schema内容、消息或数据一致性重测；不能据此签认原数据未变、端到端业务或完整备份恢复。Java版本由root只读执行，finger账号存在不等于本轮完成finger身份执行烟测。

Docker只输出ID、State.Status、Health.Status、RestartCount，未输出Env/Cmd/healthlog。监督日志只在内存分类计数，不输出原文。没有读取或复制秘密、业务数据，没有服务器文件写入、启停、安装、JAR/导入/Nacos操作。首次沙箱网络限制与随后获准的同范围只读SSH都留在JSON。

完整脱敏元数据及逐项布尔结果见[core-services-audit.json](core-services-audit.json)。
