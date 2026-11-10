# VM220 · publish-service：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/6`派生；机器位置`machines/vm220-publish-service`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：**构建/部署源码计划，尚未在本机落地**（`build-source-planned`）。
- 当前说明：后续发布机的源码取用计划：部署工具deploy+5后端。尚未由本任务clone/配置server keys或证明deploy工具已适配Puyu；现役受限发布链仍来自infra/publisher且fenced，Java业务不启。common-lib只构建/发布库制品。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/publisher](../../infra/publisher)、[infra/java](../../infra/java)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `deploy` | [bkcode/deploy](https://github.com/bkcode/deploy) | main (management local checkout observed) | 部署工具候选；管理机工作树origin已核对，未证明已在220安装或已适配Puyu发布 |
| `puyu-auth` | [bkcode/puyu-auth](https://github.com/bkcode/puyu-auth) | main (management local checkout observed) | 认证业务源码候选 |
| `puyu-bff-web` | [bkcode/puyu-bff-web](https://github.com/bkcode/puyu-bff-web) | main (management local checkout observed) | Web BFF后端源码候选 |
| `puyu-common-lib` | [bkcode/puyu-common-lib](https://github.com/bkcode/puyu-common-lib) | main (management local checkout observed) | 共享库构建输入，不是独立运行服务 |
| `puyu-gateway` | [bkcode/puyu-gateway](https://github.com/bkcode/puyu-gateway) | main (management local checkout observed) | 业务网关源码候选 |
| `puyu-service-core` | [bkcode/puyu-service-core](https://github.com/bkcode/puyu-service-core) | main (management local checkout observed) | 核心后端业务源码候选 |

## 共享库依赖来源

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 官方上游参考与产物归属

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## 构建计划与当前受限发布链

计划取用`bkcode/deploy`＋五个Puyu后端仓库。`puyu-common-lib`是构建/发布的共享库，不能计成一个运行服务；管理机main分支观察不等于远端或220已部署。尚未证明deploy工具已经适配Puyu，不能直接套旧Finger发布命令。

现有220→240受限链仍由Dell `infra/publisher`提供，保持fenced；本次Git来源登记没有activate/rollback，也没有部署或启动Java。新Git Deploy Key与原220专用发布SSH key是两类身份，不能互相替换或将旧私钥复制出去。

## 仓库认证元数据（不是服务器已安装证明）

用户报告GitHub的8个Deploy Key已配置；这些引用记录管理Mac `~/.ssh/deploy-keys/bkcode/`已准备的仓库身份命名。本轮仅Penpot有独立读取验证，其他7个未逐一重测；不含私钥、公钥正文或口令。只读是配置目标，不能因SSH身份名称就推断GitHub已完成注册/全部授权，更未通过push探测写权限。服务器安装/分发未由本任务执行或核验。

| 仓库ID | key basename | SSH alias | 读取验证范围 |
| --- | --- | --- | --- |
| `deploy` | `deploy_ed25519` | `github-bkcode-deploy` | GitHub registration/read access not reverified in this documentation task |
| `puyu-auth` | `puyu-auth_ed25519` | `github-bkcode-puyu-auth` | GitHub registration/read access not reverified in this documentation task |
| `puyu-bff-web` | `puyu-bff-web_ed25519` | `github-bkcode-puyu-bff-web` | GitHub registration/read access not reverified in this documentation task |
| `puyu-common-lib` | `puyu-common-lib_ed25519` | `github-bkcode-puyu-common-lib` | GitHub registration/read access not reverified in this documentation task |
| `puyu-gateway` | `puyu-gateway_ed25519` | `github-bkcode-puyu-gateway` | GitHub registration/read access not reverified in this documentation task |
| `puyu-service-core` | `puyu-service-core_ed25519` | `github-bkcode-puyu-service-core` | GitHub registration/read access not reverified in this documentation task |

GitHub只读Deploy Key应不勾Allow write access；用户报告配置完成不等于本轮已独立重测所有key。除Penpot的管理Mac读取实证外，不将其他仓库写成本轮已实际read验证；服务器key未由本任务落地。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。
