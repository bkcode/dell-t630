# 测试19.20指定凭据：独立只读后检

采集：2026-11-09T15:37:53.078706+00:00。**all_passed=true**。本次独立验证使用VM210自己已有root600 desired.json和before-files.json，在guest内存读取、比较，不读取或传输Mac本机desired/旧秘密；普通证据只给布尔、计数、公开容器/文件元数据。

## 新连接认证证明

| 服务 | 独立验证 | 保留边界 |
| --- | --- | --- |
| MySQL | 显式desired新密码的fresh socket连接匹配root@localhost；fresh TCP19.20:3306、TLSdisabled+get-server-public-key匹配root@% | 原Host集合、caching_sha2_password、ssl_type空/unlocked、require_secure_transport=false全部相同；没有secondary password残留 |
| Redis | 自建只读RESP2新连接执行AUTH default+PING成功；ACL GETUSER default只在内存比较，恰好一个desired password hash | 非password ACL字典与before完全相同；runtime配置除requirepass行外字节相同，未CONFIGSET/REWRITE |
| RabbitMQ | 新admin使用desired新密码fresh HTTP whoami；AMQP连接认证并打开`/`和`/finger-test`均成功 | 旧admin使用原密码HTTP仍成功；旧app原密码AMQP仍成功；旧runtime userhash/tags与旧definitions私有比较保持 |

这些验证没有调用应用helper去偷偷回退旧秘密；MySQL和Redis显式用本run desired值，Rabbit原/新认证分别使用不同来源。AMQP只做connection/auth/vhostopen，不创建队列、不publish、delete或消费消息。本机LAN MySQL外部连接由root另行验证，见[LAN-MySQL-auth.json](LAN-MySQL-auth.json)，本报告不冒称自己复测外网链路。

## 文件、权限与持久引用

- 五文件mysqlroot/redis/rabbitadminsecret、bundle.env、definitions的device/inode/UID/GID/mode与guestbefore-files.json相同且600，无symlink；不是atomicrename替换。
- 三新secret当前bytes精确等于guestdesired+newline，仅在内存比较；container内三个filebind的inode/UID/GID600也与本次preflight相同。
- bundle.env只RABBIT_ADMIN_USER键改变，其它字节按原worker合同保持；所有旧definitions user/vhost/permission和其它字段保持，新admin追加由producer独立记录。
- Redisruntimeconf与私有before相比，只有requirepass行变为desired；原ACL类别/keys/channels等完全保持。实际操作由rootworker完成，**本postcheck没有写文件或执行任何变更命令**。
- root已同步本机私有镜像文件，证据见[local-mirrors.json](local-mirrors.json)；本后检仅server范围，不把其回执当自己重新读传Mac秘密。

## 数据与服务保持

- Puyu51张表每张独立COUNT与原export snapshot一致：puyu_auth_local178、puyu_erp_local1113；原Finger表数3/10/6、nacos_test12及Nacos配置36保持。
- 原四container ID/Image/PID/StartedAt与本日Puyu postcheck前基线精确相同，healthy/restart0/OOMfalse，未重启。
- dell-data-test-data.service active/running、原MainPID1202、NRestarts0。独立旧基线没有monotonicstart字段，本次只采当前，不伪造逐项start相等；rootproducer另有前后supervisor start精确比较。

## 范围与限制

仅测试VM210。未访问/修改本机源数据库或正式200/201，没有改TLS/authplugin、Nacosadmin/DBuser/appuser、Java或源连接。Nacos36配置的COUNT保持不等于本次重新认证所有Nacos用户或重新逐字比正文；已存在的Nacos导入证据负责该范围。

没有服务器写、账号/ACL/grant变更、文件同步、重启、dump、业务行读取、原文/密码/hash输出或外发通知/Git。密码、salt、runtime requirepass与旧hash仅内存比较，JSON只有结果。证据：[postcheck.json](postcheck.json)，producer状态：[applied.json](applied.json)。
