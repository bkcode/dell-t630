# 本期范围与验收边界

更新：2026-11-07。当前因UEFI0058 POST/先前DIMM_B1 SEL事件暂停服务器操作；本轮在本地同步文档、规则与暂停状态，编写人工手册并进行Git交付，不远程修改服务器；实际Git结果见[交接记录](20-git-and-handoff.md)及交付证据。[硬件记录](cleanup/hardware/DIMM_B1-incident.json)不等于根因已确诊。最后完整服务验收02:35:01+08，最后成功PVE操作02:44:29+08；历史passed与最后15UP不证明现在在线。

## 当前交付合同

最后核验清单为12角色（11VM+1LXC）和3模板9001/9010/9011，43vCPU/85GiB；正式230与测试240各一运行基础，Java业务不部署，publisher fenced。9guest+3模板安装fish4.0.2-1，默认Bash，CF/Penpot/Ops及PVE宿主排除。数据、Penpot、NAS、内部Lark保留已验范围；NAS为家用影音与游戏文件库，不是正式唯一备份目标。

Nexus仍是最后验收的221独立角色，220仅standby。合并已获[明确短停授权](cleanup/nexus/maintenance-authorized.json)，未执行，待硬件恢复与fresh冷备/身份/网络/监控/回退门禁。不能再写等待同项用户许可，也不能把授权写成合并成功。

| 验收集合 | 状态含义 |
| --- | --- |
| [原38项](acceptance.json) | 26项原阶段历史passed，12项future/manual pending；旧测试五服务E2E不代表仍部署 |
| [清理10项](cleanup/acceptance.json) | 9项历史passed，Nexus合并1项pending且已授权 |
| REC恢复6项 | 硬件、冷备、数据身份、网络、监控、回退均pending，未执行；不混入历史9项通过计数 |
| [阶段状态](phase-delivery.json) | 硬件暂停、当前live未验证；预算与角色以plan为准 |

## 原12项延期条件

| 用例 | 仍未完成的条件 |
| --- | --- |
| ACC-NET-003 | 新公网域名/Cloudflare账户侧路由与HTTPS；现有CF归档仅PVE |
| ACC-DATA-002 | 原Mac Nacos全量业务配置/Derby迁移；当前旧测试配置不激活Java业务 |
| ACC-DATA-003 | 选定真实异步业务的消费者重投、幂等与死信；基础持久化不代签 |
| ACC-JAVA-002 | 业务模块上线授权及多实例ID并发；当前不部署Java业务 |
| ACC-JAVA-003 | 定时/Outbox并发业务与受控副作用；不外发真实资金/券商/通知 |
| ACC-JAVA-004 | WS与多实例跨节点共享文件；旧单测试节点持久证据仅属历史 |
| ACC-PEN-002 | 公网HTTPS与真实SMTP；空默认口令/认证已有历史证据 |
| ACC-NAS-003 | 真实电视/播放器4K HDR、字幕音轨及连续播放 |
| ACC-NAS-004 | 真实PS4/PS5目标设备、格式与工具的文件传输；不下载游戏或电影 |
| ACC-NAS-005 | 已批准业务负载/SLO和真实混合负载；不编造容量承诺 |
| ACC-BAK-001 | 长期独立目的地、覆盖、保留与连续调度；家用NAS不能代替 |
| ACC-BAK-002 | 获批RPO/RTO、独立恢复硬件与完整灾备实演；初始隔离恢复不代签 |

Mac外部探针按用户明确选择保持停用；机内监控与T630同故障域，不承诺整机停机时独立外部通知。文档验收、历史实施、当前可用、业务验收、灾备恢复分别记录。
