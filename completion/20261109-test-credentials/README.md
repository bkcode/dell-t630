# 测试数据组件固定凭据同步

2026-11-09 23:34:35（Asia/Shanghai），仅VM210 / data-test / `192.168.19.20`。用户明确给出三组件账号密码并再次要求保持；本次将之前生成的测试值对齐用户指定约定。真实值不在本页、代码、验收JSON或Git保存。

| 组件 | 连接 | 本次作用 |
| --- | --- | --- |
| MySQL | 19.20:3306，root | 同步现有localhost/%两行密码，保留caching_sha2_password、Host、grants、SSL/锁定属性；短时双密码过渡完成后移除secondary |
| Redis | 19.20:6379，数据库0 | 同步default认证、持久secret与当前runtime配置唯一requirepass行；其它ACL和数据保持 |
| RabbitMQ | 19.20:5672 / 管理15672，admin | 增加指定管理身份，允许默认`/`与现有`/finger-test`；原mq_test_admin和finger_test_mq及其密码/权限保留 |

[实际apply回执](applied.json)退出0，四个容器ID/PID/启动时刻与监督MainPID/启动时刻保持，未重启。数据、Nacos账号/DB用户、源Mac与正式200/201不在本次变更集合。Rabbit同步的是新管理身份，不把旧管理secret改写理解成旧管理账号密码也改变。

## 持久来源

现役guest `/opt/dell/data/test-data/secrets/`的三secret及Rabbit definitions、`.env`管理名已同步。Docker按文件inode绑定，实施逐项校验身份后原inode写入并fsync，保留UID/GID/0600；未rename secret或修改Docker socket权限。Redis未CONFIG REWRITE、未改父目录权限，entrypoint以后仍从新secret生成配置。

Mac活动副本仅`private/data/store/test`与`private/data/bundles/test-data`共10文件同步，见[镜像回执](local-mirrors.json)；原活动副本另存private700/600，历史归档、源`work/nacos`与prod副本不动。**不得重跑旧prepare/init或重新生成测试凭据覆盖本次约定**；现役值是运行维护来源，不是旧bootstrap随机值。没有通过重启证明未来重新导入，后续正常维护重启应复核三组件认证。

## TLS与权限解释

MySQL原本提供TLS，但`require_secure_transport=0`且root ssl_type为空；本次不启用/禁用服务端TLS、不改认证插件。socket和TCP fresh连接均验证，TCP检查使用客户端`--ssl-mode=DISABLED --get-server-public-key`，只说明原caching_sha2认证可在此客户端模式完成，不据此改变或声称所有GUI驱动兼容。此前1045不应直接归因为强制TLS。

LAN21/24网络已另放行，但账号认证、SSH密钥、应用Host授权仍各自生效。ub管理Docker继续用`sudo docker ps`，不新增docker组或放宽socket。

## 证据与失败处理

[预检](preflight.md)、[审查设计](design-review.md)、[暂存](staged.json)、[apply](applied.json)均区分采样和实施状态。worker固定210身份/数据UUID、健康FailingStreak0、非阻塞事务锁；7项合成失败测试覆盖MySQL部分提交与Redis断连补偿、Rabbit持久配置和门禁。设计中的建议只有最终代码与真实回执支持的部分才签收。

受保护原文件与阶段结果只留guest root700事务目录。Rabbit不是全组件事务，失败不得盲新nonce重跑；先核该run实际partial和原管理入口。MySQL/Redis各有运行态与文件补偿验证。不要用全量用户表/definitions/业务库恢复代替精确修复。

[独立后检](postcheck.md)12项全通过，[本期验收](acceptance.json)4项通过；另从Mac直连MySQL的新连接认证成功。Nacos36配置、Puyu51表计数、原账号与容器身份保持。不把未执行的重启或GUI兼容签成通过。
