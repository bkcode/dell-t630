# 测试Nacos配置受限替换

本次用户明确授权的来源是本机两个固定namespace（finger-cloud-dev32＋finger-trascan4），目标仅VM210/19.20测试Nacos配置items；保留namespace ID/name/group/正文，不改端点/profile，不迁账号/权限/业务DB，不启动应用。

实际结果见[交付与验收](../../../completion/20261109-nacos-config-import/README.md)，执行器是单次受控实施源码，不是通用无人值守同步或回滚入口。

## 私有协议与阶段

`source.json` version1、namespaces含id/name/count、items包含namespace_id/namespace_name/data_id/group/type/app_name/description/config_tags/encrypted_data_key/content/md5。文件及source-manifest、target-before和journal均只在private或guest root700/600。任何非空加密key或tags会在写前拒绝，本期实际均空；不把Nacos2.4.3普通GET的解密正文和旧key混写。

PVE受信SSH/ub sudo只下发代码及私有包至固定VM210；root先创建新nonce目录，只有source.json时才prepare。prepare校本地bodyMD5、source两域32/4、所有字段与冲突，再完整保存目标全部配置body/metadata及namespace快照。没有成功回退材料不得apply。

apply重校source和目标集合/正文，缺失时只创建两个源namespace；每条DELETE前再次核baseline、操作后有界GET等404。Nacos删除DB后plain缓存可短暂200，此阶段只核旧正文/MD5，不用已消失DB行的showall。确认全实例0后逐项POST；POST后只允许短暂404等待，200错body立即停；随后普通GET＋showallJSON＋storedMD5＋SQL元数据共同核验。最终全实例36及完整键集合和字段必须一致。

verify从不可变source.json（含count）重校并和规范manifest比较，再完整读目标。所有源码内容与真实MD5仅私有内存/文件比较，普通报告只counts/bools/nsid/name/type/group。nullable空值按Nacos语义比较，配置正文绝不strip、改换行或替换地址。

## 并发与失败

Nacos2.4.3 DELETE没有serverCAS，客户端flock不能等同服务端全局排他。执行窗口内应停止人工配置编辑，若任一集合/MD5/正文漂移即停止，不自动强删/覆盖或回滚。所有回退须先核现况及exact属于本次的写入，禁止根据“全部清理”绕过快照去删后续未知内容。

本次首次run备份原7，已删2后缓存readback暂停；旧7快照完整保留，新run只备剩5/清5/导36，未把旧manifest重写成5。原snapshots与失败诊断/journal保留。手动回退材料不是测试自动备份计划。

程序只允许固定目标HTTP API、guest/dataUUID并拒重定向和环境代理，凭据仅guest现有secret文件；没有源码profile写、配置payload日志或Java执行路径。未来修改源码/目标/数据集须重新核实际授权与API模型，不盲重跑本次apply。
