# VM280 · resource-service：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/13`派生；机器位置`machines/vm280-resource-service`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：**官方固定native产物**（`native-official-binary`）。
- 当前说明：原NFS+官方FileBrowser固定v2.1.4-beta二进制，摘要由upstream.lock锁；无用户FileBrowser fork登记，不在来宾git pull跟随latest。管理元数据与共享资源分开。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/resources](../../infra/resources)、[infra/resources/filebrowser](../../infra/resources/filebrowser)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 共享库依赖来源

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 官方上游参考与产物归属

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `filebrowser-upstream` | [gtsteffaniak/filebrowser](https://github.com/gtsteffaniak/filebrowser) | 仅官方源码参考；未登记本机Git分支 | 现役官方v2.1.4-beta原生二进制/摘要锁；不是用户fork或源码checkout |

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## FileBrowser是固定binary，不是用户Git部署

NFS/页面公开配置属于Dell；FileBrowser Quantum使用官方v2.1.4-beta Linux AMD64固定binary与[upstream.lock](../../infra/resources/filebrowser/upstream.lock.json)，没有用户fork登记或本机Git拉取。beta不称stable，不追latest；升级需审核lock、renderer/launch门禁、installer与版本兼容，不是git pull。页面metadata/cache与共享目录分开，当前NFS/HTTPS管理权限与备份范围不因仓库索引改变。

## 认证与运行边界

本机未登记业务Git Deploy Key需求；不要为“每机有Git来源文档”额外分发私钥。基础包/镜像的上游参考不是用户私有仓库授权。模板与230/240运行机不带业务Git私钥，CF token/数据库/配置正文与Git源码互不替代。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。
