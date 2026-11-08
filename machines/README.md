# 按机器组织的配置与文档

更新：2026-11-07，Asia/Shanghai。此处为PVE宿主、最后保留的12个来宾与3份模板建立独立目录，共16份。iDRAC属于PVE物理机管理面，记录在pve目录；已删除的旧VM/QA不重新建成现役对象。

**2026-11-08基础服务恢复并已按角色复验；用户本轮暂不迁移。** 每机配置合同与新审计分别保管，不是含秘密的完整恢复包；当前状态见[恢复记录](../recovery/20261108/README.md)。原11月7日离线目录整理证据保留历史意义。

## 机器入口

| 类型 | 目录 | 地址 / 状态 |
| --- | --- | --- |
| PVE宿主 | [host · pve](pve/README.md) | 192.168.21.22 |
| LXC | [100 · cf-tunnel](ct100-cf-tunnel/README.md) | 192.168.19.5 |
| VM | [190 · network-gateway](vm190-network-gateway/README.md) | 192.168.19.1 |
| VM | [200 · data-prod-db](vm200-data-prod-db/README.md) | 192.168.19.10 |
| VM | [201 · data-prod-infra](vm201-data-prod-infra/README.md) | 192.168.19.11 |
| VM | [210 · data-test](vm210-data-test/README.md) | 192.168.19.20 |
| VM | [220 · publish-service](vm220-publish-service/README.md) | 192.168.19.30 |
| VM | [221 · artifact-service](vm221-artifact-service/README.md) | 192.168.19.31；合并验收后退役，尚未退役 |
| VM | [230 · java-prod-01](vm230-java-prod-01/README.md) | 192.168.19.40 |
| VM | [240 · java-test-01](vm240-java-test-01/README.md) | 192.168.19.45 |
| VM | [250 · penpot-service](vm250-penpot-service/README.md) | 192.168.19.50 |
| VM | [260 · nas-media](vm260-nas-media/README.md) | 192.168.19.60 |
| VM | [270 · ops-service](vm270-ops-service/README.md) | 192.168.19.70 |
| 模板 | [9001 · tpl-docker-base](tpl9001-docker-base/README.md) | 无服务IP |
| 模板 | [9010 · tpl-linux-base](tpl9010-linux-base/README.md) | 无服务IP |
| 模板 | [9011 · tpl-java-acceptance](tpl9011-java-acceptance/README.md) | 无服务IP |

## 每个目录的文件

| 文件 | 用途 |
| --- | --- |
| `README.md` | 职责、网络/资源/存储、依赖、维护方式及证据限制 |
| `config.json` | 非秘密机器配置合同，资源与身份对应plan；含最后验收时点、当前基础恢复范围与证据 |
| `config-sources.json` | 原始配置/工具/证据索引；path相对仓库根，按current-contract、historical-evidence、pending-candidate区分 |
| `configs/`（按需） | 可确认来源的非秘密快照；须带source路径与SHA，不能不加判断直接应用 |

来源SHA只锁定本地仓库文件版本，不证明它与来宾现役文件相同；修改源文件后先审核差异，再同步受影响索引的SHA，不能盲改hash凑通过。

`config.json`里的机器身份与资源由[plan.json](../plan.json)约束。修改这些配置时同时维护源合同并运行校验，避免产生多份互相矛盾的现役说明。原infra/network19/cleanup文件继续保留为技术源或历史证据，没有通过复制新目录就改变其适用阶段。

## 发布与Nexus的两个视图

目标中只保留220 `publish-service`承担发布与Nexus，主IP30+服务alias31、6CPU8GiB；但实际移交尚未执行。因此220目录记录当前4CPU4GiB/30与单独目标，221目录仍记录当前来源身份和待退役条件。不能为了凑目标11实例而提前抹去221的配置，也不能同时把31登记为两台现役VM所有。

合并目标合同见[17合并架构](../17-publish-artifact-consolidation.md)。未来验收后更新现役清单与目录状态，保留必要源/回退记录；不能仅改目录名代替迁移。

## 秘密、操作与检查

不保存.env实际值、密码、token、webhook、SSH私钥、数据库或VMA/磁盘/备份归档。CF凭据备份仅PVE；发布私钥仅220，不能为补充本目录导出220整机。来源索引不应指向private，秘密保管位置只能在受控运维指引里解释。

目录中出现命令和配置不授权执行；先读[当前交接](../11-live-handoff.md)和[人工手册](../19-manual-operations.md)。Java业务不部署、publisher继续fenced、Mac外部探针不需要，移出现行及后续工作。

在仓库根目录执行：

```sh
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
```

校验只检查本地身份、资源、来源路径与快照SHA，不判断服务器实时健康，不执行SSH、Docker或部署。

本次目录整理的[离线验收记录](validation.json)包含独立副本检查和配置漂移负例；不证明当前服务器在线。
