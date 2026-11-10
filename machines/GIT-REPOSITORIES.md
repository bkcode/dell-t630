# 每台服务器的Git来源

更新：2026-11-10，Asia/Shanghai。机器可读唯一映射为[git-repositories.json](git-repositories.json)，17份逐机文档从此表解释。所有机器的公开配置来源统一为[bkcode/dell-t630](https://github.com/bkcode/dell-t630)，不代表每台机器都需要clone或自动运行该仓库。

**当前已部署、未来计划与上游参考分别登记。** 本轮只做文档和只读取码验证，未把代码、密钥或业务应用安装到任何服务器。

| 机器 | 应用/构建源码 | 配置目录 | 当前用法 |
| --- | --- | --- | --- |
| [pve](pve/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/audit`, `infra/backup/prod-db`, `infra/ops` | configuration-only |
| [cf-tunnel](ct100-cf-tunnel/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/services-core` | configuration-only |
| [network-gateway](vm190-network-gateway/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/gateway`, `network19/audit` | configuration-only |
| [data-prod-db](vm200-data-prod-db/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/data`, `infra/backup/prod-db` | configuration-only |
| [data-prod-infra](vm201-data-prod-infra/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/data` | configuration-only |
| [data-test](vm210-data-test/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/data` | configuration-only |
| [publish-service](vm220-publish-service/GIT-REPOSITORIES.md) | [bkcode/deploy](https://github.com/bkcode/deploy), [bkcode/puyu-auth](https://github.com/bkcode/puyu-auth), [bkcode/puyu-bff-web](https://github.com/bkcode/puyu-bff-web), [bkcode/puyu-common-lib](https://github.com/bkcode/puyu-common-lib), [bkcode/puyu-gateway](https://github.com/bkcode/puyu-gateway), [bkcode/puyu-service-core](https://github.com/bkcode/puyu-service-core) | `infra/publisher`, `infra/java` | build-source-planned |
| [artifact-service](vm221-artifact-service/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/nexus` | official-artifact-service |
| [java-prod-01](vm230-java-prod-01/GIT-REPOSITORIES.md) | [bkcode/puyu-auth](https://github.com/bkcode/puyu-auth), [bkcode/puyu-bff-web](https://github.com/bkcode/puyu-bff-web), [bkcode/puyu-gateway](https://github.com/bkcode/puyu-gateway), [bkcode/puyu-service-core](https://github.com/bkcode/puyu-service-core) | `infra/java/runtime`, `network19/java-template` | artifact-consumer-runtime-only |
| [java-test-01](vm240-java-test-01/GIT-REPOSITORIES.md) | [bkcode/puyu-auth](https://github.com/bkcode/puyu-auth), [bkcode/puyu-bff-web](https://github.com/bkcode/puyu-bff-web), [bkcode/puyu-gateway](https://github.com/bkcode/puyu-gateway), [bkcode/puyu-service-core](https://github.com/bkcode/puyu-service-core) | `infra/java/runtime`, `network19/java-template` | artifact-consumer-runtime-only |
| [penpot-service](vm250-penpot-service/GIT-REPOSITORIES.md) | [bkcode/penpot](https://github.com/bkcode/penpot) | `infra/penpot`, `infra/penpot/runtime/health-supervision` | custom-code-imported |
| [nas-media](vm260-nas-media/GIT-REPOSITORIES.md) | [bkcode/jellyfin](https://github.com/bkcode/jellyfin) | `infra/nas` | official-runtime-user-fork-planned |
| [ops-service](vm270-ops-service/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/ops` | official-monitoring-components |
| [resource-service](vm280-resource-service/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra/resources`, `infra/resources/filebrowser` | native-official-binary |
| [tpl-docker-base](tpl9001-docker-base/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra`, `cleanup/fish` | sealed-template-no-business-source |
| [tpl-linux-base](tpl9010-linux-base/GIT-REPOSITORIES.md) | 无独立用户业务库 | `infra`, `cleanup/fish` | sealed-template-no-business-source |
| [tpl-java-acceptance](tpl9011-java-acceptance/GIT-REPOSITORIES.md) | 无独立用户业务库 | `network19/java-template`, `infra/java/runtime`, `cleanup/fish` | sealed-template-no-business-source |

## 发布机与running分工

VM220计划读取`bkcode/deploy`和5个Puyu JVM后端，其中common-lib仅构建库。`/var/www/finger/finger-master/projects/deploy`是用户给出的管理机工作树引用，已核origin为bkcode/deploy；不是证明220已有同路径。新部署工具是否支持当前Puyu/受限发布合同尚未验证，不替换现有Dell publisher或解除fence。

VM230/240当前仅运行基础，后续按批准收取构建制品，配置与秘密仍分别管理，不要求两机直接git pull或保存GitHub Deploy Keys。业务部署、运行分支和上线顺序后续单独确认，本表不是Java上线授权。

## 本轮Penpot验证

[管理Mac只读验证](../evidence/git-repositories-20261110/penpot-deploy-key-verification.json)：重命名后的penpot_ed25519专属key返回bkcode/penpot身份、main临时浅clone成功且目录已清。远端main实际9aedbb011cd803eb615225ca21f7f47cb8c2fa09，本地和[VM250现役](../evidence/git-repositories-20261110/penpot-runtime-readonly.json)为ff1783e7865af7aae571c985f03e057631b7af63，仍缺两条现役改造；不从远端旧版覆盖。服务器source目前无origin；本轮没有复制私钥/开启agent forwarding/配置服务器GitHub认证或更新程序。

## Jellyfin与NAS

`bkcode/jellyfin`经GitHub公开API核为`jellyfin/jellyfin`服务端fork，默认分支观察为master；只是候选，不是本轮选定部署分支。VM260当前仍官方Jellyfin镜像与OMV/Samba；OMV来源另列上游，电视端改造需要对应客户端仓库。不要把新建Jellyfin key或本表记成NAS已替换自定义程序。

## Deploy Keys与更新流程

管理Mac的8仓库专用密钥在`~/.ssh/deploy-keys/bkcode/`，私钥600、目录700；独立`ssh_config`按alias精确选择单key，公钥添加清单`PUBLIC_KEYS.md`只留该受控目录。每份机文档只记需要的文件名/alias，不含任何密钥正文。用户表示GitHub已配置完成；本期只实际验证Penpot读取，其余key与服务器安装状态不由此推定。只读属性按仓库Deploy keys设置，不以成功clone证明禁止push，更不以实际push测试。

1. 先核对应仓库、目标分支、选定commit包含所需本地改造。
2. 发布机/构建机只读取码，锁定提交；应用不同组件和AMD64依赖按各自合同构建。
3. 运行机收构建产物，保秘密/配置/数据与Git分离。
4. 明确更新窗口后才切换，验登录/原数据/服务/监控，回退程序不等于回退数据库。

不整体git pull/reset/clean覆盖现役，不重跑初始化器/格式化器，不把业务数据、用户上传、Penpot数据库/素材、Nexus制品库或NAS媒体放入源码仓库。模板不含业务源码、Deploy Key/PAT或客户数据。

## 验证

```sh
python3 scripts/validate_git_repositories.py
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
```

仓库URL的上游条目主要从本地现有组件合同/用户指定来源整理，属于源码参考而非本轮全部联网验证；许可/发行包差异以对应项目实际版本为准。独立审查见[review](../evidence/git-repositories-20261110/review.md)。

## 发布机导航模块已部署

220新增服务导航是后续用户明确授权的例外，仅使用bkcode/deploy的service-directory公开模块，当前运行本地提交63b8c08；不是原部署工具/Puyu业务已上线。源码本地main另有4条既有未推送提交，未代为发布整个分支。见[本期导航交付](../evidence/service-directory-20261110/README.md)，其他仓库/机器部署计划保持。

导航后续按用户要求切HTTP并采用紧凑全宽无顶栏，当前本地源码`ddccc2b`；原`63b8c08`为首次HTTPS历史，见[当前导航](../evidence/service-directory-http-20261110/README.md)。未代推原4条用户提交。

内部应用最终按用户要求用HTTP；导航source本地d56cae5同步FileBrowser链接，FileBrowserbinary不变，仅HTTP运行配置更新。原PVE/iDRAC内置HTTPS保留。见[内部HTTP交付](../evidence/internal-http-20261110/README.md)。
