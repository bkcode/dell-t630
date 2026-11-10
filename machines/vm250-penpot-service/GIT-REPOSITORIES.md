# VM250 · penpot-service：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/10`派生；机器位置`machines/vm250-penpot-service`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：**历史定制源码导入；未启用直接远端更新**（`custom-code-imported`）。
- 当前说明：现役main/ff1783e clean、无origin，11容器healthy；管理Mac专属key及临时clone通过，GitHub main仍9aedbb0缺两条现役改造。先补远端版本再另审部署，不从旧main覆盖。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/penpot](../../infra/penpot)、[infra/penpot/runtime/health-supervision](../../infra/penpot/runtime/health-supervision)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `penpot` | [bkcode/penpot](https://github.com/bkcode/penpot) | main (user required) | 用户指定main；现役保留ff1783e改造，通过历史Git bundle导入，不从远端旧main覆盖 |

## 共享库依赖来源

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 官方上游参考与产物归属

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `penpot-upstream` | [penpot/penpot](https://github.com/penpot/penpot) | 仅官方源码参考；未登记本机Git分支 | 官方Penpot上游；不能替代用户bkcode/penpot的部署来源 |

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## 本次Penpot读取验证与现场的差别

[管理Mac Deploy Key验证](../../evidence/git-repositories-20261110/penpot-deploy-key-verification.json)证明repository-scoped身份可读取main，并做了**浅历史克隆＋完整工作树**核查；GitHub与临时checkout为`9aedbb011cd803eb615225ca21f7f47cb8c2fa09`。临时目录已移除，没有push、复制私钥、转发agent或服务端部署。它不等于下载了完整Git历史。

[来宾只读现场](../../evidence/git-repositories-20261110/penpot-runtime-readonly.json)13:20观察`/opt/dell/penpot/source`为main/`ff1783e7865af7aae571c985f03e057631b7af63`、clean、remote列表为空、origin字段不存在；11容器running/healthy。unit累计NRestarts=22，不能因为容器RestartCount0就称unit没有重启。此轮未诊断累计重启、未启停服务。

远端main与现役ff不同，不能从克隆验证推断服务器已升级或直接拉取已配置；保留本地两条改造，未来任何更新先核不可丢失的改动、选定immutable commit，再单独获准构建/发布。官方penpot/penpot只是上游，不替代用户bkcode/penpot。

## 仓库认证元数据（不是服务器已安装证明）

用户报告GitHub的8个Deploy Key已配置；这些引用记录管理Mac `~/.ssh/deploy-keys/bkcode/`已准备的仓库身份命名。本轮仅Penpot有独立读取验证，其他7个未逐一重测；不含私钥、公钥正文或口令。只读是配置目标，不能因SSH身份名称就推断GitHub已完成注册/全部授权，更未通过push探测写权限。服务器安装/分发未由本任务执行或核验。

| 仓库ID | key basename | SSH alias | 读取验证范围 |
| --- | --- | --- | --- |
| `penpot` | `penpot_ed25519` | `github-bkcode-penpot` | verified on management Mac for Penpot |

GitHub只读Deploy Key应不勾Allow write access；用户报告配置完成不等于本轮已独立重测所有key。除Penpot的管理Mac读取实证外，不将其他仓库写成本轮已实际read验证；服务器key未由本任务落地。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。
