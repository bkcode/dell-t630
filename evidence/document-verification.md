> 此记录是初始文档阶段收据。当前实施状态见 [09](../09-implementation-progress.md)，最新本地检查见 [implementation/document-validation-latest.json](implementation/document-validation-latest.json)。

# 文档阶段验证记录（历史）

日期：2026-11-05（Asia/Shanghai）。结果：**文档验收通过，服务器实施未开始**。机器结果见 [document-validation.json](document-validation.json)。

## 本轮交付和验证范围

本轮创建了方案、模板与访问约定、应用迁移、家庭 NAS、验收标准和实施队列。4 个子 AI 分工撰写并交叉审查，主 AI 复核了最终文件和结构化清单。没有启动、克隆、重启、格式化或配置 PVE 来宾，也没有迁移、重建或停止本机应用。

- PVE 证据：[42 项只读检查](pve-audit-2026-11-05.json)，41 项退出 0；无 Corosync 的 `pvecm status` 退出 2，反映独立节点，非集群健康验收通过。
- 本机应用证据：[13 个容器的脱敏元数据和用量快照](local-services-2026-11-05.json)，来源是本机 OrbStack，不是 T630 目标部署。
- 验收：[38 个用例](../acceptance.json)，仅 ACC-DOC-001/002 已完成并有真实记录；其他 36 项实施验收 pending。
- 资源：13 个角色、53 vCPU、116.5 GiB，按保守 125 GiB 规划余 8.5 GiB；计算与模板策略均由校验器读取 plan.json。
- 密钥和账号：指定私钥的 PVE root 登录已验证；模板中 ub/公钥字段存在；未启动来宾，所以 ub 实际登录未验证。

## 交叉审查和处理

| 审查 | 发现与主 AI 处理 | 结果 |
| --- | --- | --- |
| pve_audit → README/plan/实施计划 | 将 NAS“不是唯一业务备份”收紧为“不作为正式业务备份目标” | 已统一 |
| migration_media → 架构/SSH | 增加 `ip -br addr` 采集；区分 ub、发布与业务运行身份 | 已补齐 |
| architecture_templates → 应用/NAS | OMV ISO 不继承模板账号：补创建/确认 ub 和注入公钥；首期 Jellyfin-only 配置防止旧单元启动全部影音工具 | 已补齐 |
| architecture_templates → Penpot | 分别记录跨架构平台 digest；停写边界覆盖后台 worker/GC/导入 | 已补齐 |
| pve_audit → 验收标准 | SMB 样本先保留再读取，独立测试文件验证删除；增加 NAS 缺失挂载负向测试；补 NAS 账号权限验收 | 已补齐 |
| 主 AI → 验收类型 | 登录/邀请/找回会产生会话或邮件，Penpot 对应用例改为受控修改测试 | 已纠正 |

以上修正均只写入 dell 文档，未覆盖原有 Penpot、nacos 或 home-cinema-nas 项目。

## 自动验证

```bash
cd /Users/yangzhaohui/work/www/harness/dell
python3 scripts/validate_docs.py --json
```

校验内容：必需文件与 JSON 结构、角色/资源计算、两个核心模板、验收 ID/字段/状态、Markdown 与 JSON 用例对应、实际文档验收凭证、本地文件链接及源文件行号、代码块配对、尾随空白、私钥/公钥原值残留。

主 AI 另行对文档和 JSON 扫描了私钥、公钥、Bearer 长值及 webhook URL 模式，未发现匹配。模式扫描不能替代人工敏感信息审查；本轮同时审查了 Docker 证据只包含允许字段，不保存环境变量值或进程命令行。

文档验收凭证：

- [ACC-DOC-001](acceptance/ACC-DOC-001/result.json)
- [ACC-DOC-002](acceptance/ACC-DOC-002/result.json)

本地链接检查通过不保证外部 URL 始终可访问；外部软件文档用于解释机制，当前实机事实以采集证据为准。

## 仍然待实施或验证

- RAID 级别、成员映射、缓存保护、完整盘健康；一块 SAS 盘基础摘要有 11 个重分配块，需进一步查证和处置。
- 新 VMID/IP、路由/VLAN/防火墙实现、IPv6 边界和地址冲突核查。
- 现有停止模板内部 OS、Java/Docker 版本及实际 ub 登录。
- 正式上线模块、TraScan Go 和前端承载、负载基线、应用内存和连接池预算。
- 独立备份目的地、实际 RPO/RTO、恢复演练和整机故障处置。
- NAS 真实终端 Direct Play、游戏文件传输方式、家庭负载与正式业务并发影响。

这些 pending 项不影响本轮文档交付完成，但会阻止将相应服务器或业务标为上线验收通过。无源码/API 契约变更，无需 publish；本轮没有 Git 提交，harness 根目录不是 Git 仓库。
