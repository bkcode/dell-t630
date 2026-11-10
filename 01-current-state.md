# T630当前状态与历史证据

更新：2026-11-10，Asia/Shanghai。用户已明确恢复Nexus合并并移除独立artifact-service，覆盖11月8日暂缓范围。本次已完成源停服/关机、PVE冷备校验、220正常停机与6CPU8GiB/原盘/alias31移交，目标已启动；最终数据、身份、监控及220受控重启核验通过，221已退役，详见[本次交付](completion/20261110-nexus-merge/README.md)。

## 当前合同

VM220 publish-service承接Nexus，6CPU8GiB，primary19.30＋同NIC alias19.31；原build100GiB UUID16dc6067-56ef-4687-a314-edc6421f9ed4保留，原Nexus100GiB UUID239dc45a-b1f3-408b-a8ef-7afa77b52204唯一转入scsi2，挂/srv/nexus。Nexus原入口31:8081保持，管理仍30/220 host key。完整12来宾表见[首页](README.md)，机器合同见[plan](plan.json)及[逐机索引](machines/README.md)。

当前12来宾（11VM＋1LXC）/3模板、45vCPU87GiB、15监控目标已由本次最终回执确认；不能用旧目标图替代原生证据。Java业务不启，旧链fenced；deploy-public私有配置/APIkey及构建守卫保持。资源280仅NFS，FileBrowser已停用，不迁旧资源文件、不接业务图片HTTP。

## 历史时间线

| 时间/阶段 | 原生观察或用户决定 | 限制 |
| --- | --- | --- |
| 11月7日02:35/02:44 | 清理/网络/服务验收与最后事故前PVE操作 | 原JSON不改写为现在 |
| 11月7日UEFI0058 | iDRAC SEL指向DIMM_B1，不可纠正内存错误阻止启动 | 保留失败/日志，不以F1掩盖故障 |
| 11月8日 | 用户报告重插/更换并诊断通过，恢复基础检查、暂不迁移 | 当时EDAC0/RAIDOptimal不等于独立长期诊断 |
| 11月9日 | 自然重启后12实例/3模板/15UP，正式DB-only备份及隔离小档恢复 | [历史交付](completion/20261109-prod-db-scope/README.md) |
| 11月10日资源初建 | 增280后13来宾/3模板/16UP、NFS双客户端与280重启持久性 | [原始回执](completion/20261109-resources/final-postcheck.json)；非当前合并数量 |
| 11月10日工具增量 | Penpot取8a/引导关闭、Puyu设计导入、服务器MCP；发布器main213f CLI双模式 | 各自证据只签其范围 |
| 11月10日用户恢复Nexus合并 | 停源/冷备/唯一盘与31移交/目标启动；最终签收按新回执 | [本次交付](completion/20261110-nexus-merge/README.md) |

## 已交付基础与后续限制

- 正式200/201和测试210分离。测试Nacos36份原ID/name/group/body导入，两Puyu库51表1291快照行；原源/密码/权限边界保留，未启Java或切应用连接。
- deploy-public213f已同步，Linux65测试通过，CLI prod/main dev/dev；六上游dev全缺、工作树main保持，新dev预检failed为预期保护，prod身份未配置/真实发布关闭。旧5服务dev/main成功只历史。
- Penpotmain8a/11healthy，原账号/设计保持；Puyu3页58240图形19组件，旧7文件完整数据保持。Mac skill MCP改SSH stdio到250且默认Puyu，不导出token。
- 280仅NFS共享，230/240同/mnt/resources；root_squash与缺挂载根盘守卫保留，应用写入UMask0002。资源不自动备份，三模板本次未改。
- 网关190 WAN21.23/LAN19.1，OpenWrt静态路由；PVE转发全0、无NAT，LAN21/24、WG10.66/24授权保持，NFS另受精确exports限制。

## 自动备份和未签范围

只备正式MySQL/Nacos显式白名单，当前nacos_prod；03:30/GFS3-7-4/PVE落点，新增未列库拒绝告警。旧整机job已disabled、旧档保留。本次221冷备2,400,054,202字节仅PVE且SHA/zstd/VMA通过，不扩自动备份。220发布key只220，禁止整机备份/快照导出；CF备份只PVE。

仅3301B Nacos小快照已隔离恢复，完整业务恢复、RPO/RTO、独立DR、物理重启全流程、真实电视/转码和生产并发未签。Mac外部探针不需要。详见[人工手册](19-manual-operations.md)、[本次维护手册](completion/20261110-nexus-merge/usage-manual.md)和带时间原始证据；历史成功不自动覆盖新阶段。
