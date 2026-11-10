# VM220 · publish-service：Git来源与取用边界

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/6`派生；机器位置`machines/vm220-publish-service`，身份与资源仍以[plan.json](../../plan.json)为准。

本页维护总表派生的来源与取码计划，并单列后续获准的导航部署事实。文档编辑本身没有SSH或Git远程操作；导航最新实际状态以[统一内网HTTP交付](../../evidence/internal-http-20261110/README.md)为证，首次HTTPS回执只作历史。登记仓库不代表整仓库已clone、server Git key已分发或业务已上线。

## 本机结论

- 总表Git使用方式：**业务构建/部署源码仍为计划**（`build-source-planned`）；后续独立授权的导航模块已按固定五文件release部署，见下一节。
- 当前说明：后续发布机的源码取用计划：部署工具deploy+5后端。尚未由本任务clone/配置server keys或证明deploy工具已适配Puyu；现役受限发布链仍来自infra/publisher且fenced，Java业务不启。common-lib只构建/发布库制品。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/publisher](../../infra/publisher)、[infra/java](../../infra/java)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 已部署的导航模块：精确例外

用户新增并收窄为无需账号密码、只预览跳转的内网导航。现役仅取 `bkcode/deploy` 的 `service-directory/server.py`、`services.json`、三个Web文件，绑定当前提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`；[最新导航应用回执](../../evidence/internal-http-20261110/navigation-links-applied.json)登记每文件SHA256。ddccc2b是此前布局阶段。`63b8c08` 的首次HTTPS[source-manifest](../../evidence/service-directory-20261110/source-manifest.json)仅是历史。管理机项目位于 `/Users/yangzhaohui/work/www/finger/finger-master/projects/deploy`，发布机源码路径约定为 `/var/www/finger/finger-master/projects/deploy`；运行release独立位于 `/opt/dell/service-directory/releases/<SHA>/`，并非把整个deploy工作树直接运行或安装所有候选业务。

入口 **[http://192.168.19.30:9080/](http://192.168.19.30:9080/)** 按用户要求使用HTTP，移除顶部栏并使用全宽紧凑布局；不加载TLS或登录凭据。匿名只读，不调用原发布链、不探测URL；未来清单改项目Git后提交新SHA，再部署新release/只重启导航。无应用密码或运行state，也不读取/复制旧deploy配置、MCP jobs、Git或publisher私钥。Linux UID/GID2001仅隔离导航进程，不是应用账号。[手册与验收边界](../../evidence/service-directory-20261110/README.md)。

[源码Git状态](../../evidence/service-directory-20261110/source-git-state.json)记录：任务前本机main已比观测到的GitHub main `593069eb54a723ee0e63f85b937b9981b39ac1ec` 领先4条用户提交；本次新增自身8文件提交 `63b8c08`（父 `81148e8614ee5c49e6f9e4d1b85aebef8adfb33d`），**已本机提交、未push**，避免顺带发布原4条提交。没有amend/rebase/force。现役五文件确由git show精确提交导出，日后维护只能取已审查明确提交，不能git pull旧main覆盖。Dell配置文档独立交付不代表deploy源码已推到GitHub。

上述源码Git记录与首次[重启/浏览器/后检](../../evidence/service-directory-20261110/README.md)属于63b首次HTTPS阶段。后续仅本机提交HTTP变更 `c141506ec6a59dd7f123cabc00f099f1cf87d4e1` 和全宽布局 `ddccc2b98bbb3dfdc9de649443dc3fcdc7b4860f`，仍未push、未改写4条既有用户提交。随后新增FileBrowser链接HTTP提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`，共4条任务提交仍未push；运行release现为d56提交的精确五文件；旧TLS证书/私钥只留未启用历史。最新[统一内网HTTP记录](../../evidence/internal-http-20261110/README.md)及[14:28后检](../../evidence/internal-http-20261110/final-postcheck.json)为准，FileBrowser链接HTTP、14条/topbar0/全宽保持且原服务不变；不借旧验收扩大证明新布局或目标站点可达性。

这不证明 `bkcode/deploy` 已适配Puyu部署，更不证明五个后端已上线；Java仍停用、publisher fenced、common-lib仍只是共享库。表中 `build-source-planned` 保留业务取码计划语义，导航release另按本节证据登记。

## 用户应用/构建输入仓库

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `deploy` | [bkcode/deploy](https://github.com/bkcode/deploy) | main (management local checkout observed) | 仅service-directory模块精确提交已作为五文件导航release安装；原部署工具/Puyu发布适配仍候选 |
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
