# FileBrowser Quantum native管理页

用户最新要求自建内网应用默认HTTP，PVE/iDRAC内置管理HTTPS保留。FileBrowser入口改为 **[http://192.168.19.80:8080/](http://192.168.19.80:8080/)**，固定官方native v2.1.4-beta；HTTP切换原生验收及14:28最终后检已通过，以[内网HTTP交付](../../../evidence/internal-http-20261110/README.md)为最新状态。只移除本应用TLS，原resources/admin密码、认证、权限、固定JWT、marker、UID/GID、ACL与NFS保持。

[HTTP原生回执](../../../evidence/internal-http-20261110/filebrowser-applied.json)验证两个旧账号原密码新登录及原scope/权限、匿名401/日常设置403，JWT/marker/UID/GID/state与NFS身份保持；[最终后检](../../../evidence/internal-http-20261110/final-postcheck.json)确认16targets、资源六服务和HTTP健康UP。[HTTP浏览器登录](../../../evidence/internal-http-20261110/filebrowser-browser.json)已用原resources口令进入资源页，测试会话与临时认证资料已清。原06:12 [HTTPS部署/原生fixture/浏览器/重启](../../../completion/20261110-filebrowser/README.md)留为首次历史，不能代签当前HTTP；旧证书/私钥只留未启用历史，系统CA不变。完整[当前使用手册](../../../completion/20261110-filebrowser/usage-manual.md)，基础NFS见[资源交付](../../../completion/20261109-resources/README.md)。

## 固定合同

| 项目 | 实际合同 |
| --- | --- |
| 产物 | 官方`gtsteffaniak/filebrowser` v2.1.4-beta Linux AMD64，固定SHA见[upstream.lock.json](upstream.lock.json)，不自动升级 |
| Binary | `/opt/dell/filebrowser/releases/v2.1.4-beta/filebrowser`，native，不安装Docker/Podman |
| 管理面 | HTTP19.80:8080（切换已验收），仅LAN21/24、WG10.66/24及本机；独立`inet dell_filebrowser_input`，不改NFS表/PVE/GW路由 |
| 共享 | 唯一`/srv/resources`，继续同目录供230/240挂`/mnt/resources`，不迁旧文件 |
| 身份/权限 | Linux filebrowser UID2000/primary resources GID2980，UMask0002、文件660/目录2770；source private，日常view/download/create，modify/delete/share/提权拒绝 |
| 账号 | 日常resources；维护admin有完整权限，不把日常禁删等同admin或OS绝对禁删 |
| 状态/凭据 | `/var/lib/dell-filebrowser` 2000:2980/700，DB/cache离共享；config公开，JWT/初始化认证按原LoadCredential与marker规则保持，TLS凭据不再加载，值不进Git |
| 初始化 | `/etc/dell-filebrowser/bootstrap.complete` root0644；成功后不再注入初始化管理员口令，JWT每次加载 |
| 资源 | VM280原2CPU/2GiB内，服务CPUQuota100%/MemoryMax384M；无新VM/业务Java/公开图片入口 |
| 备份 | 程序metadata自动备份disabled；资源/state/secret不扩入现行正式DB/Nacos备份 |

此tag名称含beta，不能称stable；本次选用原因是官方v2.0.2未含GHSA-892f-9h5p-mfc8修复、v2.1.0稳定release地址404，固定已含修复tag。新版本发布后另审兼容与安全，不使用浮动latest/stable替换。官方安全来源与维护流程见[手册](../../../completion/20261110-filebrowser/usage-manual.md)。

## 本目录工具

- [prepare.py](prepare.py)：无参数固定renderer，返回6项公开文件，manifest给十六进制SHA；不联网/安装/生成secret。配置是JSON兼容YAML，精确scope/HTTP/auth/defaultPermissions与日志边界不接受任意覆写。
- [test_prepare.py](test_prepare.py)：纯测试包括锁定配置、禁危险变更、argv不含secret、首次/后续启动口令规则、精确systemd POSIX ACL、单自有表事务。代码通过不替代native证明。
- [install.py](install.py)：主AI受控安装器，实施以实际回执/目标SHA为准；不能为刷新日期重放初始化或强制改密。
- [DESIGN.md](DESIGN.md)：固定native设计与最初收口范围，含待验证的原始条件；当前实际状态以本页及新completion回执为准。
- [monitoring](monitoring/README.md)：旧专属CA/六服务合同与采集代码来源保留历史；当前健康改HTTP、命名filebrowser-http-health并移除ca_file，已由新回执验证；旧实际安装见[监控回执](../../../completion/20261110-filebrowser/monitoring-installed.json)。不新增Promtarget或外发测试消息。

初始launcher曾因把ACL mask误当组权限而拒绝合法systemd凭据；仅兼容root0:0 dir550/file440、ACL恰named UID2000只读且无其他用户/组/write，保留原owner-only分支。运行时凭据没有chmod/chown，失败及[修复](../../../completion/20261110-filebrowser/acl-compatibility.json)保留。API/NFS首试的root_squash测试前置错误也保留，不将它改写成finger权限故障。

## 首次HTTPS阶段实际通过范围（历史）

[native验收](../../../completion/20261110-filebrowser/native-acceptance.json)statuspassed/fixture_cleaned；日常delete/override/edit/share/提权403，匿名资源401，NFS/原服务/PID/挂载状态保持。[浏览器](../../../completion/20261110-filebrowser/browser-acceptance.json)只签真实登录、四文件列表、观察到href后的深链PNG渲染；自动点击未导航，不签全部按钮或pointer导航。

首次公开自签证书[tls.crt](../../../completion/20261110-filebrowser/tls.crt)只留历史，当前HTTP无需证书，旧私钥不加载；系统truststore未改。FileBrowser是私有管理页面，Finger上传路径未接、Puyu数据库images未迁出、Java未启，不是Nginx业务图片服务或公开静态域名。
