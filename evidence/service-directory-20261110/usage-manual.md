# 服务导航使用与维护手册

更新：2026-11-10，Asia/Shanghai。实际地址：**[http://192.168.19.30:9080/](http://192.168.19.30:9080/)**，位于VM220 `publish-service`。不需要账号密码。当前发布提交为 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`，初始14个入口。按用户最新要求使用HTTP、移除顶部“个人内网 / 服务导航”栏，缩紧标题/边距并采用全宽布局。TLS和登录凭据均不加载，无需账号密码。最新验收看[统一内网HTTP交付](../internal-http-20261110/README.md)；[14:26链接更新](../internal-http-20261110/navigation-links-applied.json)与[14:28最终后检](../internal-http-20261110/final-postcheck.json)已通过，保留此前dd阶段的浏览器布局实证。此前HTTPS及63b提交只作[首次历史](README.md)。

## 首次访问

连接受信LAN `192.168.21.0/24`，或已有WireGuard `10.66.66.0/24` 客户端后打开上述HTTP地址。9080仅允许这两个来源网段及VM220本机；其它19网来宾不会因目录可见而获得访问许可。PVE不提供旧DNAT转发。

当前导航不使用HTTPS，不需要接受自签证书或核证书指纹。自建内网应用按最新要求默认HTTP；FileBrowser已改HTTP并保留原账号密码认证，PVE/iDRAC内置管理HTTPS本轮保留。导航免登录不提供SSO，也不修改目标服务账号密码。

### 首次HTTPS证书说明（历史，当前已不用）

首次部署曾使用[公开自签证书](tls.crt)，指纹为：

```text
7B:CF:87:90:17:E9:6B:D7:09:E9:86:A0:74:C7:01:B4:AA:93:12:10:97:77:D8:2B:51:55:3C:2E:81:EB:25:FC
```

原TLS首访、CA核验及指纹只解释旧验收，不能照搬成当前HTTP访问步骤。旧证书/私钥仅留未启用历史，现役unit不再配置TLS LoadCredential，也不加载应用登录凭据。没有修改系统全局truststore或其它服务证书。

## 页面操作

1. 打开页面即可看到入口列表。左侧选分组，或使用搜索框匹配名称、地址、说明；环境下拉可选全部、正式、测试、共享、管理。
2. 点击入口在新标签页打开目标网站；链接带 `noopener noreferrer`。请求由你的浏览器直接发到目标，不经导航代理；目标可能继续要求自己的登录和网络权限。
3. 使用“复制地址”复制到本机剪贴板。浏览器拒绝剪贴板权限时可手动选择显示地址复制；导航不会保存剪贴板内容。
4. 没有匹配项时使用“清除筛选”恢复列表。工具栏刷新按钮与错误提示的“重新读取”只重新GET目录，不检查目标健康、不启动服务。
5. 刷新失败会提示错误并保留上次已读条目。先恢复导航自身连接再重试，不能把保留条目解释成目标当前在线。

页面是服务入口目录。环境、说明、显示状态来自维护清单，均不是实时监控结果；实时指标到Grafana/Prometheus查看。没有新增、修改、删除、登录或退出按钮，没有浏览器状态写回。

## 初始入口

| 分组 | 入口 | 地址 |
| --- | --- | --- |
| 基础管理 | 服务导航 | http://192.168.19.30:9080/ |
| 基础管理 | Proxmox VE | https://192.168.21.22:8006/ |
| 基础管理 | OpenWrt路由器 | http://192.168.21.1/ |
| 基础管理 | iDRAC | https://192.168.21.21/ |
| 工作工具 | Penpot | http://192.168.19.50:9001/ |
| 工作工具 | FileBrowser资源管理 | http://192.168.19.80:8080/ |
| 开发服务 | Nexus制品仓库 | http://192.168.19.31:8081/ |
| 开发服务 | 测试Nacos | http://192.168.19.20:8848/nacos/ |
| 开发服务 | 正式Nacos | http://192.168.19.11:8848/nacos/ |
| 家庭媒体 | OMV NAS管理 | http://192.168.19.60/ |
| 家庭媒体 | Jellyfin | http://192.168.19.60:8096/ |
| 运维监控 | Grafana | http://192.168.19.70:3000/ |
| 运维监控 | Prometheus | http://192.168.19.70:9090/ |
| 运维监控 | Alertmanager | http://192.168.19.70:9093/ |

此表是提交时的目录快照，没有逐一请求或验收目标服务。MySQL3306、SSH22及NFS/SMB等使用专用客户端，不能登记成HTTP地址。各入口原权限继续生效。

## 实测证据与操作边界

当前HTTP/全宽布局与FileBrowser HTTP链接以[最新统一内网HTTP交付](../internal-http-20261110/README.md)为准；[14:26导航应用](../internal-http-20261110/navigation-links-applied.json)及[14:28最终后检](../internal-http-20261110/final-postcheck.json)通过。以下dd阶段的布局实测与截图见[此前布局记录](../service-directory-http-20261110/README.md)；[HTTP应用](../service-directory-http-20261110/applied.json)和[全宽布局应用](../service-directory-http-20261110/layout-applied.json)已分别记录切换，原保护服务保持、没有修改防火墙或其它服务。

[dd阶段浏览器布局回执](../service-directory-http-20261110/browser.json)验证1920px桌面主区域x0/宽1920、390px手机无横向溢出，两种视口均无顶部栏、展示14条入口且没有表单；[桌面截图](../service-directory-http-20261110/desktop.png)和[手机截图](../service-directory-http-20261110/mobile.png)是dd阶段布局截图；d56只更新FileBrowser链接为HTTP。[14:13最终后检](../service-directory-http-20261110/final-postcheck.json)确认HTTP200/14条、自身链接HTTP、写请求405、无HSTS；unit没有TLS参数/凭据指令，运行时凭据环境和目录均不存在，五文件与dd提交摘要一致，旧服务保持，16targets及导航指标均UP。只重启导航，未改其它应用、防火墙或路由。该浏览器回执只签上述布局与匿名展示，未重签所有按钮或目标服务可达性。

以下为首次HTTPS阶段历史，不代表新布局回归：[旧浏览器回执](browser-acceptance.json)确认当时页面匿名展示14条、搜索Penpot只剩1行、复制地址出现“已复制”提示、390px手机视图无横向溢出，外链href及 `target=_blank` / `noopener noreferrer` 属性正确；页面资源只来自导航自身。可看[桌面截图](desktop.png)与[手机截图](mobile.png)。新窗口点击自动化曾无响应并重开会话，未验收真实pointer跳转，未探测或登录各目标服务，也未据此验收所有按钮。浏览器测试只在隔离会话忽略自签提示，Mac curl另用专属CA验证200；系统全局CA没有变更。

[仅导航重启](service-restart.json)后，app PID变化、14条匿名清单和文件字节保持，原保护服务frame不变；自有nft原子重应用也未重启app。[最终后检](final-postcheck.json)确认13来宾/3停止模板、16targets全UP、PVE forwarding全0，导航unit指标为1。本次没有重启VM、Java、Penpot或Nexus。

## 管理员只读排障

先按[人工操作手册](../../19-manual-operations.md)严格SSH到VM220，核hostname和19.30；不要去PVE或别的VM执行应用命令。以下只检查导航自身：

```sh
systemctl show dell-service-directory.service --property=ActiveState,SubState,User,Group,ReadWritePaths,ProtectSystem,NoNewPrivileges
systemctl show dell-service-directory-firewall.service --property=ActiveState,SubState
ss -lnt 'sport = :9080'
sudo nft list table inet dell_service_directory_input
```

运行身份应为 `servicedirectory` UID/GID2001，OS用户只供隔离进程，没有可用于页面登录的应用身份。原生服务使用Python3标准库，无pip/npm/Docker运行依赖；内存上限128MiB、TasksMax32，root-owned release对服务用户只读。不要为了消除失败把service改成root、添加写目录或打开其它来源。

从管理机使用HTTP GET检查导航自身：

```sh
curl --fail --silent --show-error http://192.168.19.30:9080/health
curl --fail --silent --show-error http://192.168.19.30:9080/api/services
```

使用GET；`curl -I`发HEAD，会按设计返回405，不能据此判断宕机。`/health`仅报告导航进程自身，不校验14个目标。当前HTTP不使用`--cacert`或`-k`；导航自身无需TLS核验。

无法建立连接时先核客户端来源、WireGuard/路由及9080监听；若浏览器仍强制跳到HTTPS，先核地址与旧HTTPS站点记录，使用当前HTTP地址；页面空或报清单错误则核部署版本和manifest摘要。不要导出完整环境或TLS私钥，不打印发布私钥，不重启Java/Nexus/Penpot来修导航。

## 清单修改、升级与回退

唯一维护源是 `bkcode/deploy` 项目的 `service-directory/services.json`。管理机工作树为 `/Users/yangzhaohui/work/www/finger/finger-master/projects/deploy`；发布机源码约定路径为 `/var/www/finger/finger-master/projects/deploy`，该路径登记不代表复制了整仓库或server Git key已安装。[源码Git记录](source-git-state.json)明确：导航源码已在本机main提交，**未推到GitHub**。任务前本机已领先远端main 4条既有用户提交；本次只提交自身8文件，未顺带push、rebase、amend或force。观测远端main仍为 `593069eb54a723ee0e63f85b937b9981b39ac1ec`，不能用git pull旧main覆盖现役源码。后续更新先审查精确提交和推送范围，再从该提交导出运行文件；Dell文档仓库的独立push不代表deploy源码已推。

本任务前3条本机提交依次为：首次HTTPS `63b8c08`、HTTP切换 `c141506ec6a59dd7f123cabc00f099f1cf87d4e1`、全宽布局阶段 `ddccc2b98bbb3dfdc9de649443dc3fcdc7b4860f`，另加FileBrowser链接HTTP提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`，合计4条任务提交，同样只在本机提交，未push。`63b8c08` 是首次HTTPS历史版本，ddccc2b是布局阶段版本。现役固定五文件release在 `/opt/dell/service-directory/releases/d56cae553bf95ce0e2c3fe8f258a2f99389aae7c/`，不是源码工作树。

1. 在项目Git清单中改名称、URL、分组、环境、说明或enabled，保持唯一规范UUID与严格schema；最多100条/512KiB，仅绝对HTTP/HTTPS。不要写口令、token、签名链接或数据库连接串。
2. 在项目根运行 `python3 -B -m unittest discover -s tests -p test_service_directory.py -v`，复核目录和Web文件后提交新的精确SHA。
3. 维护窗口内将该提交的固定五个文件导出为新的root-owned release，核SHA256并更新 `/etc/dell-service-directory/manifest.json` 与导航unit的精确release路径；保留旧release以供回退。先审查systemd差异与原生校验，再只重启 `dell-service-directory.service`。
4. 新启动只读加载清单一次；仅浏览器刷新不能加载磁盘上的新清单。重启后核匿名200/14或预期条数、写请求405、摘要和原保护服务不变，再更新交付记录。
5. 回退也只切回已核的旧release与对应manifest/unit，再只重启导航。安装器有首次安装碰撞门禁，不可当日常升级或回退脚本盲重放；原 `dell-publish` / stage / activate / rollback 业务链不参与此导航维护。

独立重启的人工命令（完成上述版本与影响检查后，在VM220执行）：

```sh
sudo systemctl restart dell-service-directory.service
systemctl is-active dell-service-directory.service
```

配置目录为 `/etc/dell-service-directory/`，现役使用manifest与专属input.nft。HTTP启动使用显式 `--http`，没有TLS或登录凭据的LoadCredential。旧 `tls.crt` 与root-only `secrets/tls-key` 只留未启用历史，不加载、不复制到release/Git或源码工作树；其它服务的HTTPS不受影响。

本服务没有应用账号密码、数据库或可写JSON运行状态，也没有应用数据可做CRUD导出。自动备份仍只限正式MySQL/Nacos，导航不扩围；220发布私钥继续只留220，禁止whole-VM备份/快照导出。Java停用、publisher冻结、Nexus221独立与Penpot等待用户push两条改造的边界保持。
