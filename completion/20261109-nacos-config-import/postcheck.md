# Nacos配置导入：独立只读postcheck

采集：2026-11-09T13:41:50.274023+00:00。all_passed=true，限本页定义的正文一致性、可空元数据语义与元数据保留范围。没有DELETE/配置POST/grant/账号重置/Java启动或Git操作。

## 来源和目标内容

本机仅GET重新核对用户选定36项：原正文逐字、MD5及showall元数据与Mac私有source.json保持。没有修改源，也没有把内容/原始hash/key/token写到普通证据。

目标在VM210内只读取自己原run/source.json（root600），以adminfreshGET普通body及showall在内存比较36项，不将目标正文传回Mac。identity集合完全匹配、36原文和MD5全部一致。全实例36份，DEFAULT_GROUP36、35yaml+1text。

| namespace | 真实ID | 当前配置数 |
| --- | --- | ---: |
| public | `(public空ID)` | 0 |
| finger-cloud-dev | `08e7191f-3ccd-411a-be00-56798d237533` | 32 |
| finger-test | `10719261-2641-590a-b821-c8484ca955ac` | 0 |
| finger-test-empty | `23836f2e-9553-5948-84cd-431b2f241bd6` | 0 |
| finger-trascan | `7bfe03c6-0590-4ff0-8def-e07015016b54` | 4 |

因此public、原finger-test、finger-test-empty的配置项均为0，namespace对象保留；仅finger-cloud-dev32和finger-trascan4承载导入配置。没有把业务库整体迁移或新增其它来源。

## 元数据精确性边界

type/appName/tags/encryptedDataKey与配置身份按审核后的null/empty语义逐项匹配，36项通过；**原始可空字段表现有3项desc差异**，仅为空字符串与null的序列化差异，独立报告记录计数，不声称数据库nullable字段字节完全相同。配置正文逐字与MD5仍全部精确，不做换行/转义转换来凑通过。源metadata原样保持另行精确验证。

## 原基础与回退档

- users2/roles2/permissions2，与原已建空namespace后基线保持；client角色关联不变，resource精确仍原10719261…与空23836f2e…两条rw，没有本postcheck新增grant。
- schema表数仍finger_auth_test3、finger_coms_test10、finger_system_test6、nacos_test12；未查询业务行或读取配置正文以外SQL数据。
- 原4容器ID/Image与test-env.preflight相同，running/healthy/restart0/OOMfalse；当前PID/StartedAt已采，因原preflight没存这两字段，不编造旧PID逐项相等证明。producer有独立before/after frame保护记录。
- readiness/UI HTTP200，仅状态，未保存页面/健康正文。
- 原7项回退档run `e57ebd00096d42ecbccdf7a72b4afb04` 与剩余5项回退档run `12b575d6d3d04e978b904197bf3d67ee` 的target-before.json均存在、非symlink，所在目录root700、文件root600。只stat，没读取备份body或hash；7/5数量依据各prepared收据。

普通证据：[postcheck.json](postcheck.json)。本次只读admin登录和GET、现有helper SQL表计数、公开容器metadata与私有备份stat；不调用m.cfg/preflight/run/auth/bootstrap，不执行业务写、外发消息或VM240动作。Java不启动，正式201未触及。原文导入不等于配置中的开发地址已适配测试业务，不能以此宣称Java可上线。
