# 服务导航使用与维护手册

更新：2026-11-10，Asia/Shanghai。实际地址：**[https://192.168.19.30:9080/](https://192.168.19.30:9080/)**，位于VM220 `publish-service`。不需要账号密码。当前发布提交为 `63b8c0873936e94f8483c4f1f8747aedb0180d43`，初始14个入口；本期原生验收、仅导航重启、浏览器预览与最终后检已通过，具体边界以[中央交付记录](README.md)和带时间回执为准。

## 首次访问

连接受信LAN `192.168.21.0/24`，或已有WireGuard `10.66.66.0/24` 客户端后打开上述HTTPS地址。9080仅允许这两个来源网段及VM220本机；其它19网来宾不会因目录可见而获得访问许可。PVE不提供旧DNAT转发。

证书是本地自签证书。首次访问应先核对[公开证书](tls.crt)和SHA256指纹，再按浏览器流程接受该站点证书；本次没有修改全局truststore。若指纹不同，应停下核证书变更记录。公开指纹为：

```text
7B:CF:87:90:17:E9:6B:D7:09:E9:86:A0:74:C7:01:B4:AA:93:12:10:97:77:D8:2B:51:55:3C:2E:81:EB:25:FC
```

在Dell仓库本地可只读核对公开文件：

```sh
openssl x509 -in evidence/service-directory-20261110/tls.crt -noout -fingerprint -sha256 -dates
```

不要将导航证书当作FileBrowser、PVE或iDRAC证书。各站点分别核自己的证书。导航免登录不会跳过目标服务认证，不提供SSO，也不会更改业务账号密码。

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
| 基础管理 | 服务导航（清单名称“服务地址管理”） | https://192.168.19.30:9080/ |
| 基础管理 | Proxmox VE | https://192.168.21.22:8006/ |
| 基础管理 | OpenWrt路由器 | http://192.168.21.1/ |
| 基础管理 | iDRAC | https://192.168.21.21/ |
| 工作工具 | Penpot | http://192.168.19.50:9001/ |
| 工作工具 | FileBrowser资源管理 | https://192.168.19.80:8080/ |
| 开发服务 | Nexus制品仓库 | http://192.168.19.31:8081/ |
| 开发服务 | 测试Nacos | http://192.168.19.20:8848/nacos/ |
| 开发服务 | 正式Nacos | http://192.168.19.11:8848/nacos/ |
| 家庭媒体 | OMV NAS管理 | http://192.168.19.60/ |
| 家庭媒体 | Jellyfin | http://192.168.19.60:8096/ |
| 运维监控 | Grafana | http://192.168.19.70:3000/ |
| 运维监控 | Prometheus | http://192.168.19.70:9090/ |
| 运维监控 | Alertmanager | http://192.168.19.70:9093/ |

此表是提交时的目录快照，没有逐一请求或验收目标服务。MySQL3306、SSH22及NFS/SMB等使用专用客户端，不能登记成HTTP地址。各入口原权限继续生效。

## 本次实测与操作边界

[浏览器回执](browser-acceptance.json)确认真实页面匿名展示14条、搜索Penpot只剩1行、复制地址出现“已复制”提示、390px手机视图无横向溢出，外链href及 `target=_blank` / `noopener noreferrer` 属性正确；页面资源只来自导航自身。可看[桌面截图](desktop.png)与[手机截图](mobile.png)。新窗口点击自动化曾无响应并重开会话，未验收真实pointer跳转，未探测或登录各目标服务，也未据此验收所有按钮。浏览器测试只在隔离会话忽略自签提示，Mac curl另用专属CA验证200；系统全局CA没有变更。

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

从已持有公开证书的管理机核导航自身HTTPS：

```sh
curl --cacert evidence/service-directory-20261110/tls.crt --fail --silent --show-error https://192.168.19.30:9080/health
curl --cacert evidence/service-directory-20261110/tls.crt --fail --silent --show-error https://192.168.19.30:9080/api/services
```

使用GET；`curl -I`发HEAD，会按设计返回405，不能据此判断宕机。`/health`仅报告导航进程自身，不校验14个目标。不要使用`-k`绕过证书核验；无证书或错误证书应先取受信公开证书。

无法建立连接时先核客户端来源、WireGuard/路由及9080监听；TLS报错先核公开证书指纹/有效期；页面空或报清单错误则核部署版本和manifest摘要。不要导出完整环境或TLS私钥，不打印发布私钥，不重启Java/Nexus/Penpot来修导航。

## 清单修改、升级与回退

唯一维护源是 `bkcode/deploy` 项目的 `service-directory/services.json`。管理机工作树为 `/Users/yangzhaohui/work/www/finger/finger-master/projects/deploy`；发布机源码约定路径为 `/var/www/finger/finger-master/projects/deploy`，该路径登记不代表复制了整仓库或server Git key已安装。[源码Git记录](source-git-state.json)明确：导航源码已在本机main提交，**未推到GitHub**。任务前本机已领先远端main 4条既有用户提交；本次只提交自身8文件，未顺带push、rebase、amend或force。观测远端main仍为 `593069eb54a723ee0e63f85b937b9981b39ac1ec`，不能用git pull旧main覆盖现役源码。后续更新先审查精确提交和推送范围，再从该提交导出运行文件；Dell文档仓库的独立push不代表deploy源码已推。

现役固定五文件release在 `/opt/dell/service-directory/releases/63b8c0873936e94f8483c4f1f8747aedb0180d43/`，不是源码工作树。

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

配置目录为 `/etc/dell-service-directory/`，包括公开manifest、`tls.crt`、专属input.nft；唯一新增secret是root-only `secrets/tls-key`，通过systemd `LoadCredential=tls-key`传入。不得复制私钥进release、Git或源码工作树。证书轮换应预告新公开指纹并只重启导航；目前没有自动续期任务。

本服务没有应用账号密码、数据库或可写JSON运行状态，也没有应用数据可做CRUD导出。自动备份仍只限正式MySQL/Nacos，导航不扩围；220发布私钥继续只留220，禁止whole-VM备份/快照导出。Java停用、publisher冻结、Nexus221独立与Penpot等待用户push两条改造的边界保持。
