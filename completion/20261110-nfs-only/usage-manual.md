# NFS资源目录操作说明

2026-11-10，Asia/Shanghai。资源服务现仅提供NFS；FileBrowser网页服务已停用，`http://192.168.19.80:8080/`不再是可用入口。NFS通过操作系统挂载访问，不提供网页登录或HTTP图片URL。

## 当前地址与路径

| 位置 | 路径/用途 |
| --- | --- |
| VM280 `resource-service` | `192.168.19.80`，NFS服务器 |
| 真实数据目录 | `/srv/resources`，原独立ext4卷UUID `57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b`，100GiB虚拟数据盘 |
| NFS远端源 | `192.168.19.80:/`；NFSv4伪根已经指向数据目录 |
| 正式运行基础230 | `192.168.19.40:/mnt/resources` |
| 测试运行基础240 | `192.168.19.45:/mnt/resources` |
| 文件运行身份 | `finger` UID999/原GID989，附属`resources` GID2980 |

正式与测试读取和修改同一个目录，不存在环境副本；误删或覆盖会影响两边。现行exports仅允许230/240两个精确客户端，root_squash保留；没有将Mac、整个21网、WG或任意新机器加入NFS导出。用户通过SSH管理已批准运行机，再操作该机已挂载目录。新增Mac等客户端需要单独登记、核身份并补精确NFS/防火墙/bridge权限，不能用通配符直接放开。

NFS使用现有Linux UID/GID与AUTH_SYS权限，不使用FileBrowser的resources/admin密码。FileBrowser旧账号、state和秘密仅作本机受保护回退材料，不参与NFS认证。

## 操作前确认真挂载

以下命令在230或240执行，属于人工说明，不是本页自动执行：

```sh
ssh -i ~/.ssh/yang_local_rsa ub@192.168.19.45
id finger
systemctl is-active mnt-resources.automount
findmnt --mountpoint /mnt/resources -t nfs4 -o TARGET,SOURCE,FSTYPE,OPTIONS
sudo python3 -I -B /opt/dell/resources/guard.py --role client-240
```

230换IP为`.19.40`、guard角色改`client-230`。合法结果必须包含唯一真实`192.168.19.80:/` nfs4、vers4.1/protoTCP/hard，以及nodev/nosuid/noexec；仅目录存在或看到autofs不代表已挂上NFS。挂载未建立时先由管理员确认服务器健康，再启动对应`mnt-resources.mount`，不能在下层本机目录凑一个可写替代。

日常文件操作使用非root的finger，并让新文件创建进程采用`umask 0002`；不要chmod777、递归chown整个共享根或使用root覆盖权限。可先只读查看已明确需要的子目录，例如：

```sh
sudo -u finger ls -ld /mnt/resources
# 只有明确业务路径后再查看/操作那个子目录。
```

文件写入应使用唯一命名，先在同目录写临时文件再原子rename；删除前检查正式/测试双方引用。NFS未提供自动孤儿文件清理或网页回收站。程序主动0600的文件不会因defaultACL而自动强制扩权，须检查真实创建模式。

## 服务器检查

在280通过原SSH管理身份执行：

```sh
sudo python3 -I -B /opt/dell/resources/guard.py --role server
findmnt --mountpoint /srv/resources -o TARGET,SOURCE,FSTYPE,UUID,OPTIONS
df -hT /srv/resources
sudo exportfs -v
cat /proc/fs/nfsd/versions
systemctl is-active nfs-server.service dell-resources-firewall.service
systemctl is-enabled dell-filebrowser.service dell-filebrowser-firewall.service
sudo ss -lntu 'sport = :8080'
```

NFS导出应只有`.19.40`、`.19.45`和root_squash；版本保持`-3 +4 -4.0 +4.1 -4.2`。FileBrowser两unit应masked且inactive，8080无TCP/UDP监听。资源节点健康检查保留ssh、QGA、exporter、nfs-server、dell-resources-firewall共5项，不再包含FileBrowser HTTP或unit检查。

## 失联、保留与恢复边界

NFS是hard挂载，服务器失联时I/O可能持续等待。先恢复280网络、真实数据卷和NFS，再验证client真挂载；不要改soft、强制/懒卸载、格式化或删除挂载点绕过故障。当前没有Java业务启动，本轮也没有重启running或改变应用上传路径。

FileBrowser旧state仍位于`/var/lib/dell-filebrowser`，原账号/JWT等秘密仍在原受保护位置；只有原unit、健康配置与专属输入表的受保护回退副本位于280的`/root/dell-filebrowser-retired-20261110`（目录700、文件600）。这些材料不在NFS导出内，不应cat到聊天或复制到Git。当前已选择仅NFS，不自动解除mask、重新初始化或恢复网页；如以后明确决定恢复，再审查本轮journal与当前配置后安排单独窗口。

模板本轮未修改。现行自动备份仍仅正式数据库/Nacos，NFS资源文件、FileBrowser state和整机均未加入；共享目录和RAID不能替代独立备份。新增资源业务、HTTP图片访问、应用上传参数或新的客户端，均不因这次停用自动完成。

## 本次实际验证范围

22:49完成FileBrowser停用；22:50新建单次server专属canary，230/240均以finger经真实NFS读回，并检查目录写权限可用，最后精确清理canary；没有client实际写入、没有读取已有业务文件。22:51后检确认NFS原配置SHA保持、5项服务active、FileBrowser指标及8080监听消失。历史双client写入测试见[原NFS验收](../20261109-resources/native-acceptance.json)，不与本次只读测试混记。导航运行部署和VM270最终Prom证明由主AI在统一维护窗口单独补签。
