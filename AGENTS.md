# Dell T630 仓库操作规则

## 入口与当前状态

- 本仓库位于 `/Users/yangzhaohui/work/www/harness/dell`，独立 Git 远端为 `git@github.com:bkcode/dell-t630.git`；harness 父目录不是本仓库。
- 每台机器的配置与文档入口是 `machines/README.md`；保留宿主、12来宾和3模板的离线合同/来源索引，不能把新目录当现场配置导出。机器身份与资源仍由plan约束，新增/修改后运行 `python3 scripts/validate_machines.py`。
- 先读 `README.md`、`11-live-handoff.md`、`19-manual-operations.md`、`plan.json`；资源/IP/角色以 plan 为准，历史证据必须带时间解释。
- **2026-11-07 用户暂停服务器工作，等待硬件处理；当前只整理文档并提交 Git。不得连接服务器、恢复迁移或发告警测试。**
- iDRAC 控制台 UEFI0058 阻止正常启动；此前 SEL 指向 DIMM_B1。不得把 F1、一次开机或网络恢复当成内存已修复，不清日志掩盖错误，不远程 powercycle，不指导带电插拔。
- 最后综合验收 2026-11-07 02:35：12 运行实例（11VM+1LXC）+3停止模板；最后成功 PVE 操作 02:44:29 仅同步规划。当前在线状态未复验，不能继续声称 15/15 实时 UP。
- Nexus 短停合并已获用户明确授权，此前同项授权缺口已满足；合并尚未开始。硬件稳定并获得用户恢复指令后再 fresh 检查，不重复索要同项许可，也不自动继续。

## 范围与安全边界

- 用户允许子 AI；主 AI 分配范围并验收。主 AI 独占 PVE 写、VMID/IP 分配；子 AI 默认只读宿主，来宾写必须有明确窗口。
- PVE root 为 `192.168.21.22`；来宾用户 `ub`，客户端密钥 `~/.ssh/yang_local_rsa`。严格校验 host key；可信来源为已有记录或受信 PVE QGA，不能关闭校验。
- `private/`、凭据、webhook、数据库和归档不得进 Git。秘密只放目录700/文件600；不打印真实值，不复制客户端私钥。
- CF 备份只留 PVE，禁止导出 Mac。发布专用私钥只留220：不读取/复制，不做会包含该私钥的220整机备份或快照导出。
- PVE/H730/store 保留；不得格式化现役卷、将宿主已挂载块设备并交 NAS 或允许两个实例同时写原 Nexus 数据盘。
- 原 Mac 数据与源环境保留；正式库空业务数据，本机数据只用于测试迁移。部署不自动授权真实交易或第三方外发。
- Lark 内部通知已授权且按原配置保留；Mac 外部探针本期明确停用，不自动恢复或要求系统隐私授权。

## 已交付合同

- PVE 只管理/二层桥，host forwarding 全0、无旧应用NAT；190 WAN21.23/LAN19.1 路由/DNS/DHCP，无NAT。OW route19/24 via21.23。
- 所有服务来宾在19网；同网东西向由 bridge MAC/IP/角色ACL隔离。10.66.66.0/24 已授权全服务访问，WireGuard peer 继续每客户端/32。
- 230/240 正式/测试运行基础各1；**不部署或启动Java业务**，测试五服务停用，publisher fenced；唯一Java验收模板9011无业务配置/秘密。
- 核心模板9010/9001，Java验收9011。旧15对象与临时9040–9045已受保护备份后清理，不重放destroy/stage/commit。备份完整性不等于每个旧实例都已恢复演练。
- fish 已装9来宾+3模板，默认 Bash 不变；排除100/250/270与PVE宿主，不自动chsh。
- Nexus 目前仍独立221/19.31；220/19.30仅准备。目标2206CPU8GiB、primary30+alias31、原UUID盘移交，验收后才退221；详情见cleanup/nexus/resume-preflight.md。
- 合并工具非一键幂等；不能重跑prepared stage，部分mount/commit须先按journal核对。不得并启两个31地址/两个数据库写者。

## 验证与交付

- 本地文档：`python3 scripts/validate_docs.py --json`；提交前：`python3 scripts/check_git_safety.py --staged`。
- 所有 live 结果标日期/时区、命令、成功/失败和限制；历史通过与当前暂停分开，未验收保持pending。
- 文档、计划、验收状态需同步；不降低校验门槛凑通过。旧10.63/DNAT/14角色/17targets只作历史，不再当部署入口。
- 用户已明确要求本轮整理并提交Git；仅提交本仓库经检查的非秘密资料。不得改全局memory，默认不删除唯一历史证据。
