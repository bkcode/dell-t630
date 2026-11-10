# 按机器组织的配置与文档

更新：2026-11-10，Asia/Shanghai。此处为PVE宿主、13个来宾与3份模板建立独立目录，共17份（新增280资源角色）。iDRAC属于PVE物理机管理面，记录在pve目录；已删除的旧VM/QA不重新建成现役对象。

**2026-11-09继续完成基础搭建与仅正式数据库/Nacos逻辑备份，测试配置迁移及仅Puyu两库到210的DB迁移按用户最新授权完成；正式环境不动。** 新增资源服务前的当日fresh审计为12running/3tpl、15UP，forward guard跨14:24自然重启保持；正式DB首轮3301B/timer已通过、旧whole-VM计划disabled，最终状态统一见[当日交付记录](../completion/20261109-prod-db-scope/README.md)。每机JSON是合同/索引，不是秘密恢复包或实时配置导出；每机状态按各自证据与范围解释。

## 每台机器的Git来源

唯一主表：[git-repositories.json](git-repositories.json)。17个目录均有`GIT-REPOSITORIES.md`，由总表派生；每机`config.json.git_repository_mapping`仅指向总表/本机条目和仓库ID，不是clone/部署或密钥分发证明。代码/配置主仓库统一`bkcode/dell-t630`，官方包/镜像的上游参考与用户计划源码分开。

| 机器 | 唯一逐机入口 | Git取用定位 |
| --- | --- | --- |
| PVE pve | [GIT-REPOSITORIES.md](pve/GIT-REPOSITORIES.md) | `configuration-only` |
| 100 cf-tunnel | [GIT-REPOSITORIES.md](ct100-cf-tunnel/GIT-REPOSITORIES.md) | `configuration-only` |
| 190 network-gateway | [GIT-REPOSITORIES.md](vm190-network-gateway/GIT-REPOSITORIES.md) | `configuration-only` |
| 200 data-prod-db | [GIT-REPOSITORIES.md](vm200-data-prod-db/GIT-REPOSITORIES.md) | `configuration-only` |
| 201 data-prod-infra | [GIT-REPOSITORIES.md](vm201-data-prod-infra/GIT-REPOSITORIES.md) | `configuration-only` |
| 210 data-test | [GIT-REPOSITORIES.md](vm210-data-test/GIT-REPOSITORIES.md) | `configuration-only` |
| 220 publish-service | [GIT-REPOSITORIES.md](vm220-publish-service/GIT-REPOSITORIES.md) | `build-source-planned` |
| 221 artifact-service | [GIT-REPOSITORIES.md](vm221-artifact-service/GIT-REPOSITORIES.md) | `official-artifact-service` |
| 230 java-prod-01 | [GIT-REPOSITORIES.md](vm230-java-prod-01/GIT-REPOSITORIES.md) | `artifact-consumer-runtime-only` |
| 240 java-test-01 | [GIT-REPOSITORIES.md](vm240-java-test-01/GIT-REPOSITORIES.md) | `artifact-consumer-runtime-only` |
| 250 penpot-service | [GIT-REPOSITORIES.md](vm250-penpot-service/GIT-REPOSITORIES.md) | `custom-code-imported` |
| 260 nas-media | [GIT-REPOSITORIES.md](vm260-nas-media/GIT-REPOSITORIES.md) | `official-runtime-user-fork-planned` |
| 270 ops-service | [GIT-REPOSITORIES.md](vm270-ops-service/GIT-REPOSITORIES.md) | `official-monitoring-components` |
| 280 resource-service | [GIT-REPOSITORIES.md](vm280-resource-service/GIT-REPOSITORIES.md) | `native-official-binary` |
| 9001 tpl-docker-base | [GIT-REPOSITORIES.md](tpl9001-docker-base/GIT-REPOSITORIES.md) | `sealed-template-no-business-source` |
| 9010 tpl-linux-base | [GIT-REPOSITORIES.md](tpl9010-linux-base/GIT-REPOSITORIES.md) | `sealed-template-no-business-source` |
| 9011 tpl-java-acceptance | [GIT-REPOSITORIES.md](tpl9011-java-acceptance/GIT-REPOSITORIES.md) | `sealed-template-no-business-source` |

220计划使用`bkcode/deploy`＋五个Puyu后端仓库，shared common-lib仅库；现役受限发布链仍Dell/fenced。230/240只接收经审构建产物，不直接git拉、不放Deploy Key，Java业务不启。250的管理Mac读取/临时clone与服务器历史ff版本分开记录；260的用户Jellyfin服务端fork待迁，不是OMV或当前镜像。280只用官方FileBrowser固定binary，模板不带业务库/Git私钥。

用户报告8个GitHub Deploy Key已配置，管理Mac身份位于`~/.ssh/deploy-keys/bkcode/`；本轮只独立验证Penpot读权限/临时工作树，其余7个未逐一重测，未在服务器安装/分发这些key。文档不含公钥/私钥正文、PAT或密码；不通过push探写权限。仓库URL/来源登记不授权重跑bootstrap、改数据或启业务。

## 机器入口

| 类型 | 目录 | 地址 / 状态 |
| --- | --- | --- |
| PVE宿主 | [host · pve](pve/README.md) | 192.168.21.22 |
| LXC | [100 · cf-tunnel](ct100-cf-tunnel/README.md) | 192.168.19.5 |
| VM | [190 · network-gateway](vm190-network-gateway/README.md) | 192.168.19.1 |
| VM | [200 · data-prod-db](vm200-data-prod-db/README.md) | 192.168.19.10 |
| VM | [201 · data-prod-infra](vm201-data-prod-infra/README.md) | 192.168.19.11 |
| VM | [210 · data-test](vm210-data-test/README.md) | 192.168.19.20 |
| VM | [220 · publish-service](vm220-publish-service/README.md) | 192.168.19.30 |
| VM | [221 · artifact-service](vm221-artifact-service/README.md) | 192.168.19.31；本轮保持独立，不迁移/退役 |
| VM | [230 · java-prod-01](vm230-java-prod-01/README.md) | 192.168.19.40 |
| VM | [240 · java-test-01](vm240-java-test-01/README.md) | 192.168.19.45 |
| VM | [250 · penpot-service](vm250-penpot-service/README.md) | 192.168.19.50 |
| VM | [260 · nas-media](vm260-nas-media/README.md) | 192.168.19.60 |
| VM | [270 · ops-service](vm270-ops-service/README.md) | 192.168.19.70 |
| VM | [280 · resource-service](vm280-resource-service/README.md) | 192.168.19.80；NFS双客户端与280重启持久性已验 |
| 模板 | [9001 · tpl-docker-base](tpl9001-docker-base/README.md) | 无服务IP |
| 模板 | [9010 · tpl-linux-base](tpl9010-linux-base/README.md) | 无服务IP |
| 模板 | [9011 · tpl-java-acceptance](tpl9011-java-acceptance/README.md) | 无服务IP |

## 统一资源服务（新增VM280）

用户选择正式/测试共用VM280 `resource-service`（19.80）的同一目录。独立100GiB ext4盘挂`/srv/resources`，系统盘保32GiB；两running 230/240目标挂载均为`/mnt/resources`，240原`/mnt/dell-artifacts`不动。NFSv4.1-only/TCP2049/fsid0，只有19.40/19.45获export与bridge/专属输入许可；root_squash、sync、server根2770/defaultACL、共享resources附属组2980。finger原UID999/GID989保留。

[server启动](../completion/20261109-resources/server-installed.json)与[实际盘UUID](../completion/20261109-resources/storage-initialized.json)已留证；两客户端真NFS挂载/guard、非root跨机创建/读写/删除、root_squash与240缺挂载根盘写入负测均已通过；仅VM280受控重启约30秒，fsync canary持久、两客户端挂载恢复，未重启两台running。**NFS-only，不启HTTP/Java、不迁文件、不扩自动备份。** 资源角色使预算变为13来宾（12VM＋CF LXC）、3模板、45vCPU/87GiB；保守125GiB预算余38GiB。[00:20最终只读后检](../completion/20261109-resources/final-postcheck.json)确认13来宾运行、3模板停止、16/16 targets UP、资源5项服务指标UP与PVE全forward0。详见[280机器目录](vm280-resource-service/README.md)与[资源使用手册](../completion/20261109-resources/usage-manual.md)。

模板仅能将来预装客户端与disabled挂载候选，clone按真实IP/组/exports/bridge登记后显式激活；**本次没有修改三模板**。

[独立native验收](../completion/20261109-resources/native-acceptance.json)与[仅280重启](../completion/20261109-resources/reboot-exercise.json)覆盖本次专属fixture，不含真实业务或文件恢复。findmnt允许systemd-1 autofs加唯一真实nfs4的合法stack，可用`-t nfs4`辨识；单独autofs仍不算共享已挂载。客户端文件创建明确用umask0002；首轮失败及清理记录保留，随后仅按已批准UMask重跑fixture，未修改服务来追过。新增280 fish4.0.2、root/ub默认Bash已后检；当前10台guest＋3模板具备fish基线。

应用尚未接入：Finger的`file.upload.path=/mnt/resources`仅建议，未改实际配置/Nacos/profile；HTTP domain/公开图片URL未搭。Puyu现有images在MySQL内通过权限接口下载，NFS不会自动迁出，也未随部署改Java或应用连接。


## 测试配置入口：源两域原样36项

用户最新授权测试Nacos配置迁移，覆盖先前仅空基础限制。VM210 `19.20:8848`现为finger-cloud-dev（`08e7191f-3ccd-411a-be00-56798d237533`）32项＋finger-trascan（`7bfe03c6-0590-4ff0-8def-e07015016b54`）4项；旧finger-test（`10719261-2641-590a-b821-c8484ca955ac`）、finger-test-empty（`23836f2e-9553-5948-84cd-431b2f241bd6`）和public均0。ID/name/group/body原样保留、未适配端点，不代表应用已可运行。见[applied](../completion/20261109-nacos-config-import/applied.json)、[verified](../completion/20261109-nacos-config-import/verified.json)及[210细节](vm210-data-test/README.md)。

`finger_test`原应用权限仍只old＋empty，不授权两导入域；以后业务接入另配权限，当前admin可管理；后续仅Puyu两库数据迁移另获授权，仍不Java/不改profile。原7项guest私有备份保留，2＋5删除分两run留证，不公开body/hash/密码。早前[空域创建](../completion/20261109-test-env/empty-namespace-created.json)保持其当时历史含义，不再当当前旧域仍7项的证明。


## 测试MySQL新增Puyu库

VM210 `19.20:3306`按原名新增迁入`puyu_auth_local`4表/178行、`puyu_erp_local`47表/1113行，共51表/1291行，均指22:41导出快照；源应用DML可继续、源库保留且不持续同步。写前无同名检查和[原生apply](../completion/20261109-puyu-db-migration/applied.json)/[verify](../completion/20261109-puyu-db-migration/verified.json)已通过。未迁MySQL系统账号、未改目标原密码/cnf/服务、未迁Puyu Nacos配置/应用连接、未启Java，临时账号/client文件已清；[独立只读后检](../completion/20261109-puyu-db-migration/postcheck.json)已逐表核51个COUNT(*)与导出快照匹配，原四容器、Nacos36配置和既有Finger/Nacos表保持。

当前LAN21/24已受信访问19/24和网关本机，[23:00正测](../network19/lan-trusted-20261109/LAN-positive-tests.json)含测试3306/SSH/ping及正式Nacos8848；早前Nacos-only阻断仅历史。SSH仍ub/key-only，Docker需sudo，MySQL原用户Host/密码仍限制。细节见[210说明](vm210-data-test/README.md)；TLS未新增服务端配置。

## 每个目录的文件

| 文件 | 用途 |
| --- | --- |
| `README.md` | 职责、网络/资源/存储、依赖、维护方式及证据限制 |
| `config.json` | 非秘密机器配置合同，资源与身份对应plan；含最后验收时点、当前基础恢复范围与证据 |
| `config-sources.json` | 原始配置/工具/证据索引；path相对仓库根，按current-contract、historical-evidence、pending-candidate区分 |
| `configs/`（按需） | 可确认来源的非秘密快照；须带source路径与SHA，不能不加判断直接应用 |

来源SHA只锁定本地仓库文件版本，不证明它与来宾现役文件相同；修改源文件后先审核差异，再同步受影响索引的SHA，不能盲改hash凑通过。

`config.json`里的机器身份与资源由[plan.json](../plan.json)约束。修改这些配置时同时维护源合同并运行校验，避免产生多份互相矛盾的现役说明。原infra/network19/cleanup文件继续保留为技术源或历史证据，没有通过复制新目录就改变其适用阶段。

## 发布与Nexus的两个视图

目标中只保留220 `publish-service`承担发布与Nexus，主IP30+服务alias31、6CPU8GiB；但实际移交尚未执行。因此220目录记录当前4CPU4GiB/30与单独目标，221目录仍记录当前来源身份和待退役条件。加入资源280后的合并目标为12实例，不能为了凑目标而提前抹去221的配置，也不能同时把31登记为两台现役VM所有。

合并目标合同见[17合并架构](../17-publish-artifact-consolidation.md)。未来验收后更新现役清单与目录状态，保留必要源/回退记录；不能仅改目录名代替迁移。

## 现行备份范围与机器身份

自动备份仅源VM200正式MySQL/Nacos外部元数据库，当前唯一`nacos_prod`、12表、正式业务schema未创建。VM201 Nacos配置通过该库覆盖；201自身文件/Redis/Rabbit与所有其他机器数据均不自动备份。新增未列白名单数据库直接失败告警、需显式更新。

[首轮与timer](../completion/20261109-prod-db-scope/first-success-and-timer-enabled.json)3301B已CRC/传输SHA/锁释放/暂存清理通过，03:30 timer enabled（next2026-11-10），GFS3/7/4，PVE目的地`/mnt/pve/store/dell-artifacts/prod-db-backups` root700/600。[新规则](../completion/20261109-prod-db-scope/alerts-installed.json)已使用db-only指标热载，原Prom identity/三名/接收对象保持，无testsend；最终状态见[新中央入口](../completion/20261109-prod-db-scope/README.md)。

旧11来宾全机jobdisabled、旧规则组退役；19,747,582,801B旧全机档、21回退档和模板回退资料保留，不自动删。历史CF档仅PVE，发布私钥仅220；不把归档放机器目录/Git。当前是应用逻辑备份、非VM快照，仅[该3301B Nacos小档已在VM210临时隔离恢复](../completion/20261109-prod-db-restore/README.md)，完整业务恢复/RPO/RTO/异机DR未签，不迁移/合并/启Java、无Mac探针；OW规则只本地不触上传。

## 秘密、操作与检查

不保存.env实际值、密码、token、webhook、SSH私钥、数据库或VMA/磁盘/备份归档。CF凭据备份仅PVE；发布私钥仅220，不能为补充本目录导出220整机。来源索引不应指向private，秘密保管位置只能在受控运维指引里解释。

目录中出现命令和配置不授权执行；先读[当前交接](../11-live-handoff.md)和[人工手册](../19-manual-operations.md)。Java业务不部署、publisher继续fenced、Mac外部探针不需要，移出现行及后续工作。

在仓库根目录执行：

```sh
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
python3 scripts/check_git_safety.py
```

校验只检查本地身份、资源、来源路径与快照SHA，不判断服务器实时健康，不执行SSH、Docker或部署。

本次目录整理的[离线验收记录](validation.json)包含独立副本检查和配置漂移负例；不证明当前服务器在线。
