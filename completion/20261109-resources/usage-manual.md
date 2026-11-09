# 统一资源目录使用手册

更新：2026-11-10，Asia/Shanghai。用户选择正式/测试共用同一台资源服务器和同一个目录。**VM280 NFS与230/240真挂载、权限/跨机读写已通过；仅280受控重启约30秒与fsync canary持久性通过，两client挂载恢复，未重启running。** 这里只提供人工操作示例，不自动运行任何命令；不启Java、不迁入旧资源文件、不启HTTP，也不扩展当前正式DB/Nacos自动备份。

## 路径和身份

| 位置 | 用途 |
| --- | --- |
| VM280 `192.168.19.80` | 统一资源服务器；2vCPU/2GiB，32GiB系统盘＋100GiB独立数据盘 |
| server `/srv/resources` | 唯一共享文件系统，UUID `57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b`；NFSv4伪根fsid0 |
| VM230 `192.168.19.40` | 正式运行基础，客户端挂载目标`/mnt/resources` |
| VM240 `192.168.19.45` | 测试运行基础，同一个客户端挂载目标`/mnt/resources` |
| remote mount source | `192.168.19.80:/`；不是`19.80:/srv/resources`，伪根已经对应server目录 |
| 文件运行身份 | 两机`finger`保留UID999/GID989，追加`resources`附属组GID2980 |
| 240 `/mnt/dell-artifacts` | 原有独立用途，保持原状，不能覆盖成新共享挂载 |

管理员仍通过`ub`与既有SSH密钥登录，只有必要管理动作使用sudo；不拷客户端私钥。NFS只允许230/240的精确IP与TCP2049，root_squash保留；没有SMB、Docker文件服务、上传HTTP或图片URL。资源目录不按prod/test划分，双方对同一路径的更改会立即影响另一方。不要单查某个环境就认定文件孤立或可删除。

## 使用前先确认真挂载

下面命令在**对应客户端**执行；本次已实际验收，但每次故障恢复/新会话写入前仍应核真挂载，不能用历史成功代替当次检查。

```bash
hostname
id finger
systemctl is-active mnt-resources.automount
sudo systemctl start mnt-resources.mount
findmnt --mountpoint /mnt/resources -t nfs4 -o TARGET,SOURCE,FSTYPE,OPTIONS
sudo python3 -I -B /opt/dell/resources/guard.py --role client-230
# VM240改用 --role client-240；不要把两个角色写成同一个hostname。
```

`automount`激活只是本地按需挂载入口，**不是NFS已成功挂载**。`systemctl start mnt-resources.mount`真正建立NFS后，findmnt的合法stack可以同时有`systemd-1` autofs与唯一真实`192.168.19.80:/` nfs4；上例用`-t nfs4`过滤，实际NFS应为vers4.1、proto=tcp、hard及nodev/nosuid/noexec；guard还验证主机/身份/附属组。`findmnt --mountpoint`本身不会触发autofs，不能当触发器。`/mnt/resources`存在或`mountpoint`只看见autofs都不能替代这一步。

## 以非root身份操作文件

跨机验收通过后，普通文件操作使用`finger`。不要用root直接往挂载根写文件，也不要chmod777来消除权限错误。下面示例只在管理员已批准的专属临时目录上使用；将`<唯一已登记ID>`替换成实际唯一ID，不要直接照抄占位符。

```bash
# VM230：确认真NFS与guard后，由finger创建本次专属fixture。
sudo -u finger sh -c 'umask 0002; mkdir /mnt/resources/acceptance-<唯一已登记ID>; printf "%s\n" "resource-share-check" > /mnt/resources/acceptance-<唯一已登记ID>/from-230.txt'

# VM240：用同一ID读回并创建第二个文件。
sudo -u finger cat /mnt/resources/acceptance-<唯一已登记ID>/from-230.txt
sudo -u finger sh -c 'umask 0002; printf "%s\n" "resource-share-check-back" > /mnt/resources/acceptance-<唯一已登记ID>/from-240.txt'

# VM230：读第二个文件，再精确清理自己这两个fixture文件与空目录。
sudo -u finger cat /mnt/resources/acceptance-<唯一已登记ID>/from-240.txt
sudo -u finger rm -- /mnt/resources/acceptance-<唯一已登记ID>/from-230.txt /mnt/resources/acceptance-<唯一已登记ID>/from-240.txt
sudo -u finger rmdir -- /mnt/resources/acceptance-<唯一已登记ID>
```

不要对共享根执行`rm -rf`、批量chown或递归权限修复。default ACL与setgid让新文件使用共享组；创建程序主动用0600时，不能假定default ACL会强制扩大它的权限，应该从应用的文件创建模式排查。新登录/新进程才能取得追加的附属组；本轮没有Java业务需要为此重启。

业务文件应按实际业务定义目录与命名，避免同名覆盖，写入时先同目录临时文件再原子rename。涉及数据库引用的文件删除需同时核正式和测试两边引用、未完成上传、后台任务及缓存；本次NFS部署没有提供自动“孤儿文件”清理器。

## 容量与日常健康

100GiB是虚拟数据盘容量，ext4元数据等使`df`可用值略低；不能把T630 store剩余约6.7TiB当成这个共享目录已经有6.7TiB。管理员在280执行：

```bash
findmnt --mountpoint /srv/resources -o TARGET,SOURCE,FSTYPE,UUID,OPTIONS
df -hT /srv/resources
df -i /srv/resources
sudo systemctl is-active srv-resources.mount dell-resources-firewall.service nfs-server.service
sudo exportfs -v
cat /proc/fs/nfsd/versions
```

应保持实际UUID、ext4、单一fsid0导出与两个精确客户端；版本只启4/4.1。客户端可运行`df -h /mnt/resources`，但这会真正访问NFS，server失联时可能等待。大目录统计可能产生负载，应在空闲窗口限制到已知业务子目录；不要用全盘扫描当每分钟健康探测。

[00:20最终只读后检](final-postcheck.json)已确认19.80:9100被实际抓取，16/16targetsUP、资源5项服务指标UP；这是带时点健康状态，不保证未来每次检查仍相同。基础健康不能替代资源内容备份或应用上传下载验收。

## NFS故障与防止落到根盘

`hard`挂载会在server故障时持续重试，进程I/O可能长时间等待；这是避免软超时导致静默数据损坏的选择。mount unit的初次30秒超时不等于已挂载NFS的I/O会在30秒返回。不要改`soft`、懒卸载、强卸载或移走目录来绕过错误。

1. 先确认280/PVE网络、磁盘和NFS状态，再核client findmnt与相关unit；保留错误元数据，不清日志伪装恢复。
2. server必须是真数据UUID挂载，不能在数据盘缺失时往`/srv/resources`根盘下层创建文件。客户端未挂载下层目录为root0555，finger不应能写入；automount占位不是可写替代卷。
3. 若应用已在写入，先按明确维护窗口排空/停止这些依赖进程，再处理挂载；本期没有Java业务，不能因此重放旧publisher或启动历史五服务。
4. 修复已确定的网络/盘/服务原因后，再在单个client启动真实mount、执行guard和本次专属双机fixture；先验一机再验另一机。不要删除或覆盖已有文件来“验证”挂载。
5. 未来Java应配置Requires/BindsTo/RequiresMountsFor与前置guard、共享路径ReadWritePaths及UMask0002；目前未来drop-in只是候选，未安装/未启业务。

root_squash防止普通UID0请求直接取得server root，但AUTH_SYS不是密码认证或加密。批准client的管理员能够切换UID来代行文件操作；信任边界是这两台来宾的管理权、网络身份和权限，不是防恶意client root的强隔离。

## 添加下一台running及模板建议

当前只授权230/240访问，不应把21/24或整个19网加入export。新增running需要主AI确认VMID/IP/预算后，逐层完成：

1. 为新实例生成唯一CloudInit hostname/MAC/机器身份/SSH host key并登记真实静态IP；模板克隆本身不自动取得资源权限。
2. 核新实例finger身份与resources GID2980无冲突，保原primary UID/GID，只追加固定附属组；如数字冲突先停，不强改无关系统组。
3. 审核资源server exports精确client、新实例到280 TCP2049的PVE bridge peer、server专属输入白名单；这些是独立层，缺一不可。保PVE无L3/noNAT和现役LAN/WG边界。
4. 当前公开policy/renderer/guard/installer固定只接受230/240两个client角色；新running必须先审核并同步这些严格角色/IP白名单、对应离线负例及安装器固定映射。**不能只改exports就用现有安装命令安装第三台。** 再仅在空`/mnt/resources`安装经审的mount/automount与policy，默认不启动业务；显式激活、核真NFS与非root双机fixture，再纳入监控/启动顺序。
5. 对未来业务另行安装挂载依赖drop-in，不让业务在共享失效时写本机根盘。同步机器合同与验收证据，实际测试后才能签新client成功。

**模板可以将来预装nfs-common、工具与disabled挂载候选，clone后按真实IP登记/授权再激活；本次没有授权或实施修改9001/9010/9011模板。** 模板不要主动挂载共享、带NFS写入fixture、继承运行实例固定IP或拷贝任何业务文件。不得将本页步骤当成直接扩权模板/新增client的授权。

## 应用接入尚未实施

Finger文件模块未来可另审将`file.upload.path`设为`/mnt/resources`，但本次**没有修改实际配置/Nacos/profile，也没有启动Java**。资源目录挂好不会自动改变上传路径；现阶段没有HTTPdomain或公开图片URL，不应把NFS路径拼成浏览器URL。未来若启HTTP图片，只公开经业务授权的子目录并设计访问控制，不将整个共享根直接公开。

Puyu当前images存放于MySQL并通过应用权限下载，NFS不会自动把它们迁成磁盘文件；本次没有为此迁数据、改应用连接或Nacos。要改变存储模型、历史数据迁移或权限下载链必须另做设计与授权，不能只改一个路径视为完成接入。

## 数据保护范围

共享资源未纳入当前自动备份；现行自动任务仅正式VM200/nacos_prod逻辑SQL，数据库备份不包含这些文件。NFS共用目录、RAID与T630同机存储均不能提供独立灾备；误删、覆盖、磁盘/整机故障的文件恢复尚未验证。正式上传资源开始承载真实数据前，应另定文件保留、备份目的地、权限与数据库/文件一致性点，明确授权后实施；本页不自动扩围或启用旧whole-VM任务。

实际回执：[server installed](server-installed.json)、[存储初始化](storage-initialized.json)、[独立native验收](native-acceptance.json)、[仅280受控重启](reboot-exercise.json)、[最终只读后检](final-postcheck.json)。本页命令示例仍不是一份新执行证明，不应为刷新日期无故重跑。

native验收的专属fixture实际以finger UID999/附属组2980完成，目录2770、数据文件660，跨机读回/追加/删除和fixture清理通过；两client UID0清空附属组时写入被拒，240仅新mountunits短停后guard拒绝/未写根盘、恢复后通过。[首轮失败](native-first-attempt.json)保留：当时以umask0022执行并在metadata断言停止、专属对象清理，未捕获旧文件mode，不把原因追认为已独立确证；后续明确在客户端fixture进程提前应用已批准umask0002，不改server或业务服务配置来凑通过。

重启只覆盖新VM280的正常OS重启与fsync小canary，约30秒；不是物理断电、客户端OS重启或业务RTO。两台running未重启，短停/恢复的仅新NFS挂载；PVE bootID保持。
