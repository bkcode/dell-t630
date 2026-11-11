# 每台服务器的Git来源

更新：2026-11-10，Asia/Shanghai。唯一机器可读主表[git-repositories.json](git-repositories.json)覆盖16个现役目录，逐机文档/config指针与当前索引一致。Nexus并入220后，221只保留[历史归档](../archive/machines-vm221-artifact-service-20261110/README.md)，不再是独立现役Git条目。

配置仓库统一[bkcode/dell-t630](https://github.com/bkcode/dell-t630)。应用源码、官方上游参考、已部署与候选分开记录；源码归属不授权Java启动或自动替换镜像。

| 机器 | 应用/构建源码 | 配置目录 | 当前用法 |
| --- | --- | --- | --- |
| [pve](pve/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/audit`, `infra/backup/prod-db`, `infra/ops` | configuration-only |
| [cf-tunnel](ct100-cf-tunnel/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/services-core` | configuration-only |
| [network-gateway](vm190-network-gateway/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/gateway`, `network19/audit` | configuration-only |
| [data-prod-db](vm200-data-prod-db/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/data`, `infra/backup/prod-db` | configuration-only |
| [data-prod-infra](vm201-data-prod-infra/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/data` | configuration-only |
| [data-test](vm210-data-test/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/data` | configuration-only |
| [publish-service](vm220-publish-service/GIT-REPOSITORIES.md) | `bkcode/deploy`, `bkcode/deploy-public`, `bkcode/puyu-auth`, `bkcode/puyu-bff-admin`, `bkcode/puyu-bff-web`, `bkcode/puyu-common-lib`, `bkcode/puyu-gateway`, `bkcode/puyu-service-core` | `infra/publisher`, `infra/java`, `infra/deploy-public`, `infra/nexus` | build-source-configured-business-disabled |
| [java-prod-01](vm230-java-prod-01/GIT-REPOSITORIES.md) | `bkcode/puyu-auth`, `bkcode/puyu-bff-web`, `bkcode/puyu-gateway`, `bkcode/puyu-service-core` | `infra/java/runtime`, `network19/java-template` | artifact-consumer-runtime-only |
| [java-test-01](vm240-java-test-01/GIT-REPOSITORIES.md) | `bkcode/puyu-auth`, `bkcode/puyu-bff-web`, `bkcode/puyu-gateway`, `bkcode/puyu-service-core` | `infra/java/runtime`, `network19/java-template` | artifact-consumer-runtime-only |
| [penpot-service](vm250-penpot-service/GIT-REPOSITORIES.md) | `bkcode/penpot` | `infra/penpot`, `infra/penpot/runtime/health-supervision` | custom-code-imported |
| [nas-media](vm260-nas-media/GIT-REPOSITORIES.md) | `bkcode/jellyfin` | `infra/nas` | official-runtime-user-fork-planned |
| [ops-service](vm270-ops-service/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/ops` | official-monitoring-components |
| [resource-service](vm280-resource-service/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/resources` | native-os-packages |
| [tpl-docker-base](tpl9001-docker-base/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra`, `cleanup/fish` | sealed-template-no-business-source |
| [tpl-linux-base](tpl9010-linux-base/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra`, `cleanup/fish` | sealed-template-no-business-source |
| [tpl-java-acceptance](tpl9011-java-acceptance/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/java-template`, `infra/java/runtime`, `cleanup/fish` | sealed-template-no-business-source |

## 发布机、Nexus与running

220当前从独立bkcode/deploy-public main2d8f541取工具，Linux75测试通过，Puyu空制品仓库与私有YAML/CLI配置适配已验证；MCP仍仅dev且真实deploy关闭。六backend工作树main/clean保持，未在本轮fetch或创建分支。私有插件/公共库、SNAPSHOT版本与业务分支仍待后续准备。此前11月10日main213f/65测试及缺dev预检是历史，见[Puyu空仓库配置验收](../completion/20261111-puyu-nexus/README.md)。

220同时承接Nexus原固定官方镜像/数据/身份，upstream sonatype/nexus-public仅Core源码参考，不是本次从Git重建或升级CE。NexusURL31:8081不变，管理primary30，原Nexus卷与build卷独立。230/240运行基础以后仅收经批准制品，不直接拉源或存DeployKey；common-lib是共享依赖，不独立启动。

导航来自原bkcode/deploy/service-directory公开模块；当前只替换清单为13入口，移除FileBrowser并改Nexus归属，UI/HTTP不变。原源码工作树两文件修改由专属任务管理，尚未提交推送，本次不捎带旧main用户提交或声称导航源码已上GitHub。[清单回执](../completion/20261110-nexus-merge/navigation-updated.json)。

## 其他源码与历史

Penpot现役bkcode/penpot main8a9b961，公开HTTPS取固定提交、11healthy、原登录改造与设计保持；初次9aed/ff/无origin仅旧阶段，不再等待用户push。NAS仍官方Jellyfin，bkcode/jellyfin是服务端候选，不代表电视客户端或服务端fork已上线。资源280当前仅原生NFS系统包/infra/resources，FileBrowser upstream和binary只留退休历史，不是现役应用。

DeployKey以仓库精确隔离，服务器权限600/目录700，pushURLdisabled；不实际push探测只读权限。clone成功证明读取，不等于服务器身份具有写权限。密钥正文、PAT、真实凭据、私有YAML与业务数据不进Git。原发布私钥只220，不wholebackup220，不重生成MCPkey。

## 更新和验证

维护先核仓库/分支/已审查提交、clean工作树和无活动任务；只快进工具已审查版本，保留私有配置和挂载守卫，不重跑bootstrap或整体reset/clean。应用数据/SQL和Git回滚不是同一件事。[发布工具手册](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)、[Nexus手册](../completion/20261110-nexus-merge/usage-manual.md)。

```sh
python3 scripts/validate_git_repositories.py
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
```

以上仅离线合同验证，不代替服务器原生数据/身份/健康/恢复验收。文件来源SHA需随本次公开变更刷新，不能降低validator门槛。


2026-11-11最新[Nexus本机配置对齐](../completion/20261111-nexus-local-parity/README.md)已按用户安全选择完成：共有9库定义对齐，额外7保留，服务器16库；发布机mainbba3542/Linux75通过，读取maven-public、dev/prod发布imnull-*，原密码/MCPkey保持。原50组件/1347资产保留、DELETE0、不迁数据不启业务，代理cache miss未签验。先前独立Puyu映射仅旧阶段，不覆盖本次实际映射。
