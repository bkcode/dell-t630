> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 220 → 240 受限测试发布链

当前状态（2026-11-06）：用户已明确授权220→240受限发布链安装与测试演练。220专用publisher身份、240独立deployer/forced-command/精确sudoers均已安装，原生sshd/visudo及ub严格SSH复连通过；私钥只留220。A=`20261106T121030`已完成root:root0600与LoadCredential元数据迁移，五服务真实health UP，JAR/YAML/manifest字节不变。B=`20261106T124000`已由220真实stage并activate健康；随后rollback A健康，最终current=A。12项真实受限负测、2项原生sudo负测及最终安全审计通过，A core字节仍匹配可信源。正式Java仅运行基础，发布链仅到测试240。

实际安装源码只读回收在[deployed](deployed/)，逐文件SHA见 `evidence/implementation/publisher-installed-code.json`。工作目录的fixed/adopt/root存在**尚未部署的cgroup-quiescence停止策略候选**，不得直接重装或视为当前服务器版本。自动审批曾拒绝删除候选与测试的组合命令；已保留候选，采用仅调用已安装审核RPC的更安全方案继续已授权演练。`review-evidence.json`只表示本地静态验证，不表示实时安装状态。

[DESIGN.md](DESIGN.md)为完整合同，[review-evidence.json](review-evidence.json)为离线审查与故障注入记录。当前实际契约采用release `20261106T121030`，私有配置值未输出：Gateway Nacos import为finger-gateway-mobile-lan-v2.yaml；COMS域为LAN `/finger-bff-system/dell-test-files`；Snowflake DC1，Gateway/Auth/System/COMS/BFF worker1/2/3/4/5。

## 文件

| 文件 | 责任 |
| --- | --- |
| `publisher_protocol.py` | 纯协议、目标/资源/YAML/hash校验；特权端手工512-byte USTAR解析；客户端规范USTAR生成 |
| `publisher_dispatch.py` | deployer forced-command，精确SSH语法和220→240连接tuple，sudo唯一无argv root入口 |
| `publisher_root.py` | 240 root持有RPC：status/stage/activate/rollback；root自身二次校验、immutable、固定执行器、原子回执/busy |
| `fixed-deploy-test-chain.py` | 从既有测试deploy脚本准备的固定可信版本：Root0600 YAML、LoadCredential、恢复事务与真实health |
| `adopt-baseline240.py` | 仅manager在批准窗口进行A一次元数据迁移，字节SHA不变，失败恢复旧metadata和A |
| `publisher_client220.py` | 仅220 publisher运行，私钥仅在220，自己规范打包USTAR并以SSH stdin发送 |
| `install240-transport.py` | 已在批准窗口执行的transport安装器；不改A元数据或启动应用；重装前须审核当前候选 |
| `install220-client.py` | 已执行的220客户端/固定目标/可信240 hostkey安装，不读取新私钥 |
| `manager-create220-identity.py` | 已执行的220身份/key生成；公钥仅private文件，普通证据/输出只指纹 |
| `test_security.py`、`validate.py` | 本地负向与故障注入，不调用guest或服务 |

## 权限与秘密

- 新私钥：220 `/var/lib/dell-publisher/.ssh/test240_ed25519`，publisher所有、0600，绝不复制yang_local_rsa、不导出新私钥。
- 公钥仅从 `private/publisher/publisher220-test240.pub` 经manager STDIN安装；普通evidence只留SHA256指纹，不留公钥原文。
- 240 deployer独立账号，无通用sudo、无finger/docker组；root-owned authorized_keys使用from220、restrict、forcedcommand，sshd Match加第二层限制。
- sudoers仅root helper精确路径和空参数串，无任意python/systemctl/shell通配。
- 持久application.yaml为root:root0600；fixed unit使用LoadCredential，finger只读systemd credential目录，ExecStart为`file:%d/application.yaml`路径，不放秘密到Env/argv。
- Publisher上传只含manifest/JAR/config；没有远端部署脚本或任意systemd字段接口，Root执行器由manager预装并锁SHA。

## 已修审查项

1. stop_all/pointer/start全部在恢复try内；新旧core、固定LoadCredential unit在停服务前验证。pointer失败故障注入实际记录：stop → pointer(B失败) → best-effort stop → pointer(A) → start(A)。stop失败同样尝试旧A恢复；失败仍向caller报失败，不能冒充B成功。
2. 特权解析不调用TarFile/getmembers；只接受canonical未压缩USTAR、精确11有序regular成员。PAX/GNU长名/链接/设备/稀疏/压缩/大尺寸在header拒绝，member12在读取其payload前拒绝。客户端自己生成规范USTAR。
3. status不取得修改独占flock，读取过滤原子last-transaction和带PID/start_ticks的busy marker，便于断联后回读；不输出YAML、Env、日志或秘密。

已部署版本27项离线安全回归通过；本地未部署候选额外3项（共30项）通过，包括真实121030本地契约兼容检查。源码与准备版本SHA见fixed-deployer-source.json；原Java runtime部署源码未改动。

## 发布演练步骤及当前证据

1. Gateway QA已经结束，用户明确授权和主AI完整窗口已记录在user-decisions-2026-11-06.json#restricted_publisher_transport。
2. 已审Root代码/hash并安装。可信240 hostkey只经私有STDIN安装220 profile；公钥只从private.pub到240，普通证据只指纹。
3. transport前后sshd/sudoers原生校验及ub严格复连通过。初始baseline_migrated=false时220真实status拒绝；publisher不能自行放开。见publisher-limited-transport.json与publisher-baseline-false-status.json。
4. A元数据迁移已通过，旧metadata备份仅留240 root私有目录；core字节不变，root0600/LoadCredential、五health与可信policy通过。见publisher-baseline-adoption.json。不改DB/Nacos。
5. 由220客户端status、规范stage B、activate B；真实五服务health及LAN关键接口后rollback A，再health。B/A不回滚数据库或Nacos，字节兼容必须事先审查。
6. 用新身份做shell/SCP/SFTP/转发/坏target/坏tar/重复release等负向验证；新key仍仅220、无root shell。结果逐项以publisher-actual-negative-tests.json为准，未通过不能标已验收。

本链授权publisher部署测试应用代码，不承诺恶意JAR无法访问finger本来可读的测试资源；系统边界是RPC不提供root shell、正式环境、DB迁移或Nacos改写操作；arbitrary JAR仍能使用finger本来获准的test namespace资源，不能声称网络层阻断这些已允许资源。

## 实际结果与限制

- `publisher-release-exercise.json`：stage B、activate B、rollback A、最终五服务真实health、busy状态读取均通过；最终回到A。
- `publisher-actual-negative-tests.json`：12项真实SSH/RPC/归档/immutable负测通过，前后A字节/unit/pointer/PID不变。
- `publisher-final-security-audit.json`：root600/LoadCredential、固定代码policy SHA、受限sshd、2项原生sudo负测、220 key权限与指纹、ub严格复连通过。
- `publisher-LAN-public-smoke.json`：本Mac直连192.168.21.22:19999的公开OIDC/JWKS smoke失败，OSError errno65；这不是应用health通过的证据。主AI已结合LAN-entrypoint-cli-probes.json确认这是Mac Python执行面限制：原生nc/curl及LAN端口可达，不能据Python errno65判定宿主故障；主AI补原生公开OIDC/JWKS smoke。本子任务未修改宿主网络。此前121030完整业务E2E结果由主AI维护在java-test-business-acceptance.json，不能把本次health演练等同再次完成业务E2E。

可复核的验收ID、前置、步骤、可观察条件、证据与状态见[ACCEPTANCE.md](ACCEPTANCE.md)。发布操作没有数据库迁移/回退或Nacos配置改写接口；应用正常启动/注册和已获授权的测试资源访问仍存在，不作数据库字节不变或RPO承诺。
