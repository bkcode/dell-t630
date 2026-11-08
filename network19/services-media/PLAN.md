> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# Penpot / Nexus / NAS：19网段迁移准备

当前三role已按逐台明确窗口完成19网应用迁移与语义验收，实际事实和失败保留见[EXECUTION.md](EXECUTION.md)。下文是准备期精确方案和回滚参考，不应当作“仍未应用”。地址/MAC/UUID见manifest.json；目标OS/NIC/PVE/OW由root实施，子任务仅已审应用事务。tracked Git ff1783e和历史源码未做全局替换。

## 路由与管理前置

root管理router190（外21.23/内19.1）、guest NIC/持久地址/桥与ACL，以及Mac/21网到19网的实际路由。三个应用IP分别250=19.50、221=19.31、260=19.60。保留原NIC MAC，不按eth0/ens18猜设备；NAS必须按MAC更新现有OMV网络对象，保持ens18 IPv6禁用与ub密钥策略。默认网关与DNS均改19.1；root已固定vmbr19，DNS由19.1转发upstream21.1。router190与OW路由已由root实际验证；本子任务不重复修改。

这是同机改址，不重新导入数据/账号，不启动fresh init，不build/pull，不换卷/UUID，不跑omv populate初装迁移器。现有旧网段服务监督有地址门禁，必须先在旧IP仍存在时受控停止本role，再由root迁NIC/IP/路由；不能先改网让旧guard无限重启。root/QGA提供最后接入和回退通道，不关闭hostkey，不换或复制私钥。移入同一19子网后原prod/test路由隔离不能沿用旧桥假设，root的数据/Java/ops角色必须先审L2下的guest防火墙/来源ACL。

## 准确文件变更

| Role | 活动路径/选择器 | 本次变化与保留 |
| --- | --- | --- |
| PEN250 | `/opt/dell/penpot/assignment.json` `expected_guest_ip` | old10.63.30.30→19.50；hostname/storage UUID不变；target_guard.py本身从assignment读IP，不需改 |
| PEN250 | `/etc/penpot/.env` `PENPOT_PUBLIC_URI` | oldhttp://21.22:9001→http://19.50:9001；只改该公开键，所有密码/secret/flags/worker IDs字节保持 |
| PEN250 | `/opt/dell/penpot/compose.fresh.yaml` frontend ports | 当前是**字面量**0.0.0.0:9001:8080，不读取.env PENPOT_BIND_ADDRESS；改为19.50:9001:8080才真正限bind；同时将两条固定1.1.1.1/1.0.0.1 DoH上游精确合并成192.168.19.1:53；172.30.250.53内部proxyIP/静态health/网络/卷/镜像/resources保持 |
| PEN250 | `/opt/dell/penpot/runtime/health-supervision/supervisor.py` | 固定lock身份与guest_guard两处oldIP→19.50；稳态仅新IP，迁移工具才接受明确old/new阶段 |
| PEN250 | 同目录`node-health.mjs` | admin307 origin与callback精确改http://19.50:9001；MCP只初始化的内部URL不变，认证/权限不放宽 |
| PEN250 | `/opt/dell/penpot/application/target-api.py` `ORIGIN` | loopback9001→19.50:9001；新IP精确bind后原loopback不再可用，私有owner身份仍只在本guest读取，不改Git |
| PEN250 | 同目录`deployment-lock.json` | guest.ip改新IP；精确重算改动的compose package SHA和supervisor/node-health监督SHA；11imageID/UUID/资源/mount清单与Git HEAD不变 |
| Nexus221 | `/opt/dell/nexus/assignment.json`和`fresh-instance.json` | 两者expected_guest_ip同步10.63.30.20→19.31；保留原mode/new-instance proof/empty-init历史字段，不重建marker或数据 |
| Nexus221 | `/opt/dell/nexus/application-import.py` `ORIGIN` | loopback8081→19.31:8081，供既有只读verify客户端；不调用import/bootstrap/rebuild/写repo |
| Nexus221 | `/etc/nexus.env` `NEXUS_BIND_ADDRESS` | 只改公开bind为19.31；NEXUS_DATA_DIR不变；container backend internal:true与gateway固定nexus:8081 upstream不变 |
| NAS260 | `/opt/dell/nas/.env` | 只改NAS_BIND_IP=19.60、JELLYFIN_PUBLIC_URL=http://19.60:8096；UUID/UID/GID/镜像/卷全部不变 |
| NAS260 | 持久Jellyfin`config/config/network.xml`（阶段预检必须证实实际路径/结构） | LocalNetworkSubnets旧10.63.40/24→19/24；21/24、127/8和既有Docker网关保持；EnableRemoteAccess=false、UPnP关闭，不初始化账号 |
| NAS260 | OMV实际Ethernet对象（root网络阶段） | 已只读证实ens18/MAC匹配对象uuid及实际8.6 RPC schema；`omv-network-payload.json`保留所有18必需字段与metrics，只改address/netmask/gateway/DNS。仍由root网络阶段在新鲜旧值/MAC校验后经官方setter+Salt部署；不能裸写config.xml/重跑populate |

PEN `/etc/penpot/fresh-instance.json`当前仅mode/Git创建元数据、没有expected_guest_ip，整个文件保持。`application/fresh-target.py`的旧初装默认PUBLIC_URI属于已锁bootstrap代码，本期不重跑、不改它或Git。原fresh-core compose同样不是当前11服务入口，不批量替换历史源。任何未知实际差异必须停止stage，不自动容错套入。

PEN worker/import都是`http://penpot-frontend:8080`内部基址，必须保持；OriginPolicy读取当前frontend canonicalURI并只把/assets请求映回内部地址，不需加入旧/新外部宽泛host alias。MCP对外变http://19.50:9001/mcp/stream（认证值保持且不写文档/argv/日志），客户端连接配置由root另行审阅，不在此复制旧key。query-safe nginx只读overlay及其哈希不变。backend/import经172.30.250.53的dnsproxy上游也统一19.1:53，再由GW→OW21.1，禁止留下活动DoH绕路例外。import下载仍只允许官方公共包/已有安全规则，不为改址放宽SSRF。

Nexus未发现强制旧baseURL的已部署配置；nginx透传Host/X-Forwarded-*会自然返回新host。stage仅检查Base URL是否有显式旧值，有则先给root审真实API/模型，再只改baseURL，不能读取/复制proxy认证。Java/发布端Maven URL由其他role改为http://19.31:8081/repository/finger-public/或现有受限发布repo；**不改POM/JAR/metadata来替换URL**，234primary SHA/GAV保持，backend仍无外网出站。

NAS OMV80/SMB445一般随新网卡地址可达，stage用只读实际配置确认没有绑定旧地址；若有sshd ListenAddress/SMB interfaces或hosts allow明确旧IP，先列准确配置来源，不能临时开放全网/密码登录。Jellyfin对21/19客户端识别为本地，EnableRemoteAccess=false保持。媒体根guard不含IP，必须字节保持。exporter9100绑定与Ops目标/ACL由root的Ops任务统一更新。Pen/Nexus改精确IP bind后，Ops本机HTTP若仍指127.0.0.1:9001/8081必须按角色更新到新guestIP，不能因静态loopback旧值误告警。

## 每role事务顺序与回滚

1. **stage（未来窗口）**：固定hostname/MAC、旧IP、UUID、root非PVE/AMD64、local Docker及已审driver验证（250/221=overlay2，NAS260=overlayfs；不切换后端）；只读核11/2/1目标healthy与镜像ID。stage读取准确活动文件到同一来宾root700事务目录、backup600；本机不接收秘密。预构造全部补丁、校验old值和每文件SHA/mode，全部验证后才允许quiesce。公开receipt只给键名、状态和secret-preserved布尔；真实凭据聚合hash只留目标600记录，不能输出低熵密码hash。
2. **quiesce（需root明确role窗口）**：PEN先确认worker ready/idle、import无在途writer；仅停止该role的systemd监督，确认其完整容器集合停止。Nexus停止2服务，NAS仅停止Jellyfin；OMV/SMB要等root网络窗口与客户端无写入确认，不擅自停整个NAS。
3. **root改NIC/IP/路由**：保持MAC，QGA/控制台待命；NAS按真实OMV Ethernet模型更新，普通来宾按root统一机制持久改址。让新IP出现并验证严格SSH，再给应用commit。旧IP只在明确短暂transition guard中获准，不能永久把两个IP都放行。
4. **apply-files**：服务维持停止，先全量预检所有目标旧SHA和预备新SHA，逐文件同目录临时文件+fsync+replace；多文件通过事务journal+失败全部还原实现受控原子语义，不声称跨目录系统级瞬间原子。PEN锁最后写但启动前所有package/supervision hashes必须一致；私有.env只允许公开键变化。
5. **start/verify**：仅新IP门禁，原UUID/镜像/Git/新身份hash相等；原systemd路径start，禁止裸up/删卷。新URL readonly健康与鉴权、持久数据完整性通过后才向root给commit候选；root更新统一metadata/ACL/Ops与旧DNAT退场。
6. **rollback-files**：先在新IP仍可达时停止该role，按journal确认当前就是本次新SHA才恢复old备份；第三方修改拒绝覆盖。保持服务停止，root恢复旧NIC/IP/路由及OMV旧对象后，rollback-start仅接受oldIP、同MAC/UUID，再原unit启动并复验旧URL。应用配置回滚不回滚数据、身份、源Git或新用户写入。中途不确定一律停在可审journal，不盲目重跑。

## 最终验收（目前未执行）

- PEN：11healthy/notify/原镜像IDs和limits、Gitff1783e clean；同一3设计原data/revn与971原媒体SHA子集不变（当前973包含2官方导出缓存）、新身份/IDmap/凭据hash不变；新PUBLIC_URI与admin callback正确；新MCP授权read/未授权设计拒绝（不把initialize200当越权）；已完成async job IDs/status同request重试幂等，若需新增专用import必须另行明确验收对象。
- Nexus：EULA、新身份、repo/group/role均保持；49GAV234primary SHA；35metadata/1076checksum按既有再生语义，不触发rebuild任务；新地址读本地hosted/finger-public，匿名拒绝、reader写403/publisher正式写与delete403。无旧上游请求/公网代理。
- NAS：同根/2TiB UUID、key-only、三SMB共享writer/read/匿名拒绝矩阵和既有fixture SHA；Jellyfin现有原创素材可读/DirectPlay及RO媒体边界，games/incoming不暴露；strong admin/viewer身份不变，RemoteAccess=false，OMV按MAC和原ens18IPv6策略持久。任何受控写负测使用另准nonce，不改既有真实文件。
- 三role本地健康与新19URL、21网实际客户端可达；Ops本机textfile与9100新绑定由统一监控验收，不以directCLI代替后台/告警证据。Mac外部探针本期仍停用。

## 已准备代码与当前验证

`patches.py`是纯字节/JSON/XML转换；`guest_transaction.py`是未来来宾本地的受控文件事务，不包含NIC/PVE/OW命令，也不使用SSH密钥。`collect-readonly.py`仅采已批准的公开网络键/结构及公开运维文件hash，实际只读结果见active-readonly-preflight.json；没有输出完整.env、用户凭据或运行配置。OMV RPC实际位于rpc.network.json，参数结构保存在omv-ethernet-rpc-schema.json，准确old/new payload由omv_payload.py纯本地生成。

拟来宾安装目录固定`/opt/dell/network19/services-media`，root所有/不可group-world写；任何执行都先MAC+IP阶段+hostname/AMD64/UUID/local Docker及各role原driver门禁。`preflight --role <250|221|260>`无写；其它动作还需root明确role窗口的32hex nonce（操作确认，不冒充权限凭据）。stage秘密备份与SHA仅留该来宾`/root/dell-network19-media/<role>/<nonce>`700/600，stdout只有状态/role/action和无秘密声明。Network修改不在事务脚本内，需root先停role→新MAC/IP→commit-files→原unit start；回滚须停止role→rollback-files→root恢复旧网络→rollback-start。

本地fixture测试不读取真实.env；覆盖公开键以外字节保留、重复/异常旧值拒绝、Pen lock哈希重算与Git/images/storage保留、改址后admin307新origin/旧origin拒绝、Nexusmarker非IP字段保留、NAS子网/远程禁用保留、MAC限定old/new转场、全量预检、损坏备份与第三方编辑拒绝、部分事务恢复。没有运行任何guest stage/quiesce/commit/start/rollback。

实际NAS网络XML路径与schema已确认，UID/GID2000/mode644将保持；SSH监听all地址且key-only/rootno，SMB未绑定旧接口/地址也没有hosts allow/deny，因此不需改SSH/Samba认证。JF subnets实际为old40/21/127/172.18.0.1；仅替换old40→19。root统一DNS已固定19.1→21.1。
