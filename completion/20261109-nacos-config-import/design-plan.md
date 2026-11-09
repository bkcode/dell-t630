# 测试Nacos配置原样迁移：已选来源与实施门禁

更新：2026-11-09（Asia/Shanghai）。**仅本地设计**：本任务没有连接用户源/目标Nacos、PVE或来宾，没有读取配置正文/.env/秘密/数据库行，没有清空或导入。遵循`f-nacos-config`技能；官方API事实按2.4.3源码核对，不套3.x接口。

用户最新允许测试Nacos配置迁移，取代之前“只搭空服务”的方向。**来源已选，不再等待选择；配置正文、namespace ID/name、group/dataId及配置元数据原样保留，不适配端点或profile。** 仍不启动Java、不迁移业务数据库、不动正式环境。

## 1. 冻结的范围与身份映射

| 源namespace | 源ID＝目标ID | 选择时配置数 |
| --- | --- | ---: |
| finger-cloud-dev | 08e7191f-3ccd-411a-be00-56798d237533 | 32 |
| finger-trascan | 7bfe03c6-0590-4ff0-8def-e07015016b54 | 4 |
| 合计 | 两域分别保留原ID/name，group/dataId不改 | 36 |

- 唯一写目标：VM210 `data-test`，`http://192.168.19.20:8848/nacos`。拒绝正式19.11、正式MySQL19.10及其它目标；禁止redirect改变主机/路径。
- 删除范围是目标**全部namespace内的配置items**，当前盘点7项；删除前必须fresh完整盘点默认public及所有实际域/全部group，而不是只清DELL_TEST或某一个namespace。
- 保留目标已有namespace、账号、role、permissions、注册服务和业务DB，不SQL/TRUNCATE、不删域、不重置密码、不重启或启动Java。旧finger-test与finger-test-empty保留，即使其配置项被清空。
- 两个源ID在目标不存在时，仅创建同ID/name的namespace元数据；存在时核ID/name一致。ID碰撞或同ID不同名先停，不擅自改已有域名。目标最终namespace集合为原集合加缺失的这两域，不覆盖其它域。
- **不新增应用角色权限。** 现有admin管理导入；旧role关系原样保留。未来业务访问这两个源ID另行授权，应用账号当前403不以自动grant修复。
- 本机目录/Compose不是配置导出的权威来源。源owner从所选真实Nacos实例读取；源端只读、不改源服务或内容。public空ID与显示名public按所用API显式规范化，不以缺省tenant误写。

## 2. 精确清单、原样字段与前后指纹

| 集合 | 内容 |
| --- | --- |
| `S_selected` | 上述两源域全部group/dataId，必须32＋4＝36；分页去重/total相符 |
| `S_before` | 每键的`source_md5_before`、修改版本/时点、body bytes/SHA256与完整可回写元数据，仅私有保存 |
| `T_before_all` | 目标全部配置键、原body/元数据、MD5/版本，当前预期7；与namespace/账号权限/服务/DB结构基线分开 |
| `M` | 两源域ID/name → 目标同ID/name；group、dataId、body不变，不重新分组 |
| `D_expected` | 原样映射后的36个目标键与全部预期字段；不做test端点候选或正文改写 |
| `Delete_set` | 只等于冻结的`T_before_all`配置键；执行中不扩张新出现的未知配置 |

主键为`(instance, namespaceId, group, dataId)`，不跨实例复用数值row ID。逐项必须保留并比较：**content原始语义/字节、type、appName、configTags（发布参数config_tags）、encryptedDataKey**；desc/use/effect/schema等当前API提供的其它可回写字段也记录。空/null与未采集不同，不用文件后缀猜type，不把缺字段默认为text或空串。

`configTags`标签元数据与带tag的配置变体不同；beta/tag/加密配置若存在，先证明快照、删除和回写协议覆盖，不能忽略后仍称全部。分页、key集合和两次稳定枚举都要验证；source任一新增/消失/变更导致36清单不稳定则停写前重新冻结，不导入一个碰巧凑够36的子集。

body、MD5/SHA、encryptedDataKey和原始API响应仅进受保护文件，普通回执只输出计数/比较布尔。MD5用于版本/并发比较，SHA256用于文件完整性；不把MD5当作加密安全证明。

## 3. 2.4.3 Export/Import事实：ZIP不能独自证明无损

下列事实来自[2.4.3 ConfigController](https://raw.githubusercontent.com/alibaba/nacos/2.4.3/config/src/main/java/com/alibaba/nacos/config/server/controller/ConfigController.java)，实施前还需对实际源版本做能力核验：

| 操作 | 版本事实/影响 |
| --- | --- |
| GET `/nacos/v1/cs/configs?export=true` | 旧ZIP按group/dataId存body，可附appName元文件，不能靠扩展名还原完整type/tags等 |
| GET同路径`exportV2=true` | 新ZIP追加metadata.yml，保存group/dataId/desc/type/appName；模型没有configTags/encryptedDataKey |
| POST同路径`import=true` | multipart file，目标参数叫`namespace`（不是单项接口的tenant），policy缺省ABORT；命名空间须已存在；按ZIP metadata版本解析 |
| ZIP export/import加密处理 | 导出先decrypt，导入又encrypt；原encryptedDataKey和存储ciphertext不保证相同，不能当exact通道 |
| 单项POST `/nacos/v1/cs/configs` | 支持tenant/group/dataId/content/type/appName/config_tags/desc/use/effect/schema/encryptedDataKey；非空key路径与无key自动加密路径不同 |
| 单项DELETE同路径 | tenant/group/dataId定位配置，非删除namespace；无CAS参数 |

[ConfigMetadata](https://raw.githubusercontent.com/alibaba/nacos/2.4.3/config/src/main/java/com/alibaba/nacos/config/server/model/ConfigMetadata.java)证实ZIP V2元数据缺少tags和加密key；[ZipUtils](https://raw.githubusercontent.com/alibaba/nacos/2.4.3/config/src/main/java/com/alibaba/nacos/config/server/utils/ZipUtils.java)按UTF-8转换。**即使ZIP导入API返回成功，也不能据此声称本次字段exact。** `succCount`之外，fail/skip/unrecognized及完整逐项回读都要核；不默认OVERWRITE。

### 所选执行路径

1. ZIP V2可作受保护辅助导出，权威manifest还必须补齐逐项字段；本次优先**完整私有manifest＋单项POST＋逐项回读**，避免ZIP缺字段。
2. 配置详情`show=all`可补type/appName/configTags等；但详情和普通GET均可能先解密，不能把解密后的body配旧encryptedDataKey当作原始ciphertext发布。依据：[ConfigServletInner](https://raw.githubusercontent.com/alibaba/nacos/2.4.3/config/src/main/java/com/alibaba/nacos/config/server/controller/ConfigServletInner.java)、上述controller。
3. 先只报告非空encryptedDataKey的数量/布尔。如果36项全无加密key，按受保护GET body＋详情元数据核MD5/bytes后原样POST；仍显式保留空key/tag/type/appName状态，不能丢字段。
4. 如存在非空key，必须在清理前证明能取得并核对原始存储content＋同key。2.4.3分页`search=accurate`返回ConfigInfo，controller本身没有详情的decrypt步骤，是候选raw通路；但须实际核raw-content MD5与原存储md5一致，并与详情元数据交叉核验，不能仅凭字段名猜已取得ciphertext。模型依据：[ConfigInfoBase](https://raw.githubusercontent.com/alibaba/nacos/2.4.3/config/src/main/java/com/alibaba/nacos/config/server/model/ConfigInfoBase.java)、[ConfigAllInfo](https://raw.githubusercontent.com/alibaba/nacos/2.4.3/config/src/main/java/com/alibaba/nacos/config/server/model/ConfigAllInfo.java)。
5. 原样ciphertext/key的接收、回读及源/目标加密插件兼容不能证明时，在DELETE前失败；不改key、解密重加密凑“同样内容”，更不SQL查询/覆盖源或目标数据库来绕API。
6. 全部字段从源包经同协议投影到目标逐项exact核验；服务端会规范化或默认化的字段先验证可回写，无法保留则停止，不能只验证正文SHA。

## 4. 保护目标再清：完整快照与逆向计划

- 清之前从所有目标namespace导出当前每一配置的原body和上述可恢复字段，固定当前7项key/MD5/版本；同时冻结原namespace ID/name、user/role/permission关系、服务及DB结构元数据，供“没有越界”后验。快照不是用户/数据库迁移。
- 全部敏感材料只留受控700目录/600文件，不进Git、日志/聊天或公开evidence。候选PVE保护位置可为store下`test-nacos-config-change/<work-id>`，实施前核真实挂载/空间/权限；这是一次配置变更回退材料，不新增测试自动备份任务。
- body文件用opaque编号，key留私有manifest；不把group/dataId拼成路径。包须校大小/SHA、成员范围、重复/路径穿越和可重复读取。source原样快照不能被“适配候选”覆盖，本期不产生适配候选。
- 删除前就具备可审的逐项回写、回读比对和补偿journal；若快照字段不能完整回写，仅能停在export/plan，不能先清。文件/ZIP可读只证明快照完整，不等于实测恢复；以前正式小SQL恢复不替代本次测试配置回退能力。
- API回写不能还原旧数值ID/修改时间/全部history时点；DELETE/POST会新增历史，保留原历史而非直接清history表。不能承诺删除后history仍是旧计数9。

## 5. 原样内容、端点与secret边界

**不改端点，不改profile，不删/替换secret，不重新格式化YAML或换行/BOM。** 源里的Mac/loopback/旧10.63/正式或第三方地址及敏感字段按用户原样选择保存，不当作已适配、可运行的test配置。实施者不能据这些值连接外部服务、创建业务DB、启Java/调度或发通知。

body及元数据的值只在受保护流程内传递，普通报告只留保密审查是否遵守、原样比较是否相同，不打印秘密、content或encryptedDataKey。认证采用已有受控凭据，不读出/复制整份.env，不重置源/目标管理员密码。原基础.env/health仍可指旧namespace保兼容，不因新源ID自动改它；以后业务接入须单独选ID及授权。

## 6. 并发保护和全部配置清理

- 一个协调者持work-id锁；源读取窗口和目标配置发布维护窗口明确，Java仍不启动，其它手工/自动写配置暂停。本地flock不等于服务端全局排他，也不能通过改role/permission伪造冻结。
- 立即写前，source key/版本/md5仍为`S_before`，target仍为`T_before_all`。任何漂移停止，不把新项自动加进Delete_set。当前7只是预期基线，必须fresh验证。
- 每次DELETE前再次核固定19.20、显式namespace/group/dataId及原MD5/版本；删除后核该键404。全部结束后枚举所有目标域证明配置集合为空，403/500不能当作不存在。
- DELETE无CAS，读后删仍有竞态；没有可落实的写入维护窗口就不执行。单项POST的casMd5 header只适用于其已有配置条件更新，不制造DELETE或“条件不存在创建”的原子保证。
- 不调用namespace DELETE、batch numeric-ID删除、SQL/TRUNCATE、服务注销、bootstrap管理员或role/permission变更。配置DELETE经OpenAPI产生正常history，原业务数据库与四组件保持。

## 7. 创建缺失源域元数据、原样导入36项

1. 清理完成后核原namespace保留；对于源两ID只创建缺失的同ID/name元数据，不赋应用角色权限。创建前无碰撞，创建后ID/name一致；基础账号/权限/服务和DB结构不变。
2. 对36个键逐项POST，明确tenant/group/dataId/type/appName/config_tags/encryptedDataKey及其它完整字段，body原样。认证token仅进受控Authorization，content仅进受保护请求body，不放URL/argv/env或打印原始响应；拒redirect。
3. 写前发现非预期同名项即停，不覆盖外部写者。每项立即回读并private比对body bytes/MD5/SHA与全部字段，而非只看true/HTTP200。
4. 最终`T_after == D_expected`，finger-cloud-dev32、finger-trascan4，其它保留namespace配置为0；键集合一致且36项内容/元数据exact。保留原ID/name/group，不把源合并进old finger-test或finger-test-empty。
5. 再核`S_after == S_before`、源不变；目标原域与账号/role/permissions/业务DB/四容器保持，仅多出必要两域元数据和对应配置。注册服务不新增/删除；history新增变化按配置操作记录，不伪称history计数不变。
6. 普通回执只记录namespace映射、计数/键清单或其受审摘要、exact布尔、基础meta保持和限制；不输出body/secret/key/指纹。admin可管理不代表应用账号已授权；不启动Java来“验证配置生效”，不签业务E2E。

## 8. 失败补偿

清理前失败零改目标；清理/导入中失败立即停止并保留准确journal。配置跨项非原子事务；按`T_before_all`回写旧项，删除补偿只限本run新发布且当前hash仍属于本run候选的项，外部漂移不覆盖/扩删。新增两域可保留为空元数据，不借补偿删除namespace。

回退逐项证明原key/type/内容/元数据匹配，原user/permission/service与DB未变；新审计历史保留。无法完整补偿明确partial/failed，不称已恢复。不能恢复整库MySQL或重置权限来完成配置回退。

## 9. 本地旧工具与实现约束

| 来源 | 处理 |
| --- | --- |
| [publish-test-nacos.py](../../infra/java/runtime/publish-test-nacos.py) | 旧prepared业务子集/旧10.63 target，不是两源域原样全量、全部目标保护/清空/补偿器；不--apply。只借鉴受控token、NoRedirect、按key回读模式 |
| [prepare-test-chain.py](../../infra/java/runtime/prepare-test-chain.py) | 会生成业务配置/秘密/SQL，不读取其产物，不运行，不进行test适配 |
| [manage.py](../../infra/data/scripts/manage.py) | 基础生命周期/bootstrap会写日志/账号权限，部分health读probe；本次不重部署或bootstrap，不能借它给新域授权 |
| [acceptance.py](../../infra/data/scripts/acceptance.py) | fixture/SQL写路径，不作配置导入验证 |
| [空域回执](../20261109-test-env/empty-namespace-created.json) | 保留基础域/role的历史起点，不能替代本次所有目标域清单 |

没有可不经改造直接复用的现成全量无损执行器；主AI实现后须审查API字段完整性、7→0→36完整集合、metadata-only建域和受保护补偿，不能直接重跑旧manager/stage。上述旧源码仅读用途/接口，未执行或读取其业务body。

## 10. 当前设计状态

来源两ID/name及32＋4、目标全部配置清理、原样内容、不适配、不新增应用权限均已明确。仍需工程完成：fresh源/目标私有快照与指纹、全部字段/加密路径可回写证明、稳定窗口及精确执行器/补偿校验。**本文件不是执行回执：本任务未读用户配置body，没有server write或clear/import。** root完成执行器后再做独立review，不新增等待用户重复授权的环节。

API身份与namespace参数规则另见[官方2.4 OpenAPI](https://nacos-group.github.io/docs/v2.4/guide/user/open-api/)。单项V1用tenant，ZIP import用namespace，V2用namespaceId；不能混用或省略导致public默认写入。
