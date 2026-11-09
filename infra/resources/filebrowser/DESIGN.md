# FileBrowser Quantum资源管理页面：固定native候选与同步清单

更新：2026-11-10，Asia/Shanghai。**设计草案，未安装、未创建账号、未开放页面或修改现役配置。** 本轮已确定官方native v2.1.4-beta、HTTPS19.80:8080与下方固定renderer；仅本地生成候选，没有安装/启动。初始化、权限与原生验收仍须主AI实际验证，不能用生成或单测结果替代通过回执。

## 1. 已有基础与本次增量

VM280 `resource-service`/19.80已有2vCPU/2GiB、32GiB系统盘和100GiB独立数据盘；数据UUID `57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b`，挂载`/srv/resources`。现役唯一NFSv4.1导出fsid0，仅230/19.40、240/19.45挂到`/mnt/resources`；正式/测试仍为**同一目录**。两running finger UID999/GID989不变，resources附组GID2980，server根root:resources2770/default ACL、root_squash与客户端hard挂载保持。基础实际回执见[资源交付](../../../completion/20261109-resources/README.md)、[最终后检](../../../completion/20261109-resources/final-postcheck.json)。

新增的是管理员资源维护页面：认证后浏览、下载及受控上传。它不提供公共图片域名、匿名下载/分享或业务上传API，不改变Finger/Puyu应用接入。只有LAN21/24与WG10.66.66/24中的授权管理员可登录；网络可达不等于自动获得登录权。

| 能力 | 本期合同 | 验收方式 |
| --- | --- | --- |
| 浏览/下载 | 已认证的维护身份，仅`/srv/resources`内 | 页面及实际下载请求；越界/未认证均拒绝 |
| 上传 | 受控新文件上传；限制路径、单文件大小和并发，默认不覆盖旧文件 | 专属fixture上传后230/240以finger读回，原有文件不变 |
| 公共分享 | 默认关闭，不能创建匿名链接/匿名令牌 | 直接请求分享创建/访问API也拒绝，不能只隐藏按钮 |
| 删除/编辑 | 默认关闭，含API、批量操作、内容写回 | 直接API负测，旧fixture保留 |
| 其他变更 | rename/move、覆盖/追加已有文件、自动解压、执行命令等不在默认允许集合 | 若产品存在对应能力，需明确禁用并验证，不因“上传”默许 |
| HTTP图片/业务服务 | 不搭公开图片URL，不改Nacos、Java、应用连接或文件后端 | 变更前后核对与未启服务证明 |

“管理员维护”描述操作者身份，不要求日常登录必须是产品内可修改所有安全策略的超级管理员。如果产品super-admin会绕过上述权限，应分离受限维护账号与受保护的初始化/配置权限；否则不能签“删除/分享已关闭”。不能仅靠前端禁用按钮、客户端请求参数或约定操作者不点来替代服务端权限。

## 2. 已选固定native合同（尚待实际安装验收）

官方产物固定`gtsteffaniak/filebrowser` tag `v2.1.4-beta`、Linux AMD64，SHA锁见[upstream.lock.json](upstream.lock.json)。不是main自动更新，也不把beta名称说成stable；binary固定`/opt/dell/filebrowser/releases/v2.1.4-beta/filebrowser`。不安装Docker/Podman或引入容器nft路径。

[prepare.py](prepare.py)是无参数固定renderer，`render()`只返回6个公开key：`config.yaml`、`dell-filebrowser.service`、`dell-filebrowser-firewall.service`、`firewall.py`、`launch.py`、`input.nft`；不安装、不联网、不生成秘密。`manifest()`给输出十六进制SHA，`validate_config()`拒绝任何额外scope/权限/监听变更。JSON格式输出兼容YAML，不依赖额外YAML包。离线回归见[test_prepare.py](test_prepare.py)。

服务身份固定`filebrowser` UID2000、primary resources GID2980。state/DB/cache统一在`/var/lib/dell-filebrowser`（owner2000:2980、0700），配置`/etc/dell-filebrowser/config.yaml`root0644；公开证书`/etc/dell-filebrowser/tls.crt`root0644、上级目录0755，secrets子目录root0700/文件0600。systemd LoadCredential读取jwt-key/admin-password/tls-key，进程每次只将JWT放自身环境，首次初始化才加载管理员口令到`FILEBROWSER_ADMIN_PASSWORD`，不放argv或普通日志。

**初始化完成标记固定`/etc/dell-filebrowser/bootstrap.complete` root:root0644，位于root持有只读目录，不放app可写state内。** installer须初始化并实际核验账号后才由root创建；wrapper遇标记存在不读取管理员口令，并明确不再注入/继承该env，避免每次重启覆盖管理员改密。配置没有adminPassword字段；auth.key和TLSkey仅保环境/凭据路径引用。

环境白名单同时固定`FILEBROWSER_DISABLE_AUTOMATIC_BACKUP=true`，避免程序自身metadata自动归档；这不是修改既有生产DB备份任务。disableUpdateCheck true；日志仅warning/error、apiLevels空与API路径过滤，不输出请求body/凭据。unit UMask0002、MemoryMax384M、CPUQuota100%、TasksMax64，预算仍在280的2GiB内，资源足够性须native验证。

RequiresMountsFor+BindsTo真实/srv/resources与独立防火墙unit，启动前以root只读guard核server UUID，实际程序以非root运行；NoNewPrivileges/ProtectSystem=strict/ProtectHome/PrivateTmp，仅共享和state可写。`launch.py`还核UID/GID、公共配置精确字节和binary完整性。CLI固定`--no-input -c /etc/dell-filebrowser/config.yaml`，不接受调用者追加参数。

## 3. 身份、数据与持久化

1. 新服务使用固定独立非root UID2000、primary GID2980，主AI须实际核NSS无冲突；不复用/创建server finger UID999来冒充running，不改两client原身份。它可追加resources GID2980来操作批准共享，但必须说明该OS写权限本身能够删除文件，**删除禁用是服务端授权边界，不能声称OS也阻止它删除**。
2. 唯一资源root为真正挂载的`/srv/resources`。启动前复用UUID/fstype/mountpoint门禁；Requires/BindsTo数据mount，盘缺失即拒绝页面写入，不能落到根盘下层。程序默认root/home、容器source、上传落点均需核实，不能只在页面显示正确路径。
3. 元数据/账号/会话数据库固定放`/var/lib/dell-filebrowser/database.sqlite`，缓存固定`/var/lib/dell-filebrowser/cache`，根目录0700、私有文件0600、属独立服务身份。上传暂存也必须明确有容量上限的位置和原子提交机制；不要把数据库、config、认证文件、缓存或恢复副本写进`/srv/resources`被两client看见。
4. FileBrowser新建资源应保留共享组2980与setgid/default ACL合同；进程提前应用umask0002，并核实际创建mode。应用若主动以0600/0644创建，umask/default ACL不能强制补出组写，需产品受支持的创建权限配置或另审精确新文件处理，不能递归chmod现有共享文件来凑通过。
5. scope边界需覆盖symlink、`..`/编码路径、下载/上传/压缩预览等入口；禁止从共享内链接跳到metadata、`/etc`或其他宿主路径。若程序不能正确拒绝这些入口，不能只依赖用户不创建链接。容器/systemd隔离是补充，不能替代实际路径负测。
6. 不读取/迁移现有真实文件验证页面；测试只用登记的专属合成fixture。正式与测试共根，清理前要核两边引用，不能只查一个环境删所谓孤儿。

账号、初始化口令/会话key等只在主AI受保护private或来宾权限受控文件保管；不得以argv、URL、普通日志、截图或Git传值。不预置默认口令/匿名登录，不让元数据目录成为下载scope。具体初始化命令/产品字段待官方版本选定后审查，本文不给未经验证的伪配置。

## 4. 网络最小增量

- 监听已定为HTTPS `192.168.19.80:8080`（尚未安装启用），证书由主AI创建/核验；不得0.0.0.0意外暴露、不新增公网CF ingress。配置为服务自身TLS，不创建Nginx图片入口；客户端须信任主AI分发的公开证书/CA，禁止关TLS校验代替受信验收。
- 管理页面只允许IPv4源`192.168.21.0/24`与`10.66.66.0/24`，本机loopback可做只读健康；其他19peer/未知来源拒绝。现役GW/PVE bridge受信LAN/WG已经有路由许可，不代表新进程可跳过280自身输入门禁。8080单独由`inet dell_filebrowser_input`自有表处理，固定atomic delete/create只替换自身表，不改现役NFS表、不清全ruleset，不开整个19/24浏览器访问。
- NFS2049原两个client、RPC外部拒绝、SSH、Ops9100、GW路由/DNS/IPv6与PVE全forward0/noNAT保持。上Web不能替换整个resources policy为宽松默认，也不能把管理HTTP与NFS来源集合混在一起。
- 若rootless端口代理改变可见源地址，必须在保留原source的位置落实白名单并实际负测。容器发布端口可能走不同hook，需用真实数据包验证拒绝路径，不只看`ss`。
- NFS/两client及其OS不为安装页面重启；所选FileBrowser自有unit可在明确窗口启动/重启。任何daemon安装前后都核表/forward/route与NFS服务identity，出现非预期差异停在本步骤，不用宽泛规则救活。

## 5. 最小实际验收合同

以下是**未来检查项，不是已完成**，保持原NFS8项验收历史，另建本次增量验收。

| 项 | 可观察通过条件 |
| --- | --- |
| 产物与进程 | 官方固定版本/AMD64完整性、独立非root身份、受控可写路径、资源限额；没有额外端口/能力 |
| 认证与权限 | 未登录拒绝资源；日常账号browse/download/upload成功；delete/edit/share/rename/overwrite/其他变更直接API均拒绝 |
| 来源白名单 | 实际LAN21与WG10.66请求可到认证页；其他19peer/未知来源实际拒绝，保留原NFS/SSH/9100合同 |
| 上传与路径 | 专属新文件上传，230/240 finger读回及组/mode正确；同名覆盖、越界、符号链接、超限与并发拒绝，原文件未改 |
| NFS与失效门禁 | 原280UUID/exports/两个client真NFS保持；页面缺盘拒绝、没有写根盘（破坏性故障注入须另审窗口，不为验收停业务） |
| 持久化/清理 | 页面自身正常重启后账号/metadata持久、scope不变；仅清本次fixture，无未知文件/私钥/会话数据进入普通证据 |
| 整体回归 | 13guest/3tpl、原16targets及资源服务指标、Lark/原NFS/防火墙不漂移；无Java/图片入口/文件迁移或自动备份扩围 |

页面“成功上传”不等于应用上传API已接入或文件已备份。若产品不能服务端禁止覆盖/删除/分享，不应降级成UI隐藏后上线；先报告缺口，再选受支持权限/接口控制方式或收窄功能。验收不使用真实敏感文件、不发通知、不用浏览器地址栏传口令。

## 6. 后续需要同步的canonical文件与文档

下表是主AI未来落实/收口清单，**本草案没有修改这些文件**。

| 文件/入口 | 应同步的最小内容 |
| --- | --- |
| `plan.json` VM280角色/操作状态 | 新管理服务的部署方式、固定版本、unit、端口/来源、scope与证据；资源仍13来宾/45vCPU87GiB，不扩NFS client或备份 |
| `AGENTS.md` / tasks | 用户新增管理页面范围、实施与未实施边界；禁止用旧“NFS-only不HTTP”否认本次新授权，但继续无公开图片/Java/数据迁移 |
| `infra/resources/filebrowser/` | 最终版本/renderer/install/guard/测试与README；选型通过后才增加真实命令，不重放资源provision/bootstrap |
| `infra/resources/README.md` | 从“NFS-only无HTTP”更新为“NFS＋受限管理员页面；无公共图片URL”，保原NFS工具与失败历史 |
| `machines/vm280-resource-service/{README.md,config.json,config-sources.json}` | 实际服务/身份/可写路径/监听/来源/权限；索引公开配置和增量回执，不复制secret |
| `machines/README.md` | 新页面入口和范围；230/240目录仅在共享权限/实际运行合同发生变化时补，不能伪造它们已接入上传业务 |
| 根`README.md`、`02-architecture.md`、`11-live-handoff.md`、`12-service-access-and-operations.md`、`19-manual-operations.md` | 区分管理HTTP与业务图片/上传API；真实访问URL、日常受限操作/失败处理/权限与凭据保管渠道；无Java/备份扩围 |
| `completion/20261109-resources/README.md`、`usage-manual.md` | 原NFS验收按原时点保留；增加管理页面链接与新限制，不改原8项结果冒称涵盖Web |
| 新`completion/<本次FileBrowser阶段>/` | 脱敏native安装、正负权限/来源、上传互读、回归/persistence及final-postcheck，独立acceptance清单 |
| server owned input policy / 持久化renderer / 原检查器 | 精确Web端口来源规则并与现场一致；NFS/SSH/监控与其他owned表保持；只由主AI受控安装 |
| Ops服务白名单/collector | 如需增自有unit指标，仅追加FileBrowser role内服务并native验证；不自动添加外发通知或重建原Ops |
| sources/index/validators/Git | 主AI统一刷新public来源SHA、链接、机器合同、秘密扫描与提交；不把草案列成实际运行证明 |

现行自动备份仍仅正式VM200数据库/Nacos配置。新增FileBrowser metadata、缓存与资源文件都未自动纳入；页面可下载文件不等于有独立备份。任何元数据导出/恢复与文件一致性策略另行确定，禁止重新启用旧whole-VM任务或将真实会话数据库提交Git。

## 7. 安装前仍需实际验证的事项

1. 固定官方binary已由主AIstaging；native启动、证书信任、非root身份/384MiB限额与配置兼容仍需原生验证。
2. 配置中的每source权限和userDefaults只是默认值，初始admin实际记录及直接API行为必须核验；private source拒分享，不能虚构不存在的source.permissions.share字段。
3. root初始化marker只能在账号成功且策略核验后创建；真实改密后重启保持、JWT稳定与日志无secret须验收。
4. 模板/Java/Nacos/图片业务均不修改；外置metadata/cache、目录/文件mode、越界与独立来源负测、共享NFS/16targets回归。
5. 只重启自有FileBrowser服务的窗口、精确回退自有unit/8080表及新阶段验收目录；不卸载NFS、不格式化、不递归改现有共享树权限。

以上由主AI按已有用户授权完成核对与审查，不代表要求用户重复确认已经明确的浏览/下载/受控上传范围；仅未验证产品能力与原生行为保持pending。
