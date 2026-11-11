# VM220 · publish-service：Git来源与取用边界

## 2026-11-11 Nexus本机配置对齐（保留额外仓库）

用户已选择只对齐本机配置、保留服务器额外7库，禁止删除任何仓库/制品。目标读取maven-public、dev写imnull-snapshots/prod写imnull-releases；新group有序包含imnull-snapshots、imnull-releases、maven-releases、maven-snapshots、maven-central。imnull-releases按本机设ALLOW，默认maven-releases仍ALLOW_ONCE；缺imnull-snapshots时只新增，服务器15→16库，Puyu3/Finger3/dell-acceptance全部保留，原50components/1347assets需保持。

原puyu-reader/puyu-publisher账号密码和原Puyu权限保留，只增标准6Maven读取及publisher对imnull2 add/edit；无delete/admin，不改其它角色。Nexus隔离网络不放开，无数据迁移/清库/业务构建，MCP仍dev-only/deploy关，原key/paths/SSH不改。example/test/docs默认值已推main/bba3542且发布机同步，Mac75项通过，Linux75项37.158秒通过；YAML仅改三个库名、密码/MCPkey/其余设置保持。[配置应用](../../completion/20261111-nexus-local-parity/configuration-applied.json)确认原50/1347和额外7库保持、DELETE调用0；[实际YAML连接后检](../../completion/20261111-nexus-local-parity/connected-postcheck.json)已通过，两身份经maven-public取现有imnull资产均200/原字节一致，9参考定义语义相等、16库和旧50/1347保持；MCP协议/401/403及dev-only/deploy关保持，无新job。[当前方案](../../completion/20261111-nexus-local-parity/README.md)、[操作说明](../../completion/20261111-nexus-local-parity/usage-manual.md)。此前Puyu专属group配置为上一阶段历史，不据此覆盖本次新映射，也不删除仍保留的Puyu仓库。

## 2026-11-11早期Puyu空仓库接入（历史映射）

已在既有Nexus新增puyu-releases（RELEASE/ALLOW_ONCE）、puyu-snapshots（SNAPSHOT/ALLOW）与puyu-public（仅前两者），以及专用reader/publisher身份。权限fixture正负测通过后已清，当前0components/0assets；原旧库/管理员/账号/EULA/密码不改，Nexus未重启，不复制Finger/imnull制品。

[发布机应用](../../completion/20261111-puyu-nexus/publisher-applied.json)和[连接后检](../../completion/20261111-puyu-nexus/connected-postcheck.json)保存本次实际验证。新group是Puyu内部制品入口，不代理全部公共依赖；项目既有MavenCentral/pluginPortal/JitPack直连保持，Nexus内部网络不放开。两新口令仅VM220受保护600来源，已接入ub600/ignored统一config.local.yaml；artifact_exec.py配置层适配器源码main/2d8f541已推送，Mac75项回归＋固定/bin/bash专项10项通过；发布机已同步同SHA并通过Linux75项回归、离线show/check和固定build.bash ls只列项目，连接后检已通过：真实私有YAML身份认证、MCP协议/匿名401/Origin403与限制保持，未提交新任务；这是配置完成，不是业务构建就绪。它仅CLI显式入口，注入原NEXUS_*环境给固定build.bash，不改build/common/Go/Java、不自动接MCP。

当前主库仍main、dev远端缺失；1.0.0等release版本不能自动发SNAPSHOT，私有gradle-conventions/公共库尚需后续供应。今天不改版本/建分支、不构建或发布业务，MCP仍dev-only/真实deploy关，旧链fenced、原MCPkey不变。[交付状态](../../completion/20261111-puyu-nexus/README.md)、[操作说明](../../completion/20261111-puyu-nexus/usage-manual.md)。

更新：2026-11-10，Asia/Shanghai。本文从唯一[Git来源总表](../git-repositories.json)的`/machines/6`派生；机器位置`machines/vm220-publish-service`，身份与资源仍以[plan.json](../../plan.json)为准。

本页维护总表派生的来源与取码计划，并单列后续获准的导航部署事实。文档编辑本身没有SSH或Git远程操作；导航最新实际状态以[统一内网HTTP交付](../../evidence/internal-http-20261110/README.md)为证，首次HTTPS回执只作历史。登记仓库不代表整仓库已clone、server Git key已分发或业务已上线。

## 本机结论

当前新增[deploy-public实际安装与预检](../../evidence/deploy-public-publisher-20261110/README.md)：源码和7套Git身份已在VM220安装，6个后端仓库main读取通过，只有受管理源码/配置与MCP，不代表业务部署解冻。当前CLI prod/main与dev/dev，MCP仅dev；[本轮上游审计](../../evidence/deploy-public-modes-20261110/branch-audit-before.json)证实全部缺dev，工作树仍main。


- 总表Git使用方式：**源码与发布器已配置、业务发布关闭**（`build-source-configured-business-disabled`）；后续独立授权的导航模块已按固定五文件release部署，见下一节。
- 当前说明：当前Puyu使用独立deploy-public，当前main/bba3542已推送并在VM220应用，Linux75测试通过（37.158秒）；2d8f541为此前Puyu初接入；旧213f/65测试及模式探针仅对应11月10日阶段；loopback MCP保持，CLI prod/main dev/dev、MCP仅dev，新预检因缺origin/dev按设计failed。旧5服务dev/main预检仅历史，六后端上游dev缺失、工作树main保持；真实发布关闭、旧链fenced、Java不启。
- 所有基础设施公开配置由`infra` → [bkcode/dell-t630](https://github.com/bkcode/dell-t630)统一管理；这不表示本机保存了该Git工作树，也不授权自动pull/执行bootstrap。

本机相关配置路径：[infra/publisher](../../infra/publisher)、[infra/java](../../infra/java)。旧执行器仍有具体UUID/角色/授权门禁，不能从这些链接批量重放。

## 已部署的导航模块：精确例外

用户新增并收窄为无需账号密码、只预览跳转的内网导航。现役仅取 `bkcode/deploy` 的 `service-directory/server.py`、`services.json`、三个Web文件，绑定当前提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`；[最新导航应用回执](../../evidence/internal-http-20261110/navigation-links-applied.json)登记每文件SHA256。ddccc2b是此前布局阶段。`63b8c08` 的首次HTTPS[source-manifest](../../evidence/service-directory-20261110/source-manifest.json)仅是历史。管理机项目位于 `/Users/yangzhaohui/work/www/finger/finger-master/projects/deploy`，发布机源码路径约定为 `/var/www/finger/finger-master/projects/deploy`；运行release独立位于 `/opt/dell/service-directory/releases/<SHA>/`，并非把整个deploy工作树直接运行或安装所有候选业务。

入口 **[http://192.168.19.30:9080/](http://192.168.19.30:9080/)** 按用户要求使用HTTP，移除顶部栏并使用全宽紧凑布局；不加载TLS或登录凭据。匿名只读，不调用原发布链、不探测URL；未来清单改项目Git后提交新SHA，再部署新release/只重启导航。无应用密码或运行state，也不读取/复制旧deploy配置、MCP jobs、Git或publisher私钥。Linux UID/GID2001仅隔离导航进程，不是应用账号。[手册与验收边界](../../evidence/service-directory-20261110/README.md)。

[源码Git状态](../../evidence/service-directory-20261110/source-git-state.json)记录：任务前本机main已比观测到的GitHub main `593069eb54a723ee0e63f85b937b9981b39ac1ec` 领先4条用户提交；本次新增自身8文件提交 `63b8c08`（父 `81148e8614ee5c49e6f9e4d1b85aebef8adfb33d`），**已本机提交、未push**，避免顺带发布原4条提交。没有amend/rebase/force。现役五文件确由git show精确提交导出，日后维护只能取已审查明确提交，不能git pull旧main覆盖。Dell配置文档独立交付不代表deploy源码已推到GitHub。

上述源码Git记录与首次[重启/浏览器/后检](../../evidence/service-directory-20261110/README.md)属于63b首次HTTPS阶段。后续仅本机提交HTTP变更 `c141506ec6a59dd7f123cabc00f099f1cf87d4e1` 和全宽布局 `ddccc2b98bbb3dfdc9de649443dc3fcdc7b4860f`，仍未push、未改写4条既有用户提交。随后新增FileBrowser链接HTTP提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`，共4条任务提交仍未push；运行release现为d56提交的精确五文件；旧TLS证书/私钥只留未启用历史。最新[统一内网HTTP记录](../../evidence/internal-http-20261110/README.md)及[14:28后检](../../evidence/internal-http-20261110/final-postcheck.json)为准，FileBrowser链接HTTP、14条/topbar0/全宽保持且原服务不变；不借旧验收扩大证明新布局或目标站点可达性。

这不证明 `bkcode/deploy` 已适配Puyu部署，更不证明五个后端已上线；Java仍停用、publisher fenced、common-lib仍只是共享库。表中 `build-source-configured-business-disabled` 区分已取源码/MCP搭建与尚未启用业务发布，导航release另按本节证据登记。

## 用户应用/构建输入仓库

| ID | 仓库 | 分支/引用语义 | 用途与边界 |
| --- | --- | --- | --- |
| `deploy` | [bkcode/deploy](https://github.com/bkcode/deploy) | main (management local checkout observed) | 仅service-directory模块精确提交已作为五文件导航release安装；原部署工具/Puyu发布适配仍候选 |
| `deploy-public` | [bkcode/deploy-public](https://github.com/bkcode/deploy-public) | main / bba3542（VM220已同步） | Puyu发布器与MCP已安装，CLI双环境、MCP仅dev，业务dev缺失/真实发布关闭 |
| `puyu-auth` | [bkcode/puyu-auth](https://github.com/bkcode/puyu-auth) | main (management local checkout observed) | 认证业务源码候选 |
| `puyu-bff-admin` | [bkcode/puyu-bff-admin](https://github.com/bkcode/puyu-bff-admin) | main (VM220 verified) | 后续登记专属key后已Git克隆，第五服务；不代表业务部署 |
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

当前取用独立`bkcode/deploy-public`＋五个Puyu服务及common-lib仓库，原`bkcode/deploy`只保留Finger/导航来源。`puyu-common-lib`是构建/发布的共享库，不能计成一个运行服务；管理机main分支观察不等于远端或220已部署。尚未证明deploy工具已经适配Puyu，不能直接套旧Finger发布命令。

现有220→240受限链仍由Dell `infra/publisher`提供，保持fenced；本次Git来源登记没有activate/rollback，也没有部署或启动Java。新Git Deploy Key与原220专用发布SSH key是两类身份，不能互相替换或将旧私钥复制出去。

## 仓库认证元数据（不是服务器已安装证明）

用户报告GitHub的8个Deploy Key已配置；这些引用记录管理Mac `~/.ssh/deploy-keys/bkcode/`已准备的仓库身份命名。本轮仅Penpot有独立读取验证，其他7个未逐一重测；不含私钥、公钥正文或口令。只读是配置目标，不能因SSH身份名称就推断GitHub已完成注册/全部授权，更未通过push探测写权限。服务器安装/分发未由本任务执行或核验。

| 仓库ID | key basename | SSH alias | 读取验证范围 |
| --- | --- | --- | --- |
| `deploy-public` | `deploy_ed25519`（Mac）/`deploy-public_ed25519`（VM220） | `github-bkcode-deploy-public`（VM220） | 用户已将该GitHub DeployKey改绑新repo；VM220 main读取已实测，服务器pushURL禁用 |
| `puyu-auth` | `puyu-auth_ed25519` | `github-bkcode-puyu-auth` | GitHub registration/read access not reverified in this documentation task |
| `puyu-bff-admin` | `puyu-bff-admin_ed25519` | `github-bkcode-puyu-bff-admin` | 新增注册后VM220 main读验证通过，私钥仅私有目录 |
| `puyu-bff-web` | `puyu-bff-web_ed25519` | `github-bkcode-puyu-bff-web` | GitHub registration/read access not reverified in this documentation task |
| `puyu-common-lib` | `puyu-common-lib_ed25519` | `github-bkcode-puyu-common-lib` | GitHub registration/read access not reverified in this documentation task |
| `puyu-gateway` | `puyu-gateway_ed25519` | `github-bkcode-puyu-gateway` | GitHub registration/read access not reverified in this documentation task |
| `puyu-service-core` | `puyu-service-core_ed25519` | `github-bkcode-puyu-service-core` | GitHub registration/read access not reverified in this documentation task |

GitHub只读Deploy Key应不勾Allow write access；用户报告配置完成不等于本轮已独立重测所有key。除Penpot的管理Mac读取实证外，不将其他仓库写成本轮已实际read验证；服务器key未由本任务落地。

## 后续变更入口

新增/修改仓库先由主AI更新[唯一总表](../git-repositories.json)，核对应角色的读权限、不可变版本、构建/发布适配与授权，再同步本页和[机器合同](config.json)的`git_repository_mapping`。源码读取、build、部署、数据库迁移与启动是不同阶段，不因本页列出URL而自动授权。

本文无真实凭据或key正文；公开来源索引只保存元数据，现有秘密与归档边界保持。

## 当前Git身份和操作边界

7套Git身份仅用于deploy-public及六个Puyu后端/公共库的源码读取，ub目录700/文件600，GitHub443复用既有可信host key。每个仓库为独立身份；原`deploy_ed25519`现绑定deploy-public，不能再当作旧Finger deploy凭据。服务器SSH公共配置引用专属alias文件，repo core.sshCommand固定all-repos.conf，pushURL为no-push://disabled。未通过写入探测GitHub权限；Allow write access按用户配置应关闭。原220发布SSH私钥是另一身份，未读/未导出。

配置端口、MCPkey、路径/目标均在ignored的统一YAML；关键值不进本文。实际目标deployer@19.45仅预览，旧forced-command程序仍未适配Puyu且fenced。源码拉取和只读校验不授予直接systemd部署权限。详见[发布机操作说明](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)。

## 当前分支就绪边界

CLI dev取dev、prod取main，MCP仅dev。源码工具本身仍main，不随业务环境切分支。本轮6仓库上游main存在/dev缺失、当前工作树main；source_ready只表示目录身份，不等于dev就绪。target_branch_available只查询本地origin引用。缺配置分支的预检在构建/SSH前拒绝，显式sync才fetch；没有dev时不代建、不push、不回退main。prod身份未配置、真实发布关闭。源码更新及实例读回以[本轮模式记录](../../evidence/deploy-public-modes-20261110/README.md)为准。

## Nexus同机归属（2026-11-10）

Nexus已由2206CPU8GiB/primary30＋alias31承接，原镜像/数据/账号/EULA保持，独立221退役。公开配置来源新增infra/nexus；上游sonatype/nexus-public仅Core源码参考，不从该仓库重建/升级现役CE。原Nexus100GiB卷与build100GiB卷独立，制品数据不是Git仓库。

导航本次使用精确公开清单release nfs-nexus-20261110-12f2461e4766，共13入口，移除FileBrowser并改Nexus描述，HTTP/UI保持。原Git源码两文件修改尚未提交推送，旧d56/14入口只是上一阶段；不冒称整份原deploy已发布。部署工具/MCP/原发布私钥与fence保持。[本次回执](../../completion/20261110-nexus-merge/README.md)。
