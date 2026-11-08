> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 三类模板 fish 构建窗口

当前9040/9041/9042均已完成fish安装、新strictSSH验证和独立授权封版；9040原netplan门禁拒绝与9041原profile门禁拒绝均留存，批准修订后通过。root已停三builder并转candidate，独立QA9043/9044/9045均通过且释放；原模板备份、替换和最终metadata/image一致性由root负责，不由QA通过推断已完成。PVE所有创建、关机、磁盘备份、替换和删除由root独占。原模板9001/9010/9011不启动。默认root/ub登录shell保持原值，本轮不chsh、不配置fish或插件。

| Builder | 来源 | 严格hostname | 严格IPv4 | 资源 |
| --- | --- | --- | --- | --- |
| 9040 | 9010 Linux | fish-build-linux | 192.168.19.197/24 | 2CPU/2GiB |
| 9041 | 9001 Docker | fish-build-docker | 192.168.19.198/24 | 2CPU/2GiB |
| 9042 | 9011 Java | fish-build-java | 192.168.19.199/24 | 2CPU/2GiB |

MAC必须由root实际分配后写入，示例值不能作为真实目标。root用QGA核对MAC/IP/hostname/SSH host fingerprint，再给strict SSH target。不能直接信任ssh-keyscan，也不改其它guest的known_hosts。

## 执行包与阶段门禁

`template-builder.py`复用相邻`install-guest.py`的已验fish安装流程，只替换独立builder名单，不更改原永久guest名单文件。两文件放目标`/root/dell-fish-template-stage-VMID/`，root拥有、目录700、脚本644或600、contract和window600。seal只接受该精确stage，且其中只允许以下文件：

- template-builder.py、install-guest.py
- contract.json、install-window.json、seal-window.json

contract结构（MAC由root补齐）：

```json
{"schema_version":1,"vmid":9040,"source_template":9010,"hostname":"fish-build-linux","ip":"192.168.19.197","mac":"ROOT_ASSIGNED_LOWERCASE_MAC","fish_version":"4.0.2-1","no_chsh":true}
```

window结构：`vmid`、`allowed_phase`（install或seal，不能互用）、`expires_at`（带时区ISO时间）、`contract_sha256`。摘要为Python `sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode())`，不依赖文件空格。root生成窗口文件并确认备份/模板事务，不因check成功自动获得seal许可。

目标guest内命令模板：

```sh
sudo -n python3 -I -B /root/dell-fish-template-stage-9040/template-builder.py --contract /root/dell-fish-template-stage-9040/contract.json --phase check
sudo -n python3 -I -B /root/dell-fish-template-stage-9040/template-builder.py --contract /root/dell-fish-template-stage-9040/contract.json --phase install --window /root/dell-fish-template-stage-9040/install-window.json
```

check不写文件（Java既有非root验证脚本会创建并自动清除专用临时编译smoke）。check采集OS/CI/精确IP+MAC/资源，以及壳与类型特有保护SHA；失败不调用APT或seal。安装只新增精确fish/fish-common4.0.2-1及必须依赖，先APT模拟拒绝任何已装包upgrade/reinstall/removal。no-install-recommends/no-upgrade/NEEDRESTART_MODE=l，不apt update/fullupgrade/autoremove，不主动重启服务。成功留root600 `/root/dell-fish-builder-VMID.json`，只含非秘密基线、shell、源保护SHA、机器身份摘要与公钥fingerprint。新strict SSH由调用端另验。

root收取成功安装receipt到本机普通evidence，再另给seal窗口：

```sh
sudo -n python3 -I -B /root/dell-fish-template-stage-9040/template-builder.py --contract /root/dell-fish-template-stage-9040/contract.json --phase seal --window /root/dell-fish-template-stage-9040/seal-window.json
```

seal清machine-id、生成hostSSHkeys、CIseed/instances与网络缓存、构建IP生成文件、固定hostname/history/生成authorized_keys，恢复localhost及firstclone ssh_deletekeys:true/preserve_hostname:false。PVE generic cicustom公共ub用户/授权公钥不动，由下一clone重建authorized_keys；不复制client私钥。只删除确认为cloud-init生成且含当前builderIP的静态网络文件，遇未知配置拒绝。删除自己精确stage及receipt，apt clean/sync；不关机、不重启、不做PVE操作。seal后运行中的builderIP/SSH连接暂保留；root随后正常关机，**不得再启动该sealed builder当运行机**。

seal任何阶段失败均为真实失败，不能直接转模板；root用现有QGA/控制台诊断，清理后的身份不可强行恢复成另一业务VM的身份。

## Docker与Java保护

9041原模板实测Docker29.9.3、`/var/lib/docker` rootful、driver=overlayfs（containerd image store默认开启）、live-restore=true，daemon无features字段。root明确选择本轮**保持该原profile**，不顺带切classic。合同docker_profile必须精确为`{"driver":"overlayfs","live_restore":true,"containerd_snapshotter":"default-enabled"}`，另docker_daemon_sha256锁实际原文件SHA；安装前后及seal前逐次校验。此前classic预期导致的首次check拒绝单独保留，不追改为通过。

必须0容器、0卷、0镜像、仅bridge/host/none默认网络、Swarm inactive、无Docker子挂载。零镜像门禁拒绝清未知预载镜像。实际`/var/lib/docker/engine-id`文件必须等于daemon info ID才可进入seal；遇旧/etc/docker/key.json、未知路径或模式即停。

通过门禁后仅停9041的docker.socket/docker/containerd，确认全停，删除engine-id与无工作负载的default network local-kv.db。**不递归删除/var/lib/docker或containerd目录，不清任何业务VM数据。** `/etc/docker/daemon.json`原SHA和Docker版本保留不变。官方Moby实现参考[LoadOrCreateID源码v28.5.1](https://github.com/moby/moby/blob/v28.5.1/daemon/id.go)：缺engine-id时新生成UUID；公开源码仅作背景，目标实际文件与ID严格相等仍是强制门禁。

9042必须java UID999/nologin，已有`/usr/local/libexec/dell-java-acceptance/verify.py --smoke`以java执行通过、SHA原值、JDK/java/javac目标不变、exporter仍masked、不含业务。不修改验收脚本/JDK/java用户，不启动任何Java业务。

## 替换与独立QA

新时序：9040/9041/9042 install并单独获准seal后，root停机转为临时candidate template；从candidate full clone QA9043/9044/9045（可复用已停builder释放的197/198/199IP，先撤builder静态登记）。**先QA candidate，成功后root才备份原9001/9010/9011并替换原VMID。** 旧源模板一直stopped且尚未修改，坏candidate不会先落地到原模板。最终原VMID恢复后root再核metadata及镜像一致，不虚称早期QA来自已替换的最终VMID。

`template-qa.py --contract ROOT600FILE`只用于root明确命名fish-qa-*的专用clone，拒绝全部现役/原template/3builder VMID。contract包含：

- purpose=`fish-template-independent-QA`、source_template=9001/9010/9011（logical最终ID）、candidate_vmid=9041/9040/9042（实际clone来源），root新分配vmid/hostname/ip/mac；
- expected_shells（builder安装前root/ub原值），trusted_hostkey_fingerprint（rootQGA结果）；
- forbidden_machine_id_sha256、forbidden_hostkey_fingerprints：至少含本轮对应builder及已验的其它QA；
- protected_files：对应installreceipt before.files，Java verify.py/Docker daemon.json必须带原SHA；
- Docker额外forbidden_engine_id_sha256：builder及其它已验DockercloneID摘要。

QA必须CI done、精确身份、fish精确版、ub临时no-config/private smoke、原shell、无builder工具/receipt与业务目录；Docker必须独立engineID+零容器/卷/原overlayfs+live-restore profile和daemonSHA；Java仍原verifySHA/JDK21/java999/exportermasked/无业务监听。调用端另做新strictub SSH。QA通过后root才签收新模板。至少独立QA相对builder身份不同；若需要证明多克隆互异，再由root资源窗口生成第二QA，将第一QA摘要加入forbidden列表，本工具不自行分配/创建。

清理：root仅删除自己QA/builder对象，保留受保护原template备份和本轮receipt。QA/模板实际验证未完成前，不修改runtime-status.json中的模板状态为passed。

## 本地验证

`python3 -B cleanup/fish/test-template-builder.py`：10项纯fixture通过，包含三类型精确合同、excluded/liveVM拒绝、错IP/MAC/source/version/shell拒绝、phase与摘要错配、过期窗口、失败guard不调用phase、原shell与SHA变化拒绝。两新脚本AST解析通过。没有将fixture当实际guest或模板验收。
