> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# fish补齐：盘点与后续模板窗口方案

> 当前进展更新：root已明确开放7guest及后续220独立install-only窗口，190/200/201/210/220/230/240/260共8台已完成fish4.0.2-1，bash与核心服务保持。权威实时结果为runtime-status.json。template/default-shell问题仍pending；下文初始只读方案作为阶段记录保留。

当前仅完成只读盘点，**没有安装、apt update、chsh、配置文件变更、服务启停或模板启动**。用户默认shell选择尚由root确认；在新明确指令前一律install-only，保持bash。不操作PVE宿主shell/package，不触CF100、Penpot250、Ops270、待退役231/232/221或旧QA。

## 已确认的范围和事实

保留guest：190/200/201/210/220/230/240/260，均Debian13 trixie x86_64；ub与root当前/bin/bash，fish和fish-common未装。离线APT lists candidate均4.0.2-1，没有fish缓存deb。fish下载约1.88MB、common约2.06MB，Installed-Size合计约23MiB，**不含缺失hard dependencies**。Depends包括bsdextrautils、groff-base、man-db、procps、python3和PCRE/libc等；Recommends为xsel、浏览器，不安装recommend可减少体积，但不能跳过man-db等harddep。

190512MiB虚拟网关当前MemAvailable373698560B（约356MiB），根盘可用约29GiB；不编译Rust/源码、不dist-upgrade、不装插件/主题框架。其它guest根盘可用均>24GiB，详细即时值在inventory。资源/包版本须执行前重查，缓存candidate不是永不变的保证。

模板：9001=tpl-docker-base、9010=tpl-linux-base、9011=tpl-java-acceptance，三者均template/stopped。PVE元数据为DHCP、ub、ssh_deletekeys:true、preserve_hostname:false；模板内OS/shell/fish live package/cache状态**unknown-stopped**，没有挂载或启动模板磁盘。9011既有封版/QA验收证据显示Debian13/JDK21/无业务，不能把旧证据当本次fish安装通过。

## 运行guest后续安装窗口（本轮未执行）

root逐role开放窗口，先保存ub/root及服务账号shell、fish包状态、OS/DNS/盘/内存、APT锁是否占用和关键服务PID/健康基线。包模拟必须确认只新增fish/common和必要依赖，没有升级/删除关键现役包；不删除APT锁、不杀其它apt进程。

优先精确已审核candidate版本、Debian13官方签名APT，no-install-recommends/no-upgrade，不整机update/upgrade，不下载第三方fish框架。当前只有metadata无deb，不能假称可直接--no-download；若精确包URL过期或依赖不满足，停在解析阶段报root，由root决定刷新lists或使用同版本离线包集合，不能放宽签名。

190优先在临时构建clone解析/下载所需deb，再在root批准512MiB窗口仅安装同一已验证包集合；避免在网关上高内存解析/编译。若必须在线APT，限制只装所需包、保留当前resolver/nft/dnsmasq/SSH进程；man-db trigger/timer等包效果要记录，不能承诺“fish无任何systemd副作用”。不会主动重启网络、Docker、SMB、应用或PVE。

安装后检查fish --version及dpkg确装版本、/etc/shells中的fish路径（可能由包正常增加）。对比ub/root及服务账号登录shell必须保持；不写bashrc/profile/config.fish/universal vars、不执行chsh、不改Publisher/deployer/finger/nologin服务账号。独立fish smoke只能在明确的无config/不持久history方式、从新包实际--help确认参数后运行；不将启动fish视作改默认shell。

安装失败只报告实际阶段/exit类别，不为成功动业务配置或强删依赖。原shell始终bash，保持SSH复连能力；新依赖不能盲purge以免删原先已有包。真实关键服务与默认shell前后验证，excludedrole不连不改。

## 模板更新方法：不启动原模板，root独占PVE操作

1. root保存每个源template config/disk引用/user snippet SHA、当前状态和既有封版清单，源保持stopped/template。root分配临时builder VMID/MAC/hostname/IP/预算，以**full clone**从对应template复制到独立磁盘；child不调用qm clone/start/set/template/power。
2. builder显式hostname、DHCP或root指定临时server19地址、仅现有客户端**公钥**与ub。模板保持ssh_deletekeys:true让首次clone生成自己的hostkey；第一boot root经可信QGA核对hostname/IP/MAC/machine-id、hostkey后才给child strictSSH info。不得复制客户端私钥或复用其它VM的machine-id/hostkey。
3. child仅在明确builder窗口确认实际OS、shell、fish/package缓存及模板属性，再按同版本策略安装fish。9001需保留Docker基础，9010Linux基础，9011JDK21/非root/监控验收脚本/无业务配置与凭据；不植入任何特定role默认IP、密码、MCP key或运行应用。默认shell仍按本次user选择；未确认即保持bash。
4. 验证包与原template差异、关键工具、默认shell、ub公钥登录。若builder还要改metadata/reboot，使用**instance-only** ssh_deletekeys:false保留首次生成的key，防止重演230 metadata变更再生key；这个instance override不能封进最终通用模板。
5. root批准后复用既有已审封版清理逻辑：清cloud-init instance/cache、DHCP lease、machine-id、host私钥和临时QA状态，恢复generic hostname/DHCP/user snippet first-clone策略，不去删ub授权公钥。模板本体不运行；由root将清理后的builder停机转为**版本化candidate template**，原9001/9010/9011继续原地保留。
6. root从新candidate建立两个独立full QA clones。验证两者machine-id/hostkey互不相同且不同于builder/其它保留guest；ub严格SSH、公钥权限、明确hostname、cloud-init/QGA、fish版本、原默认shell一致。9011还须JDK21 nonroot smoke、无业务目录/凭据/业务unit/listener；9001Docker基础保持。第一次生成key后如做reboot验证，只给各QA实例保key，template仍firstclone生key。
7. 双clone验证通过才由root决定promote新template/version映射；不要让child直接改源template config或替换base盘。若必须维持原template ID，root单独规划保留原disk/config的受控离线替换/回退，不挂载或用apt修改原template本体，不在PVE安装fish/guestfs来省略身份验收。
8. root清理自己分配的builder/QA或保留版本化candidate，记录恢复到stopped/template状态。旧模板/旧证据不覆盖；本轮只准备方法，没创建任何clone。

## 通过条件与当前状态

| 条件 | 当前状态 |
| --- | --- |
| 8个指定guest OS/shell/已装fish/APT缓存/空间盘点 | 已只读完成 |
| 3源template保持stopped，身份flags采集 | 已只读完成；live包unknown |
| fish仅安装且默认shell未改 | pending root窗口/用户shell选择 |
| 190低内存安装、关键网关服务前后保持 | pending |
| 三类template独立builder安装/封版/双clone身份验证 | pending root分配，不启动源 |
| excludedroles/PVE宿主无操作 | 保持；仅PVE读取template安全元数据 |

工具inventory.py仅允许列出的8guest与3template，只读APT时禁用持久pkgcache生成，不apt update、不输出源仓库URL或秘密。权威盘点inventory.json，摘要inventory-summary.json。安装/模板验收不能用本计划保存签收。
