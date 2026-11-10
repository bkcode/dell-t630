# VM220服务导航首次HTTPS部署历史

> **当前入口已改为 [http://192.168.19.30:9080/](http://192.168.19.30:9080/)**。用户随后明确不需要HTTPS，并要求移除“个人内网 / 服务导航”顶部栏、缩紧标题与外侧留白；当前使用全宽布局，提交 `d56cae553bf95ce0e2c3fe8f258a2f99389aae7c`（ddccc2b为此前布局阶段）。无需账号密码，TLS和登录凭据均不加载；旧证书/私钥仅保留为未启用历史，不用于当前访问。最新交付以[统一内网HTTP记录](../internal-http-20261110/README.md)为准；FileBrowser链接已改HTTP，[最新导航应用](../internal-http-20261110/navigation-links-applied.json)及[14:28最终后检](../internal-http-20261110/final-postcheck.json)通过；[布局应用回执](../service-directory-http-20261110/layout-applied.json)已通过，[最新浏览器](../service-directory-http-20261110/browser.json)与[14:13最终后检](../service-directory-http-20261110/final-postcheck.json)均通过。

以下内容只记录13:50—13:59首次HTTPS部署及其验收，提交 `63b8c08` 和旧截图/指纹不代表现役版本。历史文件保留，不作为当前访问或TLS首访要求。

更新：2026-11-10，Asia/Shanghai。用户在“仅Penpot部署”的较早范围之后，另行明确授权在发布机增加只读导航，这是本期精确新增例外。当时入口为 **[首次HTTPS历史入口](https://192.168.19.30:9080/)**；无需账号密码，只预览、搜索、筛选、复制地址和外链跳转。各目标服务继续使用自己的认证。

`bkcode/deploy` 的 `service-directory/` 模块已按提交 `63b8c0873936e94f8483c4f1f8747aedb0180d43` 的固定五文件部署到VM220；没有运行原发布链，没有安装五个Puyu后端。**首次HTTPS阶段匿名只读导航已交付：原生验收、仅导航重启、浏览器预览与最终后检均有通过回执。** 浏览器新窗口点击自动化无响应后已重开会话，未签真实pointer跳转或目标站点可达性；所有href及新窗口安全属性已验。

## 证据与使用入口

| 记录 | 本次证明的范围 |
| --- | --- |
| [使用手册](usage-manual.md) | 访问、证书核对、页面操作、清单维护及故障处理 |
| [预检](preflight.json) | 13:37只读确认VM220身份、原build盘、Python3.13.5、端口及专属UID可用，Java进程0 |
| [源码独立审查](source-review.md) | 只读范围源码审查PASS；审查文件摘要绑定最终部署的对应文件，不等同远程验收 |
| [提交文件摘要](source-manifest.json) | 从精确提交导出的server.py、services.json及三个Web文件SHA256 |
| [安装回执](installed.json) | 13:50导航启动，14初始入口，UID/GID2001，未创建应用账号密码，原保护服务不变；该回执原始状态仍是native-pending |
| [原生只读验收](native-acceptance.json) | 13:52匿名HTTPS/API/静态入口200、14条清单、无cookie、写方法405、旧登录/路径负测、文件摘要与只读权限、专属nft来源及原服务基线一致 |
| [仅导航重启](service-restart.json) | 13:56仅新app PID变化，14入口匿名读取及清单字节保持；自有nft表原子重应用不重启app，原保护服务frame不变 |
| [监控增量](monitoring-installed.json) | 13:55既有publisher node health增加导航unit检查，无新Prometheus target、不重启exporter或其它服务、不人工外发告警 |
| [最终后检](final-postcheck.json) | 13:57共12项检查通过；13运行来宾/3停止模板、PVE forwarding全0、16targets全UP、导航unit指标1、精确release摘要与原服务保持 |
| [真实浏览器](browser-acceptance.json) | 13:59匿名14入口、搜索Penpot仅1行、复制提示、外链href/blank/noopener/noreferrer、390px无横向溢出；资源仅来自导航自身 |
| [源码Git状态](source-git-state.json) | 导航源码8文件只提交本机，未push；五个运行文件由精确提交git show导出，未改写既有用户提交 |
| [桌面预览](desktop.png)、[手机预览](mobile.png) | 公开目录界面截图，无凭据；只证明已记录画面 |
| [公开证书](tls.crt) | 仅公开证书；私钥不在仓库 |

原生独立[说明](native-acceptance.md)另记录VM210到9080一次TCP负测超时；仅说明该路径未连通，不单凭超时归因某一防火墙层。浏览器自签提示仅在隔离测试会话中忽略，另有Mac curl持专属CA验证HTTP200，没有改系统全局CA。没有从所有LAN/WG客户端逐一验收，也未探测或登录目录目标。新窗口点击自动化失去响应后会话重开且已关闭，不能把已验href/target属性扩大成真实pointer全链路通过。

## 源码与Git交付边界

`bkcode/deploy` 本机main在任务开始前，已比观测到的GitHub main `593069eb54a723ee0e63f85b937b9981b39ac1ec` 领先4条既有用户提交；本次只新增8个自身源码文件的提交 `63b8c08`，父提交为 `81148e8614ee5c49e6f9e4d1b85aebef8adfb33d`。没有push，以免顺带发布4条用户既有提交；没有rebase、amend、force或改远端历史。服务器五文件确由本机精确提交导出，不依赖旧远端main，不能用git pull旧main覆盖现役源码。后续维护须审查明确的新提交与推送范围。Dell配置文档仓库是独立Git交付，不等同deploy源码已push。

## 首次HTTPS阶段运行合同与范围（历史）

- Python3标准库原生服务 `dell-service-directory.service`，专用OS用户 `servicedirectory` UID/GID2001只读运行；此Linux运行身份不是应用登录账号。无应用账号、密码、数据库、CRUD、SSO或JSON运行状态。
- 仅监听 `192.168.19.30:9080` HTTPS；自有 `dell-service-directory-firewall.service` 管理 `inet dell_service_directory_input`，只允许LAN `192.168.21.0/24`、WG `10.66.66.0/24`、本机19.30及lo。没有修改PVE/路由或其他服务入口。
- release为 `/opt/dell/service-directory/releases/<SHA>/`，只含固定五文件；root配置 `/etc/dell-service-directory/manifest.json`、公开 `tls.crt` 及root-only TLS私钥，私钥由systemd `LoadCredential=tls-key`传入。未把deploy仓库现有配置、Git key或发布私钥复制进release。
- 清单只包含14个HTTP/HTTPS地址，导航不探测、不代理目标，不执行部署/启停。MySQL、SSH、SMB/NFS等协议端口不伪装成Web URL；目标认证保持。
- 日后新增入口改项目Git清单并提交，新release只重启导航服务；浏览器不提供增删改。安装器是首次安装工具，不盲重放，也不调用原业务发布流程。
- Java业务仍停用、publisher仍fenced、Nexus仍独立221；Penpot继续等待用户推两条改造后重新核远端，不代push或更新现役。自动备份不扩围，资源NFS与FileBrowser合同保留。

首次HTTPS阶段证书SHA256指纹（当前已不用）：

```text
7B:CF:87:90:17:E9:6B:D7:09:E9:86:A0:74:C7:01:B4:AA:93:12:10:97:77:D8:2B:51:55:3C:2E:81:EB:25:FC
```
