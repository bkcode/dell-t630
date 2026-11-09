# 测试Nacos选定配置原样导入：已完成

2026-11-09（Asia/Shanghai）。用户最新明确授权：清测试210内全部配置items，来源仅本机finger-cloud-dev32和finger-trascan4，共36，保留source namespace ID/name/group和正文原样，不改连接地址/profile，不启动应用。本次覆盖先前空服务限制，但不包含业务数据库、账号权限或正式环境迁移。

## 最终使用入口

测试UI：http://192.168.19.20:8848/nacos/，沿用现有管理员nacos（密码仅受控文件，不在普通文档）。

| Namespace | 保留的源ID | 当前配置数 |
| --- | --- | ---: |
| finger-cloud-dev | 08e7191f-3ccd-411a-be00-56798d237533 | 32 |
| finger-trascan | 7bfe03c6-0590-4ff0-8def-e07015016b54 | 4 |
| public | 空ID | 0 |
| finger-test（旧） | 10719261-2641-590a-b821-c8484ca955ac | 0 |
| finger-test-empty | 23836f2e-9553-5948-84cd-431b2f241bd6 | 0 |

全实例36项，全部DEFAULT_GROUP，35yaml＋1text。查看导入内容需在UI选择前两个空间，不是先前finger-test-empty。原来7项已从当前配置列表清除，namespace与历史审计保留，不SQL truncate。未选的本机Broker/Puyu/public数据未导入。

## 私有保护与实施

[源清单](source-inventory.md)及[私有导出收据](source-export.json)核源36项，源GET正文、showall.content和真实storedMD5交叉一致；source前后稳定，tags/key均空，body105559B包只在private/SSH，普通证据不含正文、密码、MD5/key值。2.4.3列表md5字段可能null，不能把它当真实摘要；使用单项detail与body确认。

[初始准备](prepared.json)完整保存在VM210 `/root/dell-nacos-config-import/e57ebd00096d42ecbccdf7a72b4afb04/target-before.json`（原7项）；首次apply在DELETE后plainGET缓存尚未变404时安全停止，见[失败记录](first-apply-failure.json)和[只读诊断](delete-readback-diagnostic.json)。已删2、剩5，无新增sourceitem。没有覆盖原7快照或盲重跑整个7项列表。

修正为DELETE/POST后仅有界只读等缓存可见，不重复写；DELETE的旧200必须与baseline原文/MD5匹配，404才能继续，不调用已删除DB行的showall；POST仅404可等待，200错正文立即停。

[新run准备](remaining-prepared.json)另存剩5项回退快照，run12b575d6d3d04e978b904197bf3d67ee；[apply](applied.json)清剩5、确认全实例0、再逐项发布36；总原7清理=首次2＋新run5。[新独立SSH verify](verified.json)再次全量核原namespace/group/type和正文。两私有回退快照均root700目录/600文件，临时手动回退材料，不新增测试自动备份计划。

**并发边界**：Nacos2.4.3 DELETE没有serverCAS，本次明确操作窗口、客户端锁和逐项fresh双读漂移检测，不把它称为服务端全局排他；失败不盲删/自动覆盖未知写入，私有journal保留。

## 实际验收与限制

[独立后验](postcheck.json)核本机源36仍同私有export，目标36身份集合、正文逐字及MD5全部精确一致，原ID/name/group保留。可空元数据按已审语义比较：3项source空description在目标为null，不宣称nullable字段raw字节一致；正文未strip、转换或替换。

users2/roles2/permissions2及旧两resource保留，旧3业务schema表数3/10/6+nacos_test12保持，原4容器身份/镜像healthy/restart0/OOMfalse，UI/readiness200。应用finger_test原权限仍仅旧finger-test＋finger-test-empty，没有自动给新两个导入空间授权；管理员可管理，后续应用接入另配权限。

[运行/监控后验](runtime-ops-postcheck.json)：VM240 Java业务进程0、15/15targetsUP、Prom/AM无活动告警，机内Larkactive而无人工发消息。正式实例、网关/LAN放行、业务DB、源码profile与自动备份范围没有因导入改变。

原样导入意味着配置可能仍指向源本地/其他依赖地址；本次未做测试端点适配，不表示应用已部署或可运行。这是一次性配置复制，不持续同步；未做业务E2E/RPO/RTO或外发副作用验收。

实现：[受限执行器](../../infra/data/nacos-config-import/target-worker.py)及[设计审查](design-plan.md)，当前四项见[验收清单](acceptance.json)。
