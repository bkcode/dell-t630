> 当前已由主AI部署：280 NFS/重启/客户端原生验收通过，16targetsUP与5项资源服务指标均1；Lark仅新role增量生效，无人工测试外发。见[交付](../../../completion/20261109-resources/README.md)、[实际监控后检](../../../completion/20261109-resources/final-postcheck.json)。下文和manifest保留原本地候选时点，不代表当前未部署；不得重跑one-shot CAS或重新park已有节点。

# resource-service / VM280：Ops增量候选

状态：**本地准备完成，VM280尚待实际部署/验证，未由本任务启动或远程安装。** 已按root分配固定19.80、2CPU/2GiB、共享prod/test资源角色准备。数据卷实际UUID由root装盘后登记，本目录不格式化、不迁文件、不启动Java、不扩备份。

## 本地修改与未变部分

- `../guest-baseline/install-guest-baseline.py`：ROLES仅加resource-service，role_health_profile仅加`nfs-server.service`、`dell-resources-firewall.service`；原10角色的profile/candidates逐项语义相同。
- `../guest-baseline/guest-targets.json`：保留原10行，追加VM280/19.80，scope明确pending，不把catalog赋值当在线。
- `../guest-baseline/collect-guest-health.py`：**字节未改**。已有collector只接受.service，不把.mount强塞进去，不增加daemon/HTTP/远程探测。
- 挂载由root资源服务原生合同检查：nfs-server.service的BindsTo/RequiresMountsFor依赖srv-resources.mount，ExecStartPre `/opt/dell/resources/guard.py`核实际UUID；firewall先就绪。Ops只读两个serviceactive，不能将unitactive本身当NFS导出/真实mount功能验收。
- `../lark-notify/bridge.py`：ROLES仅加resource-service。ALERTS、LABELS、所有receiver/auth/重试/去重/秘密传递不变，不发消息。原代码备份lark-bridge.before.py是公开源码。

本地10项测试通过：保留旧10profile/entries；新role精确two units/noHTTP/noDocker；collector已有格式可接纳；错误role/hostname/IP拒绝；Prom实际10targets仅append1；exporter仅19.80bind；新Larkrole正向render/所有旧role行为相同/unknownrole和unknownalert拒绝。测试只离线render/mock，不sender、不HTTPsend。

## 实际Prometheus路径（270只读已核）

`/opt/dell/ops/config/prometheus`为RO bind到`/etc/prometheus`。实际配置fileSD引用：

- `/etc/prometheus/targets/guest-node.json` → host `/opt/dell/ops/config/prometheus/targets/guest-node.json`，实际10个guest目标。
- `/etc/prometheus/targets/http-services.json`，现有3行，不改。

现役promtool整configcheck退出0，SHA与原目标原样保留在[prometheus-readonly-baseline.json](prometheus-readonly-baseline.json)。**仓库旧`../config/prometheus/targets/guest-node.json`目前是[]，不得拿它覆盖现役10目标。** 本目录`guest-node.candidate.json`从实际10完整保留后仅追加：

```json
{"targets":["192.168.19.80:9100"],"labels":{"role":"resource-service","zone":"shared","vmid":"280"}}
```

VM280未ready前不要落目标，否则会制造真实down告警。原15总targets若其它5不变，新资源验证后预期16，不计成替换既有Nexus节点或新物理HA。

## 给root的安装staging清单（当前不执行）

280先由root完成网络/hostname/原data UUID/防火墙/NFS守卫、strictSSH；本任务没有280凭据或SSH连接。VM280的NFS客户端/2049端口与Ops70到280:9100网络准入由root明确矩阵验证，不从监控安装推导业务端口全放。

仅将以下3个公开文件放到新280 root-owned staging目录，例如`/root/dell-resource-monitoring-stage`：

1. `infra/ops/guest-baseline/install-guest-baseline.py`（新11role）
2. `infra/ops/guest-baseline/collect-guest-health.py`（原未变）
3. `infra/ops/guest-baseline/guest-targets.json`（新11role）

先核每个SHA/不group-world写，staging是公开工具，不放密码。只在新280主机、原19.80已实际生效后：

```sh
sudo /usr/bin/python3 /root/dell-resource-monitoring-stage/install-guest-baseline.py --install-only --role resource-service
```

这会真实安装/写unit但park exporter与collector，**只在root明确280安装窗执行**。不要对既有10角色批量重跑install-only（会停放其monitor）。source11与installer必须配对；既有runtime10旧pair当前保持，不用单独替一半导致len(ROLES)门禁失败。

root核真实NFS/mount/UUID/firewall功能通过后，将本目录`health.candidate.json`按精确role/IP/root644安装到280 `/etc/dell-guest-monitoring/health.json`。原通用安装默认只有SSH/agent/exporter3基础项，NFS/FW候选不会自动激活；没有真实验证不能先声称监控已覆盖。

```sh
sudo /usr/bin/python3 /opt/dell/guest-monitoring/install-guest-baseline.py --check-private-ip --role resource-service
sudo runuser --user prometheus -- /usr/bin/python3 /opt/dell/guest-monitoring/collect-guest-health.py --check
sudo /usr/bin/python3 /opt/dell/guest-monitoring/install-guest-baseline.py --activate --enable-collector --role resource-service
```

以上仅命令参考、尚未执行。实际验收：仅19.80:9100监听、无0.0.0.0监听，timer运行，原namespace/数据不变，NFS和FW loaded/active，textfile2服务为1，实际数据mount UUID正确。NFS/防火墙可Typeoneshot active/exited；collector看ActiveState，不强迫其成为常驻daemon。

## 通知与Prom应用清单（270独立窗口）

实际桥路径`/usr/local/libexec/dell-lark-notify/bridge.py`；unit `dell-lark-notify.service`。本次只读actualSHA=`12d733376239919ba55c3739ebf8a0564de12ceaad9fba28c75d8632630a41e6`，与本地改动前一致；unitSHA=`682831587cd2d624aec40efb2651e0020a3c64b2630f5b6df88200aae0fc6fbf`，active/running/NRestarts0。详见[lark-readonly-baseline.json](lark-readonly-baseline.json)。

root审阅后按旧SHA精确CAS公开bridge（备份公开旧代码root600、父root700），只加ROLES成员；不改AM renderer/receiver，因原alertname集合没变。真实unit重启仅桥服务使新enum生效，MainPID会改变；需要先核无在途通知、维护窗口，LoadCredential照常，本操作不读token。**不能**运行之前以旧alertnamesSHA写死的备份白名单installer来覆盖这次role增量。部署后核实际新SHA/原bind172.18.0.1:19093/active，不发测试通知。

当280已ready且9100只读GET/textfile通过，root对实际guest-node.json做CAS增量：

1. fresh SHA必须等manifest的runtime_Prometheus_guestnode_old_SHA256，原target组精确等只读baseline；漂移则重读重新审候选，不能盲覆盖。
2. root保留原bytes/mode，按同目录临时regular文件+fsync/replace落`guest-node.candidate.json`，**只这个fileSD文件**；配置、规则、http-services、secrets和容器不动。
3. 原Prom容器`/bin/promtool check config /etc/prometheus/prometheus.yml`复核；fileSD会自动刷新，不需要recreate或为一个target改Promcommand/lifecycle。若要HUP须另有具体批准，不能原样调用其它installer。
4. 等实际targets API出现唯一vmid280、11个node全UP、其它原目标保持；确认本机NFS/FW指标为1，原Lark通道仍正常。文件存在不等于已抓取/告警可送达。
5. 失败仅当目标file仍本次新SHA时恢复旧bytes，不动其它目标/告警配置；不删除280数据或关闭NFS来凑状态。

## 明确未做

没有修改PVE/VMIP/ACL、启动280、安装guestbaseline、写270target/桥、读取secret/Env/Cmd、修改其它agent目录、发Lark或扩备份。prod/test只是同一受控资源服务的客户端范围，不代表数据库环境合并或迁数据。现有backup scope仍正式DB/Nacos；Java不部署，Macprobe不恢复。

SHA/路径与候选状态见[manifest.json](manifest.json)，功能断言测试见[test_candidates.py](test_candidates.py)。所有后续实际结果由root独立收据签收。
