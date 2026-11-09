# 单份Nacos逻辑备份隔离恢复演练：最小安全设计

日期：2026-11-09。用户明确执行隔离恢复演练第1项。本文件仅本地设计/审查，**没有传输、创建容器、导入SQL、生成凭据、服务器写或Git操作**。执行与最终验收须另有实际收据。

## 目标与限制

仅从PVE既有私有prod-db备份取一份已成功的`nacos_prod`逻辑档，在VM210独立空scratch恢复并检查。当前首档run为`b16d1ed9ff0a4ff1877179428bd592c6`、3301B、12表；执行前重新核实，不仅依赖此前CRC/SHA结果。该档包括Nacos配置、namespace、历史及库内认证元数据；不用源MySQL/Nacos运行密码，不读VM200当前业务行。

本次不迁移、不覆盖用户数据，不触碰VM210现役测试MySQL/Redis/MQ/Nacos卷，不启Nacos JVM/Java业务，不访问外部端点，不更改PVE自动备份timer、retention或旧归档。结果只证明当前这份小Nacos库可在已定义隔离环境恢复，不等于正式业务恢复、获批RPO/RTO、PITR、异机灾备或原全部验收完成。

## 对象与资源门禁

主AI只读预检已记录于[target-preflight.json](target-preflight.json)：VM210建议资源帽1CPU/1GiB，采样时余量满足1GiB+512MiB且盘空闲≥2GiB，生产精确MySQL ImageID在210缓存。它是采样，不是资源预留；创建前立即重测，余量不足则停止，**不自动加内存、重启其它VM或改用生产200**。

固定目标：VM210/data-test/192.168.19.20，原数据挂载`/srv/dell-data`、UUID `dd1773f9-aa48-4401-a9c8-caf0f66845f3`。只创建新`/srv/dell-data/_prod_db_restore_qa/<nonce32>/`，O_EXCL、root700、祖先无symlink。不存在/未挂/UUID不符立即拒绝，不能落根盘兜底，也不能用`/srv/dell-data/test-data/mysql`等现役目录。

固定镜像：以预检和本次生产镜像身份一致的actual ImageID `sha256:a0f6c7786c75739bd76a37b4b85e0f47b7c5d5a17a094bdd522412fb464d5cbe`启动，`--pull=never`、linux/amd64。再次核digest/实际ID/架构，不用mutable tag、不拉新镜像。preflight中的生产访问只提供公开镜像元数据，恢复脚本不需要再连接生产SQL。

在210保存现有4容器ID、image ID、PID/StartedAt/restart/health及其完整**挂载路径元数据**为保护基线；不读Env/Cmd/healthlog。创建、导入、验证、清理各阶段比较基线，任一现役身份/健康变化立即停QA并报告，不能为“通过”重启现役服务。

## 1. PVE源档fresh复核与安全传输

1. PVE root端核`/mnt/pve/store`真实原ext4/UUID、新prod-db namespace及run目录root700；manifest/receipt/archive均regular、root600、singlelink、无各级symlink，runID和`source_vmid=200`、数据库精确`['nacos_prod']`、receipt verified。源只读，不修改归档、权限、protected标志或retention。
2. 对同一打开的源文件重新计算SHA/bytes、gzip完整CRC与展开上限，校manifest/receipt；确认dump结束标记与12表对象集。保存inode/dev/size/mtime，传输前后复核，不能用文件名代替内容身份。SHA与SQL只在PVE私有进程/文件内，公开报告只比较布尔和计数。
3. 由PVE内部QGA向**仅210**固定nonce spool传输，1MiB/块、严格base64/count/offset/累计size、总超时；`guest-file-write`的返回count必须等于请求或用明确的短写循环补齐，不忽略partial write。不得经Mac、guest-exec stdout或任务日志转发payload。
4. target写新`.partial`且root600，最后flush/close、SHA/bytes/CRC与源一致后原子封存。最后一块非空也必须写，超时/短写/磁盘满/校验不符本轮失败，不能猜成功或改源备份重试。
5. 仅公开小manifest控制元数据；含schema细节、认证hash或内容摘要的内部比较资料放target root700/600，不进入普通evidence/Git。源manifest只读，target副本属于本次QA清理范围。

本次source小档3301B，可沿用有界internal QGA文件协议；不要套一次性公开API的大文件限制，也不要因此声称该实现适用于无限大SQL。后续数据增长超过已审大小/展开/超时上限时另审，不自动放宽。

## 2. 新身份、目录和entrypoint

独立随机root密码由target本地产生，只保留本次root700目录下受控秘密文件；不复制源root/Nacos账号、DB密码或凭据文件。`MYSQL_ROOT_PASSWORD_FILE`仅传文件路径，秘密不进Docker argv/Env值、日志或普通报告。

**UID/GID必须从精确缓存镜像原生核实**，不能只凭名称假定。若确认为mysql UID999/GID999，则新data目录应chown给它并700；秘密文件给实际mysql UID/GID、0600，内部以只读文件bind挂到固定`/run/secrets/restore-root-password`。root仍可管理，但不能错误地留root:root600再以999启动，导致entrypoint读不到文件。

以该非rootUID/GID启动官方entrypoint，rootfs read-only。挂载`/var/run/mysqld`、`/tmp`为小且有界的tmpfs，前者明确UID/GID；data mount只有新空scratch。官方entrypoint会读取`*_FILE`、检查DATADIR并初始化空库，且可能执行initdb目录文件；因此**不把源SQL挂到/docker-entrypoint-initdb.d，不挂宿主config，不复用任何已有MySQL数据目录**。具体行为需以精确8.4.5镜像内脚本和原生help为准；当前上游说明仅作机制依据。[Docker官方entrypoint](https://github.com/docker-library/mysql/blob/master/8.4/docker-entrypoint.sh)

父目录root700不会自动让容器内999能读绑定的root600文件；必须同时核挂载目标的实际权限。除data新目录所有权与秘密文件外，不递归chown父挂载，更不能chown `/srv/dell-data`或现役数据库树。

## 3. 容器隔离和导入身份门禁

固定唯一容器名和owner/nonce标签，记录完整64hex containerID。参数至少：network=none、skip-networking、零PortBindings、无host网络、无Docker socket、非privileged、cap-drop ALL、no-new-privileges、read-only rootfs、restart=no、1CPU/1GiB硬帽与等额memswap、pids限额、bounded tmpfs。参数支持须原生help核验，不凭mock代替。

MySQL启动固定`event-scheduler=DISABLED`、`local-infile=0`、`secure-file-priv=NULL`，关闭binlog，限制连接数与buffer pool；MySQLX如可用也明确关闭并核实际支持。event-scheduler必须读回DISABLED，不只是OFF；DISABLED避免导入中的SQL重新开启。secure_file_priv=NULL不能被SQL动态改写；它限制服务端文件读写，但不是完整SQL安全沙箱。[MySQL服务变量](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html#sysvar_secure_file_priv)

**每次docker exec导入/查询/重启/删除前都锁定containerID并核：**

- owner/nonce标签、actual imageID、name、非rootUID与本次创建时间匹配；ID不在现役4容器集合。
- NetworkMode=none，零published ports和host/其他网络；容器本机socket可用，无外部连接。
- Mounts精确等于本次新data bind、只读临时secret，以及允许的tmpfs。没有现役data路径、父`/srv/dell-data`、生产备份/PVE路径、宿主root或docker.sock。**路径在容器里看起来是/var/lib/mysql并不能证明安全，必须检查host Source的canonical路径、inode/dev及非别名。**
- source SQL不要挂给mysqld；最好由host受控读文件通过STDIN送socket客户端，只让新data目录可写。即使只读挂载，也不能把整个QA父目录含控制脚本/凭据一起暴露。

任何身份不符都拒绝执行SQL，不能回退用容器名或compose service别名。绝不连接`data-test`现役mysql、生产19.10:3306或其它TCP端点；客户端只在该scratch容器内以固定UNIX socket工作。

## 4. SQL本身必须当可执行代码

SHA/CRC只能证明传输与已有档一致，不证明SQL安全。mysqldump包含DDL、可执行版本注释与会话设置；不能只查`DROP`/`\!`字符串后宣称安全，也不能先运行SQL再评估对象集。

建议双重边界：

1. 在PVE/target私有进程内以严格、受限SQL词法解析确认固定`nacos_prod`、12个预期InnoDB BASE TABLE、当前无view/routine/event/trigger；仅接受本次mysqldump已审语法。未知statement、DELIMITER变化、其它schema、用户/权限/plugin/UDF、文件导入导出、全局SET等拒绝本轮，不“跳过不支持语句”来凑导入成功。旧`sql_snapshot.parse`会忽略若干非CREATE/INSERT语句，**只能用于内容比较，不能原样当SQL安全白名单**；版本注释中的SQL也要检查，不得作为普通注释直接丢掉。
2. scratch root仅bootstrap、读回隔离变量和查询基线。更收敛的导入使用本次新建的临时import账号，仅给`nacos_prod.*`确需CREATE/DROP/ALTER/INDEX/SELECT/INSERT/UPDATE/DELETE/REFERENCES/LOCK TABLES等，不给全局ALL/FILE/SUPER/SYSTEM_VARIABLES_ADMIN/CREATE USER/PLUGIN等。当前无programmable对象，不授其创建权。若实际dump需要超出权限，停止审查，不能自动升root导入。

客户端固定`--protocol=socket --binary-mode --local-infile=0 --batch`，非交互STDIN，不启pager/tee/source命令、不以host shell解析SQL。`--binary-mode`在非交互输入下禁绝大部分mysql本地命令，可防`\!`等命令执行，但仍保留charset/delimiter，不禁服务端SQL，不能替代上述隔离与授权。[MySQL客户端binary-mode](https://dev.mysql.com/doc/refman/8.4/en/mysql-command-options.html#option_mysql_binary-mode)

原镜像为8.4.5，不使用8.4.6才增加的`--commands`等选项来假装防护。任何mysql参数应先以该缓存镜像原生命令核支持；此前mysqldump connect-timeout不兼容的教训同样适用。

不要使用`--force`继续错误语句；导入客户端/解压任一非0整轮失败，stderr只在私有缓冲分类，不输出含SQL片段的原文。设置总超时与连接失败门槛；停止只限本次精确container，不能kill现役mysqld或清生产锁。

## 5. 12表、内容与持久性验证

导入前scratch只允许初始化系统库及本次由root预建的空nacos_prod；保存新root/import身份的非敏感基线，不导入MySQL系统账号。

期望内容从**本份备份**生成，而不是重新读线上Nacos或修改现役库：

- 数据库集合精确；12表集合、列名/顺序/类型/nullable/default、主键/唯一索引/普通索引、engine/charset/collation按支持语法规范化比较。仅列名与表数不足以证明完整结构；SHOW CREATE TABLE与dump字面差异只允许已审默认表示归一化，未知差异停止，不忽略约束。
- 对每表逐列按二进制安全表示比较NULL/空串/字节、无序行multiset计数与hash；hash仅私有进程内，公开只报告行数和`all_columns_digest_match`。不得输出config正文、auth password hash、用户名/角色关联、dataId或内容hash。
- namespace/config主记录、tags/beta/历史及users/roles/permissions等都纳入；空表也要证明为空，不能因为当前配置条目少就只比总count。授权用户hash与权限关联完整比较，不重设源身份、不启动Nacos尝试认证。
- `CHECK TABLE`结果与隔离变量再次读回；root/import帐号依然仅scratch新身份，Nacos库内认证元数据是恢复对象，不能与MySQL bootstrap root密码混淆。
- 若主AI实施窗允许，仅对该专用scratch容器一次正常restart，持同一新data目录，重验ready、变量、12表与内容digest不变。不得重启VM210或其现役服务。无需为这份小样本增加并发/负载测试。

原逻辑比较器可复用其NULL/HEX/长度前缀与multiset摘要思路；完整SQL安全检查与结构比较必须独立补足。真实schema不支持时报告具体类别，不改真实SQL/实体或关闭约束来通过。

## 6. 清理与失败处理

在开始前生成本次对象manifest：targetVM210、nonce、containerID/name/imageID/labels、允许目录与dev/ino、临时secret文件身份、原4容器保护基线。清理只依manifest，不扫描所有restore容器或通配删目录。

先核专用容器ID/owner/Mounts→正常stop→有界等待→remove该ID；若无法确认停止，不删其data目录，不使用对现役的force/lazy/unlock。再确认该容器不再引用本次目录，按精确白名单/无symlink删除spool/data/secret及本次脚本，拒任何额外对象并报告。需要递归清scratch MySQL数据树时必须以已验证nonce根dirfd为界、拒symlink/挂载点越界，不用宿主路径字符串的宽泛`rm -rf`。

成功或失败都尝试清理自己对象；确认清理完成再标cleanup passed。失败时可保留受控最小诊断，但含恢复数据/密码的残留不能在普通报告中曝光，也不能把残留当成功清理。PVE原备份、manifest/receipt、备份timer与retention、原11全VM历史档全部不动，不prune备份。

最后重查现役4容器ID/PID/StartedAt/health/挂载与备份timer enabled/next-run等原状态保持；只读报告QA容器消失、QA目录/秘密无残留。不重新跑SQL导出或备份来补证。

## 验收和时间记录

计划至少分四项记录：源档fresh身份/传输校验，scratch实际隔离与新凭据，12表结构及完整内容恢复（和获准restart），清理及现役保护。每项有目标、UTC与Asia/Shanghai时间、退出码、比较布尔、失败类别和限制；普通证据不含SQL、凭据、敏感值或其摘要。

分别记录传输、初始化、导入、比较、restart、清理耗时和总耗时。**恢复时间只针对本3301B/12表小Nacos库、现有缓存镜像与已运行VM210**；没有模拟整机/磁盘故障，没有还原真实业务schema，也没有获批业务RPO/RTO。可证明该档具备当前小样本的可恢复性，不能把结果改写为全部原38项/6REC或正式整体灾备均通过。

当前状态：设计完成，等待主AI审核并在批准对象/资源门禁下实施。没有服务器操作或新的恢复passed证据。
