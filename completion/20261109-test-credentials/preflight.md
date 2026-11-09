# VM210测试凭据同步：只读管理方式预检

采集：2026-11-09T15:15:24.936640+00:00。用户明确指定测试19.20应保持所给账号密码；本次仅识别安全在线变更方式，**未修改任何密码/配置、未CONFIG REWRITE、未重启或备份**，普通证据没有当前密码、认证hash或完整Env/Cmd。

## MySQL

- root@%与root@localhost均已存在、unlocked；plugin=caching_sha2_password，ssl_type空，require_secure_transport=false，bind=*。不以本次需求更改TLS、plugin、账号Host或全局安全开关。
- 当前root授权helper可用；凭据只通过容器内部已有挂载读取，不进普通argv/输出。NacosDBuser、appusers与Nacosadmin保持。
- 活动rootsecret host `/opt/dell/data/test-data/secrets/mysql-root-password` → container`/run/secrets/mysql-root-password`，UID/GID999/999、600、host/container inode均285669。

## Redis

- 原secret认证PING成功，protected-mode=yes。运行config_file为`/run/dell-redis/redis.conf`，tmpfs、UID/GID999、600/inode2；Redis进程UID999。原requirepass值没有查询或输出。
- 公开entrypoint从`/run/secrets/redis-password`生成runtime配置；每次启动会覆盖该runtime文件，所以只改runtime不会保证未来启动保持用户指定值。
- 持久secret host `/opt/dell/data/test-data/secrets/redis-password`，UID/GID999、600，host/container inode均285678，RO bind。
- `COMMAND INFO config|rewrite`证明该命令存在，**没有执行**。runtime父目录root:root0711，不能仅凭文件可写推定具体rewrite I/O流程必成功；root应审核最小runtime+持久secret同步方式，避免改目录权限/重启来绕过。可控原inode配置更新方案也需root明确窗口，当前没有实施。

## RabbitMQ

- 当前RABBIT_ADMIN_USER公开键值为`mq_test_admin`，该运行账号tags=administrator；另有应用账号`finger_test_mq`，现有`admin`不存在。
- 唯一现役vhost `/finger-test`；两个旧账号均拥有原.* configure/write/read权限。持久definitions用户、vhost和permissions一致；没有输出password_hash或runtime参数值。
- definitions host `/opt/dell/data/test-data/secrets/rabbit-definitions.json` → `/run/secrets/rabbit-definitions.json`，UID/GID999、600、host/container inode均285677。
- `/opt/dell/data/test-data/secrets/rabbit-admin-password`是管理helper受控引用，root:root600/inode285675，没有直接bind进Rabbit容器。用户指定admin时应按root明确方案新增/同步，不误删或重置旧管理/应用账号、vhost及权限。
- Rabbit公开config引用现definitions路径，当前不改配置布局、TLS或原cookies。

## 持久文件与本机副本

**所有live Compose secret是文件级RO bind：不能用rename/atomic replace换inode。** root后续须按精确路径与预期inode/UID/GID/mode校验，原inode打开写入、truncate+fsync并保留原所有权/600；同步运行态与持久引用后以同容器内stat和新认证验证。这个要求与一般新配置文件原子替换不同，不能混用。此预检没有写入。

Mac本机下游副本仅stat定位，见JSON `local_private_bundle_file_metadata`：

- `private/data/bundles/test-data/.env`（600），selectedadmin用户名改变时须由root只改该公开键，其余保持。
- 同bundle的mysql-root-password、redis-password、rabbit-admin-password、rabbit-definitions.json。
- `private/data/store/test/`对应3份secretstore文件。

这些是不同inode的副本，不是假定hardlink；root需按未来privatejournal明确同步集合、备份和失败恢复，不能把本机源`/Users/.../work/nacos`或正式200/201加入变更。rollback材料只能private700/600，不打印旧值/hash；不要wholebackup220或碰CF。

## 结果边界

当前已获得足够公开管理元数据，无需猜密码或重建服务。root统一后续测试only在线写窗口与验证；本次未改任何服务器或本机secret内容，未发外部消息/Git/Java动作。既有库、已迁puyu数据、Nacos36配置和账号角色不因凭据同步被初始化。

机器证据：[preflight.json](preflight.json)。JSON含精确sourcepaths/inodes、TLS元数据、Redis能力布尔、Rabbitnames/tags/vhost/permissions，不含现有密码或hash。
