# Git 与资料交接

更新：2026-11-09，Asia/Shanghai。本仓库是部署知识与代码仓库；本轮fresh审计基础健康并补齐用户新范围的正式数据库/Nacos逻辑自动备份，不迁移数据。现行正式DB首轮3301B与03:30 timer已有成功回执，旧11来宾job停用、档保留；Git或文档通过不代替恢复演练、独立灾备或Nexus合并。当前状态入口：[当日交付记录](completion/20261109-prod-db-scope/README.md)。

## 仓库与阅读顺序

远端：`git@github.com:bkcode/dell-t630.git`。本机工作目录：`/Users/yangzhaohui/work/www/harness/dell`。

```sh
git clone git@github.com:bkcode/dell-t630.git
cd dell-t630
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
```

先阅读 [README](README.md) → [当前交接](11-live-handoff.md) → [人工操作手册](19-manual-operations.md)。操作前查看 `plan.json` 和对应验收证据的日期；严禁把旧候选、旧网段或历史成功记录当当前现场。

## Git 中有什么

| 目录/文件 | 内容 | 使用边界 |
| --- | --- | --- |
| 根目录编号文档 | 状态、架构、模板、访问、验收、手册 | README/交接优先；较早阶段的数字保留历史说明 |
| `machines/` | 每台宿主/来宾/模板的配置合同、来源索引与运维文档 | 离线整理、身份资源受plan约束，不含秘密或实时配置导出 |
| `plan.json`、`tasks.json` | 配置合同与任务登记 | 包含暂停和未完成项，不等同实时探针 |
| `evidence/` | 初次盘点和带日期的实施证据 | 不改写原执行结果，新增核验另留证 |
| `infra/` | 应用、NAS、监控、备份、发布链脚本 | 部分为旧网配置，不能整目录执行 |
| `network19/` | 独立网关与19网迁移代码/验收 | 历史stage/commit不重复执行 |
| `cleanup/` | 模板精简、fish、合并准备、硬件事件 | 合并未执行且本轮不做；旧resume不自动授权 |
| `recovery/`、`completion/` | 带日期的恢复/补齐与实时任务脱敏回执 | 当日README优先，部分进度不等于最终成功 |
| `scripts/` | 管理SSH、文档与Git检查 | 管理脚本需要私有凭据和可信host key |

## Git 中没有什么

`private/`本机受保护资料、数据库/导出、VM磁盘/ISO、应用备份、密码、真实webhook、SSH私钥和本机known_hosts均不提交。仓库不是完整备份；新电脑克隆后无法凭代码自动登录或恢复数据库。

本机受保护文件的位置见[凭据索引](12-service-access-and-operations.md)。如换电脑，由管理员通过受控渠道重新授权管理公钥并核验主机指纹；不要把私钥或整个 `private/` 加入Git。应用凭据按最小范围交接，不能在聊天/工单/提交中展示。CF备份仍仅PVE，发布私钥仍仅220；这两个边界不因换电脑或交接改变。

## 提交流程

在仓库根目录运行：

```sh
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
git status --short
git add -- .
python3 scripts/check_git_safety.py --staged
git diff --cached --check
git diff --cached --stat
git commit -m "docs: update Dell deployment handoff"
git push origin main
```

OW完整规则用户明确只留本地，`openwrt/rules-20261108/`已local exclude，`local/openclash-rules-20261108`不得push。只push已审公共分支，不执行push --all，也不强加ignored规则。提交前人工审查变更；不要使用 `git add -f private`、force push 或把备份压缩后绕过忽略规则。检查脚本只报告风险位置，不输出秘密内容；通过是有限的规则检查，不保证发现所有未知凭据。

## 当前交接事实

- 当日fresh验收入口为[11月9日交付](completion/20261109-prod-db-scope/README.md)：自然重启后12running/3tpl、15UP、forward guard持久与EDAC0/RAIDOptl；11月7日02:35仅历史。
- 11月7日02:44:29仅为故障前最后成功同步，不再当成当前最后PVE操作；原故障时间线不改写。
- 随后PVE不可达；用户控制台显示UEFI0058，历史SEL指向B1；11月8日恢复记录另行保存，不覆盖该历史。
- Nexus合并已有维护授权，220准备完毕、221未移交；基础已恢复，但用户暂不迁移；将来明确恢复该任务后fresh核验。
- 现行自动备份仅VM200正式MySQL/Nacos外部元数据库，当前只有nacos_prod/12表、正式业务schema未创建；新库未列白名单直接拒绝告警、需审核更新。首轮3301B已校验、03:30 timer enabled/GFS3-7-4，PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600，见[新中央入口](completion/20261109-prod-db-scope/README.md)及[首轮回执](completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)。其他数据不自动备份；旧whole-VM jobdisabled、19,747,582,801B和21档保留不自动删除。新db-only三规则已[热载](completion/20261109-prod-db-scope/alerts-installed.json)，原Prom identity/三名/接收对象不变，无testsend。仅下述小档已临时隔离恢复，未签完整业务恢复/异机DR/RPO，SQL与私有manifest不进Git。
- 本轮空闲iperfserver已停用且留包、新备份namespace已安装，这些有各自回执；本页同步只改文档，不删除源数据/私有资料或修改全局记忆。

**仅这份3301B `nacos_prod`小快照已完成VM210临时隔离恢复**：12表10行，活跃`config_info`为空，10行为历史、命名空间及认证/权限元数据。源备份SHA、timer及VM210原4服务保持、临时资源已清理；不扩签业务库、RPO/RTO或异机灾备，见[限定恢复收尾](completion/20261109-prod-db-restore/README.md)。

当前业务边界保持：Nexus不合并/数据不迁移、Java业务不启、Penpot实际ff提交不更新main；用户不需要Mac外部探针，不列当前或后续待办。
