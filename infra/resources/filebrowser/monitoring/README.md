> 已退休（2026-11-10）：FileBrowser unit/HTTP检查已从280健康配置移除，资源只保留原5项NFS角色服务；旧FileBrowser指标不存在，不新增或删除280 node target。当前[健康规范](../../../../completion/20261110-nfs-only/health.nfs-only.json)和[后检](../../../../completion/20261110-nfs-only/final-postcheck.json)优先。**以下六服务、HTTP/HTTPS/CA候选与历史安装回执仅保留来源，不再作为现役监控部署入口。**

> 最新内网HTTP策略：FileBrowser健康检查已改为`http://192.168.19.80:8080/health`、名称`filebrowser-http-health`，不带ca_file；账号/NFS及六服务合同保持。见[本轮HTTP交付](../../../../evidence/internal-http-20261110/README.md)。下方专属CA/TLS回归是首次HTTPS阶段的历史支持，不代表当前还要求证书。

> 已由主AI完成实际部署，当前6服务＋专属CA HTTPS健康检查UP，16targets保持；见[安装回执](../../../../completion/20261110-filebrowser/monitoring-installed.json)和[最终后检](../../../../completion/20261110-filebrowser/final-postcheck.json)。下文记录初始候选阶段；旧manifest单独保存在manifest-preparation.json，不能据旧pending描述重放安装或回退当前服务。

# FileBrowser Quantum原生服务：监控候选

当前仅本地准备，没有写VM280/270、启动FileBrowser、采集器/Prom重载或外发消息。唯一原有源码变化是`infra/ops/guest-baseline/collect-guest-health.py`的可选专属CA支持，其原HTTP/默认HTTPS行为保持；其它原有profile、installer、Promtarget、规则、Lark源码均不改。

## 六服务与HTTPS合同

`health-services.candidate.json`保留280既有五检查（ssh、QGA、exporter、nfs-server、dell-resources-firewall），仅追加`dell-filebrowser.service`为第六个。它是候选，不代表已安装或active。

FileBrowser拟为官方native+systemd，TLS origin `https://192.168.19.80:8080`，state/cache独立`/var/lib/dell-filebrowser`，不把它放进NFS数据或Docker。UID2000/sharedgroup2980及来源21LAN/WG10由root服务安装和防火墙合同控制，不由监控脚本配置。没有Java、业务图片URL或文件迁移。

官方v2.1.4-beta源码已确认原生`GET /health`匿名200/message=ok；health.candidate.json现包含精确HTTPS URL与公开CA，原生TLS/Prometheus读回通过。health-services.candidate.json仅保留最初服务项组件，不是当前完整active配置。

路径确定且真实TLS就绪后，由root精确追加一个check（以下schema仅示意，不能原样加入nullURL）：

```json
{"name":"filebrowser-https-health","url":"<已确认origin+官方health路径>","ca_file":"/etc/dell-filebrowser/tls.crt"}
```

## 专属public CA安全语义

- 新字段`ca_file`可选，只允许HTTPS、精确`/etc/dell-filebrowser/tls.crt`。HTTP带CA、其它路径、null/headers/credentials/query均拒绝。
- 文件必须是bounded <=64KiB、root-owned regular、非symlink（包括祖先）、祖先root且无group/worldwrite；CA文件无group/worldwrite且worldreadable，当前collector账号必须可读。建议root:root0644；它是公开证书，不是tls.key。
- 只接受包含public certificate PEM且没有PRIVATE KEY标记；不读取TLS私钥、Basic/Bearer、cookie或其它秘密，不把CA正文写入metrics。
- `ssl.create_default_context(cafile=...)`建立该检查自己的CA上下文，显式保留`CERT_REQUIRED`及`check_hostname=true`；不关闭验证、不改系统全局信任。证书SAN必须匹配IP192.168.19.80，链/用途/有效期也由标准库TLS校验，不能为自签证书加insecure。
- 新CA分支使用无代理、NoRedirect；错误证书/主机名/网络失败为up0/status0，HTTP503为up0/status503。没有掩盖失败或改认证。
- **无ca_file的旧分支**继续原`build_opener(NoRedirect)`、GET/timeout3/read1024/原异常状态行为，collect仍只传原单参数；旧检查无需改JSON、不能因加入专属CA改掉它们的默认系统证书行为。

## 指标、规则和目标保持

沿用`dell_guest_service_present/active`与`dell_guest_http_up/status_code`；只新增resource-service下一个service与一个check标签。原通用`GuestManagedUnitUnavailable`和`GuestLocalHealthUnavailable`规则覆盖，不需新rule、receiver或Promtarget；resource-service已在原Larkrole enum支持，新规则名称不增加。Prom总16保持，新服务通过280原9100 textfile采集，不打开270→8080新抓取目标。

本地规则判断依据公开`infra/ops/config/prometheus/rules/infra.yml`；现役加载与实际新series仍须root部署后查询证明，本地源码通过不是运行态告警验收。没有testsend或新消息授权假设。

## root应用顺序（当前不执行）

1. root/acceptance确认官方health路径、native TLS参数；FileBrowser原unit/data/firewall/CA安装好且来源限制经实际验证。CApublic root644，TLSkey不得作为CA选入；其私钥权限由原服务合同管理。
2. 在VM280 fresh读当前collector源码SHA和`/etc/dell-guest-monitoring/health.json`，记录原bytes/权限及现五服务。未提供一个通用“覆盖全部guest”的工具；此次只280，不修改其它guest运行采集器或重跑baseline install-only。
3. 以manifest旧SHA精确CAS替换280 `/opt/dell/guest-monitoring/collect-guest-health.py`（保持原root755）；若漂移先重新审，不拿旧baseline盲覆盖。仅在现五服务精确匹配候选时加第六service；再加已确认官方HTTPS check，不带任何认证值。
4. 不restart应用、exporter或Prom。先以prometheus账号运行只读check：

```sh
sudo runuser --user prometheus -- /usr/bin/python3 /opt/dell/guest-monitoring/collect-guest-health.py --check
```

`--check`会真实执行本机GET/选定unit读但不写metrics。必须CA可读、TLS验证通过、新service present/active和HTTP200；不能只看命令exit0，因为网络up0本身仍属成功采集，应人工查状态/metrics。

5. root给明确采集窗后执行该已装collector一次或等既有timer，核280:9100的6服务/新check up1，Prom实际API仍16targets UP，新metric标签可查询。采集器只写自己的textfile；不为一个CA检查重启Prom/bridge或安装全局信任。
6. 故障/回退只恢复本次collector与health两份bytes（若当前SHA仍本候选，第三方变化拒覆盖），保留原五服务；不删除FileBrowser数据/CA/账号，不改变其它角色。未实际演练回退，不宣称运行态完成。

## 本地回归

- 新10项测试通过，包括schema/path/UID/mode/ancestor/symlink/private-key拒绝；legacy collect与old指标逐字一致、旧opener调用相同；真实loopback TLS专属CA成功、系统CA拒自签、错误CA/hostname失败、503真实状态。
- 既有`test_guest_baseline.CollectorSafety`十项全部通过。只跑相关collector旧回归，不把本仓库其它历史12role/10.63测试的预期当本次现役目标。
- 首次sandbox禁止loopback端口，3个TLS测试未执行；随后经工具批准只本地127.0.0.1随机端口/临时合成cert+key重跑全10项通过。没有访问服务器或触碰真实TLS材料。

测试命令：

```sh
python3 -B -I infra/resources/filebrowser/monitoring/test_collector_ca.py
```

需要允许本地loopback fixture绑定端口；不需要外网、Docker、secret或Nacos/MySQL访问。旧source备份是公开代码`collect-guest-health.before.py`，哈希与候选见manifest.json。root确认health路径后再完成最终HTTP候选与native运行态证据。
