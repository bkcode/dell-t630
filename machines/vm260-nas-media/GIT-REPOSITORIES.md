# VM260 · nas-media：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/10`派生；机器位置`machines/vm260-nas-media`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：**官方现役组件＋用户fork待选迁移**（`official-runtime-user-fork-planned`）。
- 当前说明：OMV/Samba与现役Jellyfin仍按原软件包/官方镜像；用户bkcode/jellyfin是服务端fork，仅密钥准备/上游类型核对，尚未由本任务克隆或替换NAS镜像。电视客户端改造不等于此服务端源码更新。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/nas](../../infra/nas)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `jellyfin` | [bkcode/jellyfin](https://github.com/bkcode/jellyfin) | master (GitHub default observed 2026-11-10; not a deployment selection) | 用户fork的Jellyfin服务端，未来NAS自定义源码候选；当前仍官方镜像 |

## 共享库依赖来源

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 官方上游参考与产物归属

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `omv-upstream` | [openmediavault/openmediavault](https://github.com/openmediavault/openmediavault) | 仅官方源码参考；未登记本机Git分支 | NAS管理系统源码参考，不是Jellyfin fork |
| `jellyfin-upstream` | [jellyfin/jellyfin](https://github.com/jellyfin/jellyfin) | 仅官方源码参考；未登记本机Git分支 | 现役官方Jellyfin服务端镜像的上游参考 |

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## NAS官方现役与用户fork计划

当前仍为官方OMV/Samba与官方Jellyfin镜像，`bkcode/jellyfin`未由本任务clone、编译或替换现役镜像。它是Jellyfin服务端/API fork，parent为`jellyfin/jellyfin`，不是OMV源码，也不是Android-TV客户端改造。

GitHub观察到default branch为master，仅是本次公开元数据观察，不是发布分支/版本选择或未来自动升级指令。未来替换须另审数据/插件/客户端兼容与回退，不能因已准备一个key就切镜像。

## 仓库认证元数据（不是服务器已安装证明）

用户报告GitHub的8个Deploy Key已配置；这些引用记录管理Mac `~/.ssh/deploy-keys/bkcode/`已准备的仓库身份命名。本轮仅Penpot有独立读取验证，其他7个未逐一重测；不含私钥、公钥正文或口令。只读是配置目标，不能因SSH身份名称就推断GitHub已完成注册/全部授权，更未通过push探测写权限。服务器安装/分发未由本任务执行或核验。

| 仓库ID | key basename | SSH alias | 读取验证范围 |
| --- | --- | --- | --- |
| `jellyfin` | `jellyfin_ed25519` | `github-bkcode-jellyfin` | GitHub registration/read access not reverified in this documentation task |

GitHub只读Deploy Key应不勾Allow write access；用户报告配置完成不等于本轮已独立重测所有key。除Penpot的管理Mac读取实证外，不将其他仓库写成本轮已实际read验证；服务器key未由本任务落地。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。
