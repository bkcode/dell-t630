> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 230 canary：先stage，OScommit后只应用监控

当前只完成本地包与helper，**尚未写230**。精确候选目录为`prepared/monitoring/vm230/`，内含六文件及`role-contract.json`。helper `apply-monitoring.py`默认不apply，只检查当前old SHA及stage SHA/配对catalog和新health；执行只由root协调员在单role窗口触发。

Root经已有可信QGA/严格hostkey管理通道将公开包、helper与`network19/contracts/230.json`复制到230 root-owned、不可group/world写的 `/root/dell-network19/staged/monitoring230/`（包中`etc/`和`opt/`层次保持）。不复制管理私钥、不改hostkey alias。OS旧IP仍在时可以运行：

```text
sudo python3 -I -B /root/dell-network19/staged/apply-monitoring.py --bundle /root/dell-network19/staged/monitoring230 --os-contract /root/dell-network19/staged/230.json --inspect
```

root完成原MAC `bc:24:11:1c:20:00` 的OSnetworkd事务后，来宾必须仅有新19.40/24、默认网关19.1、per-link DNS19.1。只有root明确创建0600窗口receipt才可apply：

```json
{"migration":"network19","vmid":230,"phase":"OScommitted-monitoring-window","parent_window_open":true}
```

```text
sudo python3 -I -B /root/dell-network19/staged/apply-monitoring.py --bundle /root/dell-network19/staged/monitoring230 --os-contract /root/dell-network19/staged/230.json --root-receipt /root/dell-network19/staged/230-window.json --apply-after-oscommit
```

本helper不执行OScommit或SSH，不改PVE/OW，不启动正式Java、不调用数据部署/通知发送。它先验证新IP在原MAC且旧IP已消失，GW/DNS一致；暂停原guest-health timer，保存root600旧六文件/原owner/mode/计时器启用状态，再以同目录rename原子写配对catalog→installer→通用collector→health→defaults→listen。原`/etc/default`实际ARGS空字节保留，旧listen只在drop-in精确替换。

执行daemon-reload、`--check-private-ip`，只restart exporter，最多15秒等待listener精确19.40:9100且无其它9100监听，不能把进程已fork当已bind；要求listener精确19.40:9100；以prometheus用户跑collector --check，不写textfile、不调用任何Lark。恢复原timer active/enabled状态。230无活动应用HTTP检查，正式业务应用保持不启动；候选127loopback检查不激活。

失败时exporter/timer停住并留下具体已写路径和root600备份，**不会在新OS上单独恢复old-only监听冒充回退成功**。root要做整体回退时先协调旧OS/MAC/桥路径，再逐文件恢复原owner/mode、daemon-reload和原exporter/timer状态，验证旧地址；新旧配置和OS必须一致。成功后由root只读核对新9100、下一分钟textfile时间戳/Prometheus targetUP，不能以collector --check签收HTTP2xx。

同一个工具可供其它11角色使用，各自已有exact contract，不能通用sed；230 canary通过后root逐role协调，媒体监督源码由其owner处理，Core只负责6个监控基线文件。190/104暂不自动加入12target。
