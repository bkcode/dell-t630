# VM210 · data-test：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/5`派生；机器位置`machines/vm210-data-test`，身份与资源仍以[plan.json](../../plan.json)为准。

**这是来源/计划文档，不是已clone、部署、分发Git私钥或重跑初始化的证明。** 本轮本文只本地写入，没有SSH、git clone/fetch/pull/push、构建或服务操作。现役状态、上游参考与后续源码计划分开解释。

## 本机结论

- Git使用方式：**仅配置来源；没有用户业务源码取用**（`configuration-only`）。
- 当前说明：测试四组件；导入的Nacos配置/Puyu数据库不代表业务程序已部署或自动关联Git库。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/data](../../infra/data)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 用户应用/构建输入仓库

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 共享库依赖来源

本机未在总表登记此类用户仓库；不得据角色名编造仓库。

## 官方上游参考与产物归属

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `mysql-upstream` | [mysql/mysql-server](https://github.com/mysql/mysql-server) | 仅官方源码参考；未登记本机Git分支 | 官方MySQL源码参考，现役按固定镜像，不在数据机编译源码 |
| `nacos-upstream` | [alibaba/nacos](https://github.com/alibaba/nacos) | 仅官方源码参考；未登记本机Git分支 | 官方Nacos源码参考；配置正文/数据不随Git迁移 |
| `redis-upstream` | [redis/redis](https://github.com/redis/redis) | 仅官方源码参考；未登记本机Git分支 | 官方Redis源码参考；当前镜像版本及许可分别核对 |
| `rabbitmq-upstream` | [rabbitmq/rabbitmq-server](https://github.com/rabbitmq/rabbitmq-server) | 仅官方源码参考；未登记本机Git分支 | 官方RabbitMQ源码参考 |

官方上游链接用于追踪组件来源，不表示本机从源码编译、已有origin或跟随默认分支；实际版本/镜像digest/包版本以机器合同和对应实现的带时点回执为准。

## 认证与运行边界

本机未登记业务Git Deploy Key需求；不要为“每机有Git来源文档”额外分发私钥。基础包/镜像的上游参考不是用户私有仓库授权。模板与230/240运行机不带业务Git私钥，CF token/数据库/配置正文与Git源码互不替代。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。
