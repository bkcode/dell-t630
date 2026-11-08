> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 220承载Nexus31与节点退役：网络准备包

**本文件记录本地准备方案；后续source CAS由主AI完成，190 DNS-only已按独立窗口执行，见[dns-runtime](dns-runtime/README.md)。** Nexus221当前仍运行、alias合并未由本子任务应用。以下合并/退役模型不代表Nexus已搬迁。 主AI已选择：230/240保留，231/232退役；Nexus221服务迁到220，220 OS hostname仍publish-service、primary19.30，19.31作为同NIC第二服务IP；6CPU/8GiB资源由主AI统一调整。

结论：保留31可以保留Nexus客户端URL和artifact-service DNS。实现重点是把**物理VM/NIC身份**与**逻辑服务endpoint**分开：31只换物理所有者，不删除逻辑服务。当前单IP模型不能直接套用；本目录提供三个源文件候选与独立diff，均未覆盖原文件。

## 包内文件与预期源改动

| 准备文件 | 未来目标源文件 | 最小变化 |
| --- | --- | --- |
| candidates/control.py + diffs/control.py.diff | dell/scripts/control.py | 多IP仅在唯一role明确additional_ips时允许，primary必须在QGA结果，未知uplink IPv4拒绝；同NICaliases，默认仍返回primary；hostkey变更保护不弱化 |
| candidates/render-bridge-acl.py + 对应diff | dell/network19/audit/render-bridge-acl.py | 一NIC row带ips；同MAC一份、端口/IPtuple可多份；显式retired_vmids跳过物理身份；Nexus目的解耦service_endpoints |
| candidates/gateway-policy.py + 对应diff | dell/network19/gateway/policy.py | DNS编译跳过退休物理host，同时保留逻辑artifact-service31（owner220） |
| dns_delta.py | 本地审查gate，不直接安装190 | 只准删Java41/42两DNS记录；强制artifact31/publisher30与所有FW/WG/MAC/管理字段不变 |
| proposed-model.json | 输入提案，不是active plan | 220 aliases31；artifact endpoint owner220/IP31/TCP8081；本次显式retired集合 |
| test_candidates.py / validation.json | 离线fixtures/结果 | 当前19项通过；不连接SSH/Docker/nft，不证明native或迁移完成 |

候选文件保留未来目标位置的ROOT/HERE语义，不能在candidates目录原地当生产CLI运行；fixture只导入纯函数并显式替换/传入测试路径。`base-manifest.json`记录所读当前源SHA。未来应用前需重新比对，若源漂移，不可直接覆盖候选。当前源、当前plan和现役网关未被本包修改。

## 单NIC两IP身份模型

已读本地最近registry：220 MAC `bc:24:11:2a:01:ad`；221旧MAC `bc:24:11:ec:e1:6f`。目标保持220这个NIC/MAC，仅批准30+31两个IPv4，不复制第二张同MAC NIC行。

| 对象 | primary | additional/service | 物理身份 |
| --- | --- | --- | --- |
| publish-service/VM220 | 192.168.19.30 | 192.168.19.31 | 单net0、MAC保持220 |
| artifact-service逻辑服务 | 无新增VM primary | 192.168.19.31:8081 | owner VM220；不是第二个常驻VM |
| VM221/231/232 | 退役后不再active | 不重新分配其旧身份 | root备份/停机/断NIC或删除后从registry排除 |

未来两份canonical数据需由主AI一致生成：active plan的220 role `additional_ips:[31]`供SSH控制使用；网络模型220 guest_address同样声明additional_ips，另有`service_endpoints.artifact-service={vmid:220,ip:31,tcp:[8081]}`与retired_vmids。不要把artifact服务再作为第二个vmid220 role累加CPU/内存，也不要为了保DNS而保留221的幽灵VM身份。

控制面fixture包括：QGA先报31仍选30；未知32/缺primary/未声明多IP/第二NIC别名/重复active owner拒绝；声明但尚未落alias时可继续经primary30管理；现有Docker br-/docker0排除规则保留。任意hostkey变化仍拒绝，不把旧dell-vm221指纹覆盖成220；管理走30和dell-vm220。190双NIC仍使用既有trusted info，不把它当本次同NICalias特例。

## PVE bridge最小变化

`mac_ids`只保留一次220端口→220 MAC；`ip_ids`批准：

```text
"tap220i0" . 192.168.19.30
"tap220i0" . 192.168.19.31
# 既有兼容fwpr220p0端口名同样两tuple，但当前PVE仍direct tap/firewall0
```

ARP的SHA/SPA、IPv4 source与destination都通过这套tuple检查，因此两个地址必须同时登记。不能用全19网IP放开或去掉MAC绑定；候选拒绝同一IPv4被另一个active物理VM占有。旧221/231/232即使为回退保留停机配置，retired集合也让其tap/fwpr MAC/IP身份完全不进入active ACL，而不是降成可DHCP的未知业务角色。

Nexus peer从hardcoded `add(source,221,8081)`改为逻辑endpoint31。保留230→prod200/201、240→test210、publisher220→240既有边界；移除231/232相关source/9100tuple。Ops只保留220 primary30:9100，不额外给31:9100建立第二套主机指标。

现有guard顺序不变：源MAC/ARP绑定、目的MAC/IP绑定、invalid先检查，随后才trusted WG规则。fixture证明from_gateway整段与当前renderer逐字相同，WireGuard10.66.66/24全19规则不改变；PVE host L3 forward0/NATnone、IPv6/VLAN拒绝均保留。bridge候选仍需root在PVE native nft-c并原子替换唯一owned bridge表；本包未做这一步。

## 220地址持久化、ARP与来源选择

执行前主AI/服务owner读取220**实际**networkd NetworkFile与MAC，不猜eth名或覆盖CI生成文件。选一个网络配置所有者：现有networkd对应文件的受控drop-in，或每实例CloudInit custom network显式两个Address；不能两套同时维护。第二地址可考虑独立[Address]及PreferredLifetime=0，使未绑定的新出站连接优先继续使用primary30，同时31仍供明确绑定的Nexus入口。默认网关保持唯一19.1、DNS不变，不新增第二NIC/第二默认路由。

修改CI资料前需核当前实例hostname、ssh_deletekeys与instance-id行为，不能因alias改动默默再生host key或跳过严格验证。发布SSH来源要实际仍为30，受限发布保持当前fence，不为了验证源地址重新启业务发布。

旧221必须先停止服务并断开/隔离NIC，确认不再声明31，再把31给220。发受控GARP或由root精确更新GW对31的邻居，验31的新MAC为220。保留URL不等于保留旧TCP会话：旧HTTP连接可能中断，维护窗口与只读验证必需。移除alias/恢复旧221也要反向更新邻居，禁止两台同时拥有31。

同VM内30↔31通常走本机，不再经过PVE bridge；alias不能维持原两个VM的安全隔离。Nexus/Publisher必须继续独立Unix身份、数据路径、容器/代理边界；publisher不得被加入docker组。Root/Nexus运行guard必须改为物理owner220/hostname publish-service+alias31实际存在，不能继续信任vmid221。Nexus对外URI、Docker发布HostIP和客户端仍31:8081；出站可能使用primary30，不能假设旧31 source策略自然保持。

## DNS与退休记录：190只需受控DNS更新

网关runtime hosts只含role/address，本身不绑定VMID，所以artifact-service→31可保留。新编译模型移除221物理row后由logical endpoint补回该DNS记录；审定退休静态记录才删除（见下表）。fixture证明新旧`nft()`输出字节完全相同，WGfull对象也完全相等，**不需要改网关FW/NAT/route/forward**。

当前Gateway hotdelta只准兼容feature新增/升信任，不能直接用它绕过hosts清理。未来单独DNS-only窗口应：

1. root冻结190 live config/dnsmasq.conf与实际MAC接口名、leases权限/状态；编译候选，`dns_delta.py`证明除hosts/planSHA外所有字段完全相同，artifact31/publisher30保留，只删审定退休静态名单。
2. native dnsmasq --test候选，备份owned config+dnsmasq.conf；保留现有lease文件、owner600与当前DNS UID/三cap，**不得调用首次fresh lease预建逻辑或清空租约**。
3. 原子写持久config与dnsmasq.conf后，**只受控restart dell-gateway19-dnsmasq.service**。host-record在主conf，SIGHUP不重读主conf，不能仅HUP就称已更新。不要重启networkd/FW/ready，不改sysctl或nft；当前实现不是“热更新整个网络”。
4. 查artifact31/publisher30/保留节点A记录、退休名称不再返回旧地址、LAN DNS/DHCP服务恢复、forward三1/WG/nft/route保持。失败恢复两文件并仅重启同DNS unit；root安排维护窗口，不用PVE fallback L3/NAT。

## 监控与退役身份

本轮只读发现：public Ops targets空列表是默认模板，private Ops bundle的targets仍有旧10.63地址；二者都不能代替现役270。root已负责冻结真实scrape目标，本包不对这些源执行通用prepare或覆盖active Lark。

退休后删vmid221/231/232的OS node target；220保留primary30:9100，不能把旧31:9100换标签继续重复抓同一主机。Nexus健康可在220 local collector新增unit及本机31:8081 status检查（该IP须实际出现在220 local_addresses），通过现有30:9100上报；或另行批准单独logical HTTP target，owner_vmid=220而非遗留221。保留既有Lark和其它目标，目标数量按冻结集合差异计算，不能强行凑旧17。

同步清理角色候选、guest-targets、Grafana节点选择、retired DNS、SSH控制inventory与后续源码；历史验收、私有备份与旧已知hostkey档案应归档而非全局sed。与data owner复核可能存在的退休Host授权，不删230/240/Nacos仍用账号；此任务不读取或操作SQL/秘密。

## 建议切换与回退顺序

1. 先由root/media冻结真实runtime、应用一致性Nexus备份/数据验证、当前ACL/plan/网络/270 targets；在220只准备包，不抢31、不启动与旧31冲突的入口。
2. root进入维护，按确切retiring目标处理监控；停止Nexus221并断NIC/onboot，Java231/232也各自正常停止后才清其身份。可分阶段退役，不能先把还在用的节点从ACL删掉。
3. root将物理plan/registry改为220 primary30+alias31、logical artifact31、retired集合，native-check并原子应用bridge，然后服务owner在220持久化31/启动恢复Nexus。使用受控GARP/邻居更新完成MAC换主。
4. 正向验旧URL31:8081与DNS、认证/构件SHA、publisher管理source30、Ops单主机+Nexus健康；反向验未声明32与旧221/231/232 source-MAC/IP不能通过，原prod/test隔离与WG访问保留。
5. 成功后root处理190 DNS-only退休记录、270真实targets/源码/预算，最后决定删除物理退役VM。回退先停新Nexus并撤31，再恢复旧221身份/ARP/服务；新仓库若接受过写入，必须由媒体owner处理应用一致性反迁，不能简单启旧数据副本。

本目录不包含执行PVE、190或guest切换的授权。待root读审开窗后再由各owner应用，不能直接运行当前refresh-bridge脚本，因它会收集并立即apply当前模型。

## 离线验收与待执行项

| ID | 前置/步骤 | 可观察条件 | 证据 | 状态 |
| --- | --- | --- | --- | --- |
| CN-01 | 声明alias/primary的QGA fixtures | primary默认30、未知/缺primary/双NIC/hostkey变化/重复owner拒绝 | test_candidates.py | 通过（离线） |
| CN-02 | 选定model+本地inventory渲染 | 220一MAC row、30+31tuple；退休身份无，Nexus peers保持 | validation.json | 通过（离线） |
| CN-03 | 新/旧GW compiled config比较 | artifact31保留、只删审定退休静态名单；nft/WG字节不变，错delta拒绝 | dns_delta.py/tests | 通过（离线） |
| CN-04 | root冻结live并开维护窗 | native nft-c/alias持久化/ARP所有权/应用SHA与ACL真实包正反验证 | 未来implementation证据 | pending |
| CN-05 | 仅190 DNS窗口 | test+DNS unit重启后A记录正确、无FW/route/sysctl变化 | 未来DNS证据 | pending |

机制依据：[systemd.network多Address及PreferredLifetime](https://manpages.debian.org/trixie/systemd/systemd.network.5.en.html)、[nftables concat sets](https://wiki.nftables.org/wiki-nftables/index.php/Concatenations)、[dnsmasq SIGHUP语义](https://manpages.debian.org/trixie/dnsmasq-base/dnsmasq.8.en.html)。这些说明配置机制，不代表本次native或packet验收已执行。

## 追加明确名单与临时Fish bootstrap

主AI现已审定可删除的静态DNS对应VMID：101、104、231、232、9000、9002、9003、9004、9005、9006、9020。candidate退休物理集合另包含221，但**artifact-service31逻辑DNS不可删除**。

| VMID | 已知静态角色 | IP |
| --- | --- | --- |
| 101 | data-docker-base-tpl | 19.101 |
| 104 | publish-legacy | 19.104 |
| 231/232 | java-prod-02/03 | 19.41/42 |
| 9000 | dell-template-inspect | 19.190 |
| 9002/9003 | dell-linux-clone-test / dell-docker-clone-test | 19.191/192 |
| 9004/9005/9006 | dell-docker-clone-a / dell-linux-clone-b / dell-docker-clone-b | 19.193/194/195 |
| 9020 | dell-restore-baseline | 19.196 |

`dns_delta.py`只删除上述审定pair中**当前实际存在**的记录，不要求已删掉的项重新出现；不允许加新记录、删其它live记录，artifact31/publisher30必须保留。fixture同时证明gateway nft字节相等、WGfull与MAC/FW/egress/管理字段保持。

Fish builders9040/9041/9042的19.197/198/199只作本次L2 bootstrap。若root把这些临时IP行放进渲染输入以登记MAC/IP，应同时显式`temporary_bootstrap_vmids:[9040,9041,9042]`；bridge只用于临时端口身份/基础网关出站，不自动派生Ops9100 peer，gateway DNS编译器完全排除它们。不得把这些行写成长期服务角色/DNS，不能以临时builder代替artifact owner。root停止/销毁builders后必须从临时输入行、temporary集合和实际registry移除，重新native检查/刷新bridge，确认旧MAC/端口/IPtuple不在active表中；不要保留“能DHCP就算清理”的身份。

Native变更范围仍不变：仅DNS配置语法检查与单独DNS unit受控重启（主conf不能只HUP），不改变WireGuardfull10访问、NATnone、hostforward0、DNS监听、转发sysctl或网关接口/MAC。所有native/packet结果继续pending维护窗口，本追加只是本地model/fixtures。

## 临时candidate与独立QA范围更新

本地候选仅接受temporary_bootstrap_vmids集合9040–9045：9040/41/42为Fish候选builder，seal并转临时template后，9043/44/45分别clone作fish-qa-linux/docker/java。19.197/198/199只能在源builder停止并从active静态登记移除后复用给QA，bridge继续拒绝两个active物理所有者同时声明同一IP。六个ID均不生成190长期DNS或自动Ops9100 peer，范围外9046等拒绝。

原长期模板9001/9010/9011须由主AI在备份和三个candidate独立QA通过后才决定替换；本包没有替换或操作这些模板。临时QA最终也须停止/销毁并移除登记。


9040..9045小修验证：输入既可显式temporary_bootstrap_vmids，也可使用root当前raw行temporary_build_only:true，二者并集仍严格限制这六个ID且不能与retired相交。fixtures固定保存在fixtures/，旧模型基线剔除临时六ID，避免把刚追加的builder raw行误当作现役190 DNS事实。构建阶段与QA阶段分别测试，同IP同时两active owner仍拒绝。当前22项离线回归通过，base源码SHA未改。
