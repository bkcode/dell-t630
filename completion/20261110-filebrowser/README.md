# FileBrowser Quantum资源管理页交付

完成验收：2026-11-10T06:12:08.767369+08:00。用户在选型后明确要求补充管理服务与对应文档，本期只扩展现有VM280，不增加虚拟机。

- 入口：**https://192.168.19.80:8080/**，仅受信LAN21/24、WG10.66.66/24和本机；其他19peer不获Web权限。真实外网WG客户端本期未复测，不把规则许可冒签端到端。
- 日常`resources`可浏览、预览、下载、新建目录/上传；删除、覆盖、编辑、分享与权限提升直接API均403。维护`admin`为完整应用管理员，不将它称为无删除权；资源source默认private。
- 数据仍为server `/srv/resources`，两running同`/mnt/resources`；Web进程2000:2980，新文件660/目录2770，NFS finger999通过组共享真实互读写。
- 采用官方native程序＋systemd，固定`v2.1.4-beta`和官方SHA256；不安装Docker，不修改宿主网络或NFS。配置/公开证书在`/etc/dell-filebrowser`，DB/cache独立`/var/lib/dell-filebrowser` 2000:2980/700；secret仅root700/600与LoadCredential。

直接阅读 **[使用手册](usage-manual.md)**，包括证书核对、账号取用、上传/下载、日常运维、改密与恢复、升级和日志排查。密码只在本机`private/credentials/filebrowser-management-20261110.json`与guest root私有文件；此仓库不保存真实口令/JWT/私钥/数据库/资源文件。

## 验收与边界

[8项验收](acceptance.json)passed。[原生验收](native-acceptance.md)证明API新文件、两机NFS互读/追加/新文件再API可见，匿名401与5项权限负测403，唯一fixture已清。PNG及文本均为本次合成样本，未读写其它业务文件。

[浏览器验收](browser-acceptance.json)证明真实登录、4个样本文件列表与96×96PNG渲染；使用观察到的实际href直接访问，自动点击导航未签收，未冒称所有UI按钮或大文件上传全测。截图仅private，临时加密登录记录/Cookie/会话已清理。

[新app重启](service-restart.json)后admin/resources原凭据仍登录，scope保持；root-owned初始化标记生效，进程不再注入初始口令，固定JWT加载，NFS等旧服务身份不变，未重启VM或两running。[最终后检](final-postcheck.json)15项全真：13来宾/3模板、PVE全forward0、16targetsUP、资源6服务及专属CA HTTPS健康UP，独立Userfilebrowser/私有state/固定binary/精确监听均符合。

当前只提供管理界面，不创建公开图片业务URL、不改Finger/Nacos上传参数、不启动Java、不迁已有资源；Puyu原MySQL存图逻辑不自动改变。资源与此app状态不扩入当前仅正式DB/Nacos的自动备份。原Nexus不合并，模板不修改，Mac外部探针不恢复。

## 版本与过程记录

官方稳定标签2.0.2仍在[GHSA-892f-9h5p-mfc8](https://github.com/gtsteffaniak/filebrowser/security/advisories/GHSA-892f-9h5p-mfc8)受影响范围；声明的2.1.0-stable在实际release API查询404，因此选已发布且修复的[2.1.4-beta](https://github.com/gtsteffaniak/filebrowser/releases/tag/v2.1.4-beta)，不称其为稳定版、不跟随可变latest/stable自动升级。实际大小/官方digest见[upstream](upstream-v2.1.4-beta.json)。管理API已原生验证不回传已知secret值，日志也做了不输出正文的[隐私布尔检查](log-privacy.json)。

[首次启动记录](first-start-diagnostic.json)：mode位门禁误拒systemd命名ACL，按只授UID2000只读的精确ACL修正，未chmod/chown运行时凭据或放宽给resources组；源码及回执保留。首次NFS runner在切finger前读marker被root_squash拒绝，见[native-first-attempt](native-first-attempt.md)；仅修测试顺序，不改服务/ACL/mode。

证书为本地自签，系统全局信任未改；[公开证书](tls.crt)可供核对，不能和私钥混淆。健康检查用专属CA且验证链与IP主机名，不关闭验证。重启/升级与备份恢复、长期安全/负载验证各自独立，本期不扩大签收。
