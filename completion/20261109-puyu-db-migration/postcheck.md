# Puyu迁测试：独立只读postcheck

采集：2026-11-09T15:11:07.273072+00:00。all_passed=true，所有比较均在受控程序内完成；普通证据没有SQL正文、业务行、行digest、实际数据hash、密码或认证hash。

## 逐表快照验收

目标从自己的root600私有manifest.json读取fingerprint，**51张表每张都独立执行SQL COUNT(*)**，与manifest.fp的对应row_count比较，不用information_schema估算行数、不用总数掩盖单表差异。

| schema | 表数 | 实际COUNT总行数 | 与导出快照比较 |
| --- | ---: | ---: | --- |
| `puyu_auth_local` | 4 | 178 | 逐表全部相同 |
| `puyu_erp_local` | 47 | 1113 | 逐表全部相同 |

完整表名集合、SHOW CREATE TABLE经同一已审语义canonicalizer处理后的DDL（含PK/unique/FK等约束）均与source fingerprint相同，51表都存在PRIMARY。schema charset/collation全部utf8mb4/utf8mb4_0900_ai_ci，与源保持。权威collation→charset映射来自目标MySQL元数据，仅消除已证明冗余字符集表示；不移除或重写约束/注释/正文来凑通过。

本次只对COUNT和DDL/结构元数据独立复核，不重新输出/查询业务行或数据digest；root的native target redump与源完整行multiset指纹、CHECK TABLE通过收据在[verified.json](verified.json)，独立检查不冒充再次逐行重算digest。

## 原基础与清理

- 原finger_auth_test3、finger_coms_test10、finger_system_test6、nacos_test12表保持，当前Nacos配置COUNT36。
- 原4容器ID/image与迁移preflight相同，running/healthy、restart0/OOMfalse；当前PID/StartedAt已采。原preflight没有PID/StartedAt，故不编造这些字段的前后精确相等证明。
- 本run `puyu_import_e28bf9aa3e8f`账号COUNT0，所有本协议临时importer前缀账号COUNT0。
- 容器`/tmp/dell-puyu-import-e28bf9aa3e8f44328eab71190a5a93a8`不存在，只做存在性检查，没有读取client.cnf或秘密。

## 源保留与密码/配置边界

本机源两个puyu库仍在、当前表数和COUNT已记录；允许源DML继续，所以没有强迫当前COUNT等于历史exportpoint。源固定container/image不变、RestartCount0/OOMfalse、StartedAt早于导出，未观察到重启。

本次及导出代码只读取原container内既有认证，不reset/change密码、认证plugin或服务配置。**没有采集过导出前密码/配置文件内容hash基线，因此不虚构独立“字节hash未变”结论**；本报告只签无相关写请求/同源身份，用户root原私有密码TLS认证成功及认证诊断属于root另行证据。不会为3306访问1045或2061修改密码/TLS/Host权限。

## 操作范围

只读target已部署root_sql直接helper与metadata，不调用m.cfg/preflight/run/迁移main/apply，不导出或重导目标，不写schema/账号/Nacos/服务，不Java/Git或外发。没有改源连接或停应用，正式200/201未操作。机器证据：[postcheck.json](postcheck.json)。
