# Puyu本机两库复制到Dell测试MySQL：影响报告

仅持久数据/基础设施复制；源Puyu代码、publicAPI、Gateway/Auth/BFF/Core/前端契约和应用连接均不改，无provider发布或cache刷新。目标写只限VM210此前不存在的puyu_auth_local与puyu_erp_local及本次临时受限importer，源保留、正式200/201不写、Nacos及Java不改。

源业务可继续DML，本次为singletransaction导出时点；DDL只在dump期间短时backup lock保护，释放确认。当前全部51InnoDB/allPK、无view/routine/trigger/event，不修改目标global event_scheduler。若实际出现不支持对象/目标同名，停于写前，不自动DROP覆盖。

用户当前消息已明确批准puyu_*迁移，不重复请求同一授权。Puyu Harness契约保存在本Dell任务目录，避免在未授权Puyu代码仓库写入。所有数据与真实摘要仅700/600私有文件+SSH，普通证据只count/booleans/结构元数据；不将数据进Git。

目标失败留精确owned DB状态与private源包，不盲删/覆盖旧数据；源始终可作回退，应用连接未切换。最终仅签数据库快照复制，不扩签在线切流、业务运行、RPO/RTO或独立灾备。
