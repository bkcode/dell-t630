# FileBrowser Quantum资源管理页使用手册

更新：2026-11-10，Asia/Shanghai。用户最新要求自建内网应用默认HTTP，PVE/iDRAC内置管理HTTPS保留。本页FileBrowser入口为 **[http://192.168.19.80:8080/](http://192.168.19.80:8080/)**，HTTP切换原生验收及14:28最终后检已通过；最新状态看[内网HTTP交付](../../evidence/internal-http-20261110/README.md)。原 `resources` / `admin` 登录密码和权限保持，JWT、初始化完成marker、UID2000/GID2980、state700及NFS不变。不关闭认证、不改密、不重跑初始化。

06:12的HTTPS原生/API/NFS/浏览器/重启回执保留为历史，不冒称新HTTP运行已验；旧证书/私钥只留未启用历史，不再用于当前访问或健康探测。

## 入口、账号和共享含义

| 项目 | 使用方式 |
| --- | --- |
| 管理页面 | **http://192.168.19.80:8080/**；HTTP切换已验收 |
| 来源 | 受信LAN `192.168.21.0/24`或已连接OpenWrt的WG `10.66.66.0/24`；本机可健康检查。其他19peer不因NFS许可自动得到页面权限 |
| 日常账号 | `resources`：浏览、预览、下载、创建目录/新文件上传；禁止删除、编辑、覆盖、分享与提升账号权限 |
| 维护账号 | `admin`：完整维护权限，只在必要维护时使用，不能声称它也绝对不能删除或改权限 |
| 密码保管 | Mac受保护文件`dell/private/credentials/filebrowser-management-20261110.json`；guest root文件`/etc/dell-filebrowser/secrets/login.json`。只经受控查看器/管理员渠道取用，不输出值、不截图、不贴到URL/命令/日志/Git |
| 资源root | VM280 `/srv/resources`；230/240同挂`/mnt/resources`，正式/测试同一个目录，不拆环境 |
| 系统/数据 | VM280 2CPU/2GiB，32GiB系统＋100GiB数据；NFS数据UUID `57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b` |

页面是受认证的维护入口，不是业务上传API或公开图片域名。它不会自动改Finger `file.upload.path`、Nacos/profile或启动Java。Puyu images仍由MySQL及应用权限下载提供，不会自动迁成NFS文件。

账号中的`account.api=false`表示禁止生成独立API tokens，不是禁止登录会话所需的Web REST。日常上传REST已通过原生验收；删除/编辑/分享/提权等403是各自权限边界，不能把所有REST都写成不可用。

## 当前访问与健康检查

从批准LAN/WG打开HTTP入口，使用原 `resources` 或必要时维护 `admin` 的原密码登录。页面仍需认证，不提供匿名资源下载；不因协议切换生成新账号、重置密码、改JWT或改变原权限。当前HTTP不需要证书首访或CA导入；PVE/iDRAC等内置管理入口仍按各自HTTPS合同访问。

管理员只读检查使用HTTP GET；新健康项名称为 `filebrowser-http-health`，不带 `ca_file`：

```bash
curl --noproxy '*' --fail --silent --show-error http://192.168.19.80:8080/health
```

`/health`匿名200仅表示进程健康，不表示资源匿名可读。HTTP切换验收以[新原生回执](../../evidence/internal-http-20261110/filebrowser-applied.json)和[14:28最终后检](../../evidence/internal-http-20261110/final-postcheck.json)为准；旧HTTPS记录只解释首次部署。

### 首次HTTPS证书（历史，当前不用）

旧[公开证书](tls.crt)及指纹只用于解释首次HTTPS验收，旧root-only私钥保留为未启用历史。当前不加载TLS、不改系统CA，以下不是现行首访要求：

```text
2B:E1:76:FF:A3:10:4B:2C:46:7C:58:23:D9:6C:FB:C2:65:BE:D6:EA:CD:4F:A4:A3:42:56:A5:0E:AB:4F:09:A3
```

## 日常使用resources

1. 从批准LAN或WG打开HTTP入口，选择密码登录，用日常`resources`账号。维护admin不是默认日常登录身份。
2. 选择`resources` source，浏览现有路径或进入已批准业务子目录。这里只映射共享root，不能看metadata/secrets；`lost+found`及符号链接按配置排除。已有跨环境文件不应按单个环境判断可删。
3. 创建文件时使用不冲突的新目录/文件名。先小文件验证；上传同名文件不能通过override覆盖旧文件。出现403时先核权限与路径，不能转用admin绕过日常边界来完成普通上传。
4. 图片可在已认证页面内预览；下载使用页面正常下载操作。预览链接受登录/权限约束，不可当成公开图片URL发给业务用户，也不要通过创建公共分享解决访问问题。
5. 上传后的文件与两个NFS客户端使用同一存储。Web创建实际UID2000/GID2980，数据文件660、目录2770；两机finger999:989＋附组2980可正常读取。NFS创建的文件同样可在页面内按权限浏览/下载。
6. 日常账号不能删除、编辑、覆盖、分享或提升自己权限；误传/改名/清理需求走维护流程，管理员先核正式和测试两边引用。不要把“看不见删除按钮”作为安全证明，本次直接API负例也已验403。

可由管理员在client上只检查**自己刚上传的已知文件**：

```bash
findmnt --mountpoint /mnt/resources -t nfs4 -o TARGET,SOURCE,FSTYPE,OPTIONS
sudo -u finger stat -c '%u:%g %a %s' -- /mnt/resources/<已知专属路径>/<新文件>
```

不得对整个共享树做递归chown/chmod，也不为验证而覆盖、下载或输出未知真实业务文件。NFS自身仍允许受信runtime按其组权限改文件，Web日常禁删不等于OS把整个共享设成只读。

## 最新HTTP验收与原账号使用

[14:25原生回执](../../evidence/internal-http-20261110/filebrowser-applied.json)用两个旧账号及原密码完成新登录，scope与权限完全一致；匿名文件访问401、日常账号管理设置403。只更新config/launcher/unit三个公开文件，NFS与原保护服务PID/身份保持；固定JWT、初始化marker、UID/GID及state路径未变，TLS私钥不加载，六服务和HTTP健康指标为1。

[14:28最终后检](../../evidence/internal-http-20261110/final-postcheck.json)确认认证仍开、原数据路径/NFS保持、无TLS配置或TLS凭据、JWT仍加载且不再注入初始化密码；16targets、资源六服务和HTTP指标UP。导航中FileBrowser链接也已改HTTP；PVE/iDRAC内置HTTPS保留。不是匿名FileBrowser，也没有重置原账号/权限。

[14:30真实HTTP浏览器](../../evidence/internal-http-20261110/filebrowser-browser.json)确认resources使用原口令进入 `/files/resources/`，看到资源页且登录表单消失；临时登录记录/Cookie/本地存储与会话已清，没有读取或写入资源文件。这不扩大为新HTTP全部按钮、预览或上传下载回归。

若旧HTTPS会话影响HTTP登录，可只清除该站点旧Cookie后，用原账号密码重新登录；这只是使用说明，本次没有修改用户浏览器。不要通过删bootstrap marker、重跑init或修改UI密码解决协议切换。

## 首次HTTPS阶段已验范围与浏览器限制（历史）

[原生验收](native-acceptance.json)status=passed、fixture_cleaned=true：日常账号创建/上传合成PNG和文本，两client以finger读回/追加/互读，页面API再下载比对一致；日常delete、override、PUT编辑、分享、提权403，匿名资源401。原NFS/挂载/客户端unit及原`/mnt/dell-artifacts`状态保持，Java仍0，无其他文件操作。

[浏览器验收](browser-acceptance.json)确认真实登录、四个合成文件列表，以及按**观察到的实际href路径直接访问**后的96×96 PNG渲染。自动点击未完成导航，**没有签收所有按钮或pointer导航全测**；管理设置/密码页面未打开，截图与密码都不在普通证据。专属fixture已清理，不要再把它的旧链接当现存文件。

首次API/NFS runner曾在切finger前以root读660标记而被root_squash拒绝，保留[native-first-attempt](native-first-attempt.json)；仅修测试前置顺序后通过，没有把错误改成finger授权故障或放宽服务权限。初始launcher也曾误拒systemd凭据合法ACL，见[ACL兼容回执](acl-compatibility.json)：只兼容root持有、仅named UID2000只读的精确ACL，未chmod/chown运行时凭据，旧启动失败记录保留。

## 服务、状态与故障处理

仅在必要管理窗口由管理员执行：

```bash
sudo systemctl status dell-filebrowser.service dell-filebrowser-firewall.service --no-pager
sudo systemctl is-active nfs-server.service srv-resources.mount
sudo python3 -I -B /opt/dell/resources/guard.py --role server
```

FileBrowser是官方native Go binary，固定`/opt/dell/filebrowser/releases/v2.1.4-beta/filebrowser`，无需Docker/Podman。`dell-filebrowser.service`以Linux UID2000、primary resources GID2980运行，UMask0002、MemoryMax384M/CPUQuota100%；其数据盘门禁和独立`inet dell_filebrowser_input`必须保持。该表仅控制8080，不替换原NFS表或改PVE/GW路由。页面故障不应通过重启NFS、两running或PVE修复。

公共配置为`/etc/dell-filebrowser/config.yaml`；metadata/database.sqlite/cache独立在`/var/lib/dell-filebrowser`，owner2000:2980、700，不在NFS共享中。HTTP切换仅移除TLS配置、启动参数和tls-key凭据加载；原认证、固定JWT及初始化口令marker规则保持。旧`tls.crt`/tls-key只留未启用历史；不要使用`systemctl show Environment`、完整进程env或打印secret文件调试。

初始化完成标记为root持有的`/etc/dell-filebrowser/bootstrap.complete`，成功后正常重启不再注入初始化管理员口令；**不要删除标记来重置密码**。JWT每次由固定私有文件提供。密码修改/账号恢复必须用受控维护流程，同时更新私有交接；旧初始化文件中的口令不保证与用户后续改密一致，不据此反复重置账号。

FileBrowser的metadata自动备份已disabled，更新检查disabled；这没有改变正式DB自动备份。资源文件、FileBrowser状态、cache和旧TLS密钥均未纳入现行自动备份，机器丢失或误删恢复未签。不要将这些目录或login.json打包进Git，也不重新启用旧whole-VM任务。

## 版本升级

- 固定版本为**v2.1.4-beta**，不把beta标签说成stable。此次官方查证v2.0.2未含[GHSA-892f-9h5p-mfc8](https://github.com/gtsteffaniak/filebrowser/security/advisories/GHSA-892f-9h5p-mfc8)修复，预期v2.1.0稳定release地址404，因此选择已含补丁的固定tag；[官方锁](../../infra/resources/filebrowser/upstream.lock.json)含AMD64 SHA。不是建议将来永远使用beta。
- 升级先查官方安全修复、架构/配置schema、数据格式/回退兼容、权限与初始化行为，再核产物SHA，单独准备受保护metadata恢复点。不能用`latest`/`stable`浮动标签或未经兼容检查的新binary覆盖固定路径；binary SHA固定`4af557de16603bdfba2ae87b7807b8654612c542b2deff826eedee72086a5da2`，升级需联动审核upstream lock、renderer、launch guard及installer/来源manifest，不能只换binary让门禁失配；不能为升级重新bootstrap账号或回滚共享真实文件。
- 新NFS client仍须同步严格resources policy/renderer/guard/installer、exports、bridge与server输入白名单；当前固定只有230/240。Web页面不是新增client的授权入口，模板本轮也没有修改。

首次HTTPS阶段[只重启新app验收](service-restart.json)已通过：服务PID改变，原admin/resources凭据仍可登录、日常scope与限制保持、bootstrap口令不在后续进程环境、固定JWT凭据加载；NFS及其他保护服务identity不变，没有重启VM或clients。这里没有做用户改密演练，不把“原凭据保持”说成已测试任意改密/恢复场景。[06:12最终后检](final-postcheck.json)statuspassed：13运行来宾/3停止模板，16targetsUP、资源6项服务指标及专属CA HTTPS健康为1；PVE所有forward0，NFS保护帧不变，其他19peer8080实际拒绝。没有新增Promtarget/receiver或外发测试消息；本页命令不能视为又执行一次重启。

新app健康只扩签此次固定版本、合成样本和所列负例；真实用户业务上传接入、全部UI按钮/导航、负载SLO、数据备份恢复及公网服务仍未签。
