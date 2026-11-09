# VM210测试基础只读预检

采集：2026-11-09T12:17:16.990953+00:00。用户最新范围为**不迁移任何数据，仅检查搭建测试基础；现有数据保留，不导入业务SQL/配置，不启动Java**。本次完全只读，认证仅使用guest内现有root600文件，未输出密码/token/配置正文或业务行。

## 当前基础已就绪

- hostname=data-test、IP192.168.19.20/24、默认GW/DNS19.1。
- /srv/dell-data实际ext4 UUID `dd1773f9-aa48-4401-a9c8-caf0f66845f3` 与plan匹配。
- mysql/redis/rabbitmq/nacos四原容器running/healthy，restart0、OOM=false。
- Nacos2.4.3 readiness GET200；原admin认证成功，命名空间读回与数据库元数据一致。
- 测试namespace `10719261-2641-590a-b821-c8484ca955ac`，名称`finger-test`；有1条rw权限记录、1个已启用账号经角色关联该namespace的rw权限。只返回计数，不输出账号名/密码hash/权限值；没有执行账号重置或再次负向写测试。

## 必须保留的现有数据库与配置

| 实际schema | BASE TABLE数 | information_schema估算bytes |
| --- | ---: | ---: |
| `finger_auth_test` | 3 | 49152 |
| `finger_coms_test` | 10 | 393216 |
| `finger_system_test` | 6 | 229376 |
| `nacos_test` | 12 | 409600 |

当前真实业务测试schema是`finger_auth_test`、`finger_coms_test`、`finger_system_test`，合计19表；不是按猜测构造的`finger_test_auth/system/coms`名称。没有读取业务行，也没有COUNT业务表数据行；bytes只是表元数据估算。

Nacos外部MySQL库确认为`nacos_test`（现有应用账号SELECT DATABASE返回）。测试namespace的`DELL_TEST`组当前**7份yaml配置**，Nacos历史配置记录COUNT9；未查询配置content值，也未发布、导入、覆盖或删除配置。旧文档18表/6配置等数字不作为现状，本次不为匹配旧数字做清理。

“空测试基础”在最新用户指令中是**不再迁入新数据/业务配置**，不能解释为授权清除这些已有schema、namespace或7份配置。现存数据来源/可否清理没有新授权，全部保留。

## 可补齐项与边界

本轮未观察到缺失的基础依赖：四组件、原UUID、网络、readiness、现有namespace及关联rw身份均就绪，**无需要立即初始化或补写的项**。没有执行Redis/Rabbit账号重建、Nacosbootstrap、fixture、schema初始化或Java启动。

认证与检查仅调用installed acceptance.mysql的直接subprocess查询及原Nacoslogin+GETnamespace；未调用m.cfg/preflight/run/auth/fixture（这些管理路径可能写private部署日志或产生测试对象）。没有读取.env值/输出凭据，没有服务器目录或容器创建、备份/迁移/重启、Git操作。

权限就绪只证明本次admin认证与已存在的namespace/角色授权元数据；未重新验证所有客户端/跨namespace否定测试。Redis/Rabbit本次只用原容器健康观察，不宣称全业务协议E2E。root统一所有后续写和Git；若后续出现真实缺项，应精确审查后再开窗口，不重跑旧10.63初装脚本。

机器证据：[preflight.json](preflight.json)。被中断的前任务仅本地读公开代码，未留下远程动作或输出；本次先检查无既有结果后才执行必要预检，没有重复迁移或初始化。
