# FileBrowser已移除，资源服务仅使用NFS

2026-11-10，Asia/Shanghai。用户明确允许移除FileBrowser；本次只处理VM280，不操作Nexus，也未执行Nexus回退。

现役安装路径/opt/dell/filebrowser、/etc/dell-filebrowser、/var/lib/dell-filebrowser、/var/lib/dell-filebrowser-manager均已移除，两服务单元为not-found/inactive，8080关闭。UID2000专属用户因未持有共享文件而删除；共享resources组GID2980保持。

原程序、配置、账号数据库和凭据集中移动到VM280本机/root/dell-filebrowser-removed-20261110，父目录root700、journal600。未输出/导出密码，未移动或删除/srv/resources任何文件；这不是Git内的恢复包，也不是自动备份任务。原先仅停用阶段的/root/dell-filebrowser-retired-20261110已移入新归档prior-retirement子目录。

## 当前使用方法

资源共享为192.168.19.80:/，仅已登记的192.168.19.40/45两客户端；正式230与测试240共用/mnt/resources。NFSv4.1、root_squash、原权限/防火墙/挂载守卫保持，没有新增浏览器文件管理入口。现有NAS媒体服务不在本次范围。

服务器可用已有ub SSH会话只读检查：

```sh
sudo -n python3 -I -B /opt/dell/resources/guard.py --role server
systemctl is-active nfs-server.service dell-resources-firewall.service
```

运行机只读检查：

```sh
findmnt --mountpoint /mnt/resources -t nfs4
```

本次未重启NFS或客户端。程序写共享文件前仍必须检查真实NFS挂载，不能把未挂载底目录当共享盘写入。日后恢复FileBrowser需单独确认；先核UID2000未被占用与归档完整性，不直接重跑旧fresh-init/安装器，不将归档凭据贴进聊天或提交Git。

[卸除回执](removal-result.json)、[服务器只读后检](final-postcheck.json)、[两个客户端真实挂载后检](clients-postcheck.json)记录本次范围。此前停用/负测/写入验收仍为各自历史，不覆盖为本次全新恢复演练。
