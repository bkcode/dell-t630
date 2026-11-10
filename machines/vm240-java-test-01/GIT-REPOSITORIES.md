# VM240 · java-test-01：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/8`派生；机器位置`machines/vm240-java-test-01`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：**运行基础/未来产物消费者，不直接取源码**（`artifact-consumer-runtime-only`）。
- 当前说明：仅Java运行基础，当前没有本次Puyu业务程序上线；未来接收220审定构建产物，不要求本机拉源码或放Deploy Key。common-lib为依赖库，不能按独立服务启动；NFS仍同/mnt/resources。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/java/runtime](../../infra/java/runtime)、[network19/java-template](../../network19/java-template)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `puyu-auth` | [bkcode/puyu-auth](https://github.com/bkcode/puyu-auth) | main (management local checkout observed) | 认证业务源码候选 |
| `puyu-bff-web` | [bkcode/puyu-bff-web](https://github.com/bkcode/puyu-bff-web) | main (management local checkout observed) | Web BFF后端源码候选 |
| `puyu-gateway` | [bkcode/puyu-gateway](https://github.com/bkcode/puyu-gateway) | main (management local checkout observed) | 业务网关源码候选 |
| `puyu-service-core` | [bkcode/puyu-service-core](https://github.com/bkcode/puyu-service-core) | main (management local checkout observed) | 核心后端业务源码候选 |

## 共享库依赖来源

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `puyu-common-lib` | [bkcode/puyu-common-lib](https://github.com/bkcode/puyu-common-lib) | main (management local checkout observed) | 共享库构建输入，不是独立运行服务 |

## 官方上游参考与产物归属

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `openjdk-upstream` | [openjdk/jdk](https://github.com/openjdk/jdk) | 仅官方源码参考；未登记本机Git分支 | OpenJDK上游参考，JDK不是业务应用源码 |

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## 仅接收产物的运行基础

表中Puyu仓库只说明未来经220构建制品的代码归属，不表示本机clone或编译。后续只接收经审immutable构建产物，不直接git拉取、不放Git Deploy Key；Java业务仍不启。`puyu-common-lib`只是依赖库，不按独立服务启动。NFS共享仍同`/mnt/resources`，本次不改它或业务profile。

## 认证与运行边界

本机未登记业务Git Deploy Key需求；不要为“每机有Git来源文档”额外分发私钥。基础包/镜像的上游参考不是用户私有仓库授权。模板与230/240运行机不带业务Git私钥，CF token/数据库/配置正文与Git源码互不替代。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。
