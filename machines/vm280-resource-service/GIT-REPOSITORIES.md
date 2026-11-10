# VM280 · resource-service：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/12`派生；机器位置`machines/vm280-resource-service`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：总表原`native-os-packages`记录保留历史来源；现役NFS使用系统包/本库基础设施配置，不从业务Git拉取或编译。
- 当前说明：仅NFS现役，FileBrowser已inactive/masked、8080关闭。原官方固定v2.1.4-beta binary与lock只作来源及回退历史，无用户FileBrowser fork或现役Git部署；共享文件/state/凭据保持。当前[停用证据](../../completion/20261110-nfs-only/README.md)与[使用手册](../../completion/20261110-nfs-only/usage-manual.md)。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/resources](../../infra/resources)、[infra/resources/filebrowser](../../infra/resources/filebrowser)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 共享库依赖来源

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 官方上游参考与产物归属

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `filebrowser-upstream` | [gtsteffaniak/filebrowser](https://github.com/gtsteffaniak/filebrowser) | 仅官方源码参考；未登记本机Git分支 | 已退休官方v2.1.4-beta原生二进制/摘要锁的历史来源；不是现役页面、用户fork或源码checkout |

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## FileBrowser历史产物与NFS现役边界

NFS公开配置属于Dell，现役服务来自系统NFS包；没有本机业务源码checkout或Git Deploy Key需求。FileBrowser Quantum此前使用官方固定binary与[upstream.lock](../../infra/resources/filebrowser/upstream.lock.json)，现两个unit已停用并masked、专属输入表和HTTP健康检查已撤，不跟随上游更新。其state/cache与凭据仅保留本机受保护历史，不恢复页面、不重跑初始化，资源/备份权限不因仓库索引改变。

## 认证与运行边界

本机未登记业务Git Deploy Key需求；不要为“每机有Git来源文档”额外分发私钥。基础包/镜像的上游参考不是用户私有仓库授权。模板与230/240运行机不带业务Git私钥，CF token/数据库/配置正文与Git源码互不替代。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。

当前Git映射已随221归档重排，资源280为native-os-packages/infra/resources，无现役FileBrowser上游依赖。原filebrowser-upstream及binary仅留退休历史；NFS配置/数据正文不因本次映射同步而改变。
