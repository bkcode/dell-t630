> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 单一 Java21 验收模板（9011）

用户当前范围是**不部署Java业务程序，只保留一份Java验收模板**。本目录只针对主AI从干净9010派生的新9011，不复用旧Java/Publisher业务模板，也不改变9010、Docker模板或三prod节点的数据。

主AI临时正常停232释放16GiB，创建9011构建实例2CPU/2GiB、19.197、MACbc:24:11:a4:d3:4d、hostname java-acceptance-build。PVE创建、预算、shutdown/template及9012 QA clone由主AI独占；模板停止后不增加常驻来宾内存。磁盘继承干净9010的32GiB sparse，不缩盘。

## 当前实际状态

- `build-evidence.json`：9011已安装Debian OpenJDK JDK/JRE **21.0.13+9-1~deb13u2**，java/javac均21；新增java系统用户UID999、nologin、独立空home。
- 通用`/usr/local/libexec/dell-java-acceptance/verify.py`已由nonroot java真实临时compile/run通过，源码和class自动清理。没有持久业务JAR、Gradle/Maven仓库、Nacos/DB/Redis/MQ/Publisher配置、Docker或凭据。
- 基础监控为CPU/load/memory/disk只读验收及已安装的node_exporter1.9.0；exporter service/socket保持masked/inactive、无9100监听，不烘焙某角色IP或监控target。
- `clean-evidence.json`：主AI审阅后只清理9011，machine-id为nextboot reset，全部host SSH keys、root/ub authorized_keys与CI seed/instances清除，磁盘网络配置没有19.197，hostname为通用localhost，/opt为空。保留JDK、java、通用verify脚本和masked exporter，未执行shutdown/reboot。
- **主AI已将9011封为停止模板，并full-clone QA9012（19.198）。** 首启IP/CI/QGA通过，但generic profile使hostname=localhost；主AI随后仅为9012注入独立profile显式hostname并正常重启。`clone-evidence.json`已实测hostname java-acceptance-clone-check、strict SSH、machine-id/hostkey不同builder、JDK21 nonroot smoke、无业务目录/单位/监听及exporter停放全部通过。9012已明确释放给主AI继续仅/run DHCP验收与销毁；本子任务不把销毁/232恢复写成已完成。

## 脚本边界

| 文件 | 范围 |
| --- | --- |
| build.py | 仅fresh9011准确MAC/IP/hostname，apt最小JDK21 headless+exporter；临时policy-rc.d禁止daemon启动并完整恢复；无PVE动作 |
| verify.py | 通用镜像内脚本，没有固定IP/VMID；仅java非root身份，检查JDK21、无业务目录/监听/persistent JVM、exporter停放、基础OS状态 |
| clean.py | 仅fresh9011，先核cloud-init clean flags；清builder身份/生成网络/密钥/历史；不重启、关机或转换模板 |

`build.py`和`clean.py`只经受控SSH执行，不放进镜像；它们包含本次9011管理身份守卫。镜像内只保留通用verify.py。所有凭据值不进入argv/env/普通证据；客户端私钥留Mac，证据只含公钥指纹或身份hash。

实例验收命令（在主AI批准的clone内）：

```bash
sudo runuser --user java -- /usr/bin/python3 /usr/local/libexec/dell-java-acceptance/verify.py --smoke
```

该脚本的network_or_external_messages_sent=false仅指验收过程不做应用联网/通知，不包括已授权apt包下载。它不是业务服务，不创建监听端口或定时任务，临时源码/class自动删除。将来需要9100时须按该实例实际地址/角色单独授权与绑定，不在模板默认开放0.0.0.0。

## 清理与克隆身份

本次clean已先验证`cloud-init clean --help`支持`--logs --machine-id --seed --configs network`，再执行官方清理。剩余仅生成50-cloud-init.yaml若残留19.197才定点删除，未扫除其它手工网络文件；hostname/hosts中builder标识替换为通用值。仅删除root/ub授权文件与histories、host SSH keys和本脚本创建的临时smoke目录，不读或复制private key内容，不触其它VM。

镜像内身份配置显式`ssh_deletekeys:true`、`ssh_genkeytypes:[ed25519,rsa]`、`ssh_pwauth:false`，没有复制190专用`ssh_deletekeys:false`。CloudInit清理后的9011不可先启动再转模板，否则会重新生成身份。9011清理时运行IP只为返回回执保留，磁盘配置已清；随后主AI已统一shutdown/template并设置generic Linux user、DHCP/19网。**每次clone必须生成独立custom user profile，显式注入该实例hostname并保留通用ub/公钥认证基线。** 使用generic cicustom user时，不能保证PVE VM显示名自动进入guest hostname；9012首启localhost已说明这一依赖。网络IP/网关/DNS仍由该实例独立CI网络配置指定，9011模板不内置角色名或IP。

## 每个clone的hostname与SSH身份契约

原说明把“独立CI元数据会设置hostname”说得过强，现已纠正。9012实测generic cicustom user使guest继续使用模板的通用localhost；主AI已只读确认本次PVE生成meta-data仅含instance-id。不能假设meta-data带local-hostname，也不能声称VM显示名自动覆盖custom user-data。

新clone应在**首次启动前**从通用user profile派生其专用profile，显式设置`hostname`及`preserve_hostname:false`，同时保留原ub、pubkey认证与其它通用基线。模板9011继续generic/ssh_deletekeys:true、无角色hostname；不要把某个QA的profile或false设置反写进模板。每实例user profile的实际内容需校验，不能仅检查PVE显示名。

对于已经首启生成独立host key的本次QA9012，主AI已实际使用仅9012的profile增量并通过正常reboot与strict SSH：

```yaml
# 这是对通用user profile的实例增量，不是可替代users/key基线的完整配置
preserve_hostname: false
hostname: java-acceptance-clone-check
ssh_deletekeys: false
```

该false仅保存**已经生成的QA9012** host key，便于本次改profile后的正常reboot严格复连；它不是新clone的通用身份策略。新实例依然由清洁模板和首次CI生成独立host keys/machine-id。重启前后对比9012本机公钥指纹与machine-id hash，不能与9011复用同一个信任别名或自动忽略hostkey变化。

Cloud-init的set_hostname模块按instance运行，update_hostname每次boot运行，但preserve_hostname和有效输入/缓存会影响结果。若本次profile更新后正常重启仍未生效，先核有效hostname配置与cloud-init执行状态；不要为修hostname重新clean machine-id/hostkeys。主AI可针对9012选择受控模块重跑或QGA的hostnamectl定点修正，并独立保留该差异；这不取代“下一clone首次启动前注入专用profile”的使用要求。验收记录只保留hostnames/状态/公钥指纹，不将完整含授权键的user-data输出到普通证据。

## 验收标准

| ID | 前置 | 步骤 | 可观察通过条件 | 证据 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| JTPL-01 | root创建fresh9011、停232预算 | 验VM guard/必要包、无业务污染 | 2CPU2GiB、准确MAC/IP、Debian13；JDK21与nonrootjava | build-evidence.json | 通过 |
| JTPL-02 | java nologin、通用脚本 | nonroot compile/run临时源码 | java/javac major21，执行user=java，源码/class删除，无业务/9100监听 | build-evidence.json | 通过 |
| JTPL-03 | root审clean范围 | 官方CI clean及定点身份清理 | machineID reset、hostkeys/authorized/seed/instances gone、无19.197配置、/opt空、exporter仍masked | clean-evidence.json | 通过 |
| JTPL-04 | 主AI统一关机/CI DHCP/template9011 | 检查PVE只停止模板与generic CI | 无固定hostname/IP，linux基础/Docker模板不变，无常驻内存增加 | 主AIsealed/template操作回报（最终receipt由主AI归档） | 主AI已完成，停止模板 |
| JTPL-05 | root创建9012 CI19.198/新MAC，独立user profile显式hostname | 核有效hostname字段→QGA指纹可信链→新strictSSH→generic smoke与清洁检查 | hostname等于独立profile；machineID/hostkey与builder不同；JDK21/nonroot、CI done、无active业务；QA随后停放 | clone-evidence.json、QA-target.json | 通过；QA已释放，后续DORA/销毁由主AI执行 |

## 9012实际验收结果

`clone-evidence.json`十个检查全部true。hostname来自独立profile；machine-id SHA `6b9806eb4b178b335c8b41fd502622672199291382ed541c5b3528e13c27ba62`不同builder，ED25519指纹也不同builder且与主AIQGA可信记录相符。通用verify SHA保持，java/javac21.0.13、java UID999临时编译执行通过且文件自动删除。没有安装业务或开启exporter、没有修改PVE/guest网络。

## 官方来源

[Debian13 openjdk-21-jdk-headless](https://packages.debian.org/trixie/openjdk-21-jdk-headless)提供AMD64 headless JDK21并配套JRE；本次实际包版本由9011 dpkg证据记录。[Cloud-init clean官方文档](https://docs.cloud-init.io/en/latest/reference/cli.html#clean)说明machine-id、seed、生成网络与日志清理；具体选项本次已用9011本机help核对。

Hostname机制参考[Cloud-init set/update hostname官方文档](https://docs.cloud-init.io/en/latest/reference/modules.html#set-hostname)；本段操作建议未由本子任务在PVE或guest执行。
