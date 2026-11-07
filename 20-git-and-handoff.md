# Git 与资料交接

更新：2026-11-07，Asia/Shanghai。本仓库是部署知识与代码仓库，服务器当前因内存错误暂停；提交文档不代表部署恢复或 Nexus 合并完成。

## 仓库与阅读顺序

远端：`git@github.com:bkcode/dell-t630.git`。本机工作目录：`/Users/yangzhaohui/work/www/harness/dell`。

```sh
git clone git@github.com:bkcode/dell-t630.git
cd dell-t630
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
```

先阅读 [README](README.md) → [当前交接](11-live-handoff.md) → [人工操作手册](19-manual-operations.md)。操作前查看 `plan.json` 和对应验收证据的日期；严禁把旧候选、旧网段或历史成功记录当当前现场。

## Git 中有什么

| 目录/文件 | 内容 | 使用边界 |
| --- | --- | --- |
| 根目录编号文档 | 状态、架构、模板、访问、验收、手册 | README/交接优先；较早阶段的数字保留历史说明 |
| `plan.json`、`tasks.json` | 配置合同与任务登记 | 包含暂停和未完成项，不等同实时探针 |
| `evidence/` | 初次盘点和带日期的实施证据 | 不改写原执行结果，新增核验另留证 |
| `infra/` | 应用、NAS、监控、备份、发布链脚本 | 部分为旧网配置，不能整目录执行 |
| `network19/` | 独立网关与19网迁移代码/验收 | 历史stage/commit不重复执行 |
| `cleanup/` | 模板精简、fish、合并准备、硬件事件 | 合并未执行；以resume检查表为入口 |
| `scripts/` | 管理SSH、文档与Git检查 | 管理脚本需要私有凭据和可信host key |

## Git 中没有什么

`private/` 约19GB本机资料、数据库/导出、VM磁盘/ISO、应用备份、密码、真实webhook、SSH私钥和本机known_hosts均不提交。仓库不是完整备份；新电脑克隆后无法凭代码自动登录或恢复数据库。

本机受保护文件的位置见[凭据索引](12-service-access-and-operations.md)。如换电脑，由管理员通过受控渠道重新授权管理公钥并核验主机指纹；不要把私钥或整个 `private/` 加入Git。应用凭据按最小范围交接，不能在聊天/工单/提交中展示。CF备份仍仅PVE，发布私钥仍仅220；这两个边界不因换电脑或交接改变。

## 提交流程

在仓库根目录运行：

```sh
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

提交前人工审查变更；不要使用 `git add -f private`、force push 或把备份压缩后绕过忽略规则。检查脚本只报告风险位置，不输出秘密内容；通过是有限的规则检查，不保证发现所有未知凭据。

## 当前交接事实

- 最后完整验收：2026-11-07 02:35；12实例+3模板，15监控目标UP属于该时点。
- 最后成功PVE操作：02:44:29，更新规划文件，未关机或迁盘。
- 随后PVE不可达；用户控制台显示UEFI0058，历史SEL指向B1；当前服务器工作暂停。
- Nexus合并已有维护授权，220准备完毕、221未移交；先修硬件和重新验收，再由用户恢复执行。
- 源数据、受保护归档和中间证据保留。本轮没有清理服务器、删除本机私有资料或修改全局记忆。
