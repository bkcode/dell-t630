> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 受限测试发布链设计与已实施合同

范围只有发布机VM220 `10.63.30.10` → Java测试VM240 `10.63.20.20`。用户已明确授权、主AI审查并释放QA窗口；transport安装、A元数据迁移、B发布与回退均已执行，最终A=`20261106T121030`五health UP。RPC不提供正式目标、数据库迁移/回退、Nacos配置改写或任意root命令。实际安装源码及SHA以deployed目录和publisher-installed-code.json为准。

## 身份与SSH

- 220新建专用publisher运行身份，生成全新Ed25519发布key。私钥仅存220 `/var/lib/dell-publisher/.ssh/test240_ed25519`，目录700/文件600，绝不复制既有yang_local_rsa，也不将新私钥导出Mac。
- 240独立deployer账号（不是finger、不是ub），密码/keyboard-interactive禁用，shell必须可执行forced command（使用/bin/sh，不用会阻断forced command的nologin）。不授予docker组或通用sudo。
- authorized_keys由root持有且仅使用root文件 `/etc/ssh/authorized_keys/deployer`；key选项 `from="10.63.30.10",restrict,command="/usr/local/libexec/dell-publisher-dispatch"`。sshd的Match User deployer再限制ForceCommand、无TTY、无转发、无用户rc、无密码、自定义root-owned AuthorizedKeysFile；不改其他管理员账号。
- 220使用manager经可信QGA核对的240 host key，不以ssh-keyscan替代信任、不关闭StrictHostKeyChecking。客户端明确ForwardAgent=no/RequestTTY=no。

## 最小sudo与Root固定执行器

240的deployer只有一条sudo：`/usr/local/libexec/dell-publish-test240 ""`（sudoers的空参数形式，表示不能带任意argv），无python*、systemctl*、shell或路径通配。所有请求通过受限STDIN JSON协议输入，root helper必须独立复核协议，不能信任非root dispatcher。helper与父目录均root持有、不可被deployer/finger写。

root helper调用manager安装的固定 `/usr/local/libexec/dell/deploy-test-chain.py`，以 `/usr/bin/python3 -I` 运行，目标guard只接受java-test-01 / 10.63.20.20；不存在远端脚本上传接口。固定 readiness marker 为 `/root/dell-java-test-readiness.json`，仍由任务管理者根据真实SQL/Nacos/network/issuer证据维护，publisher不能设置或替换。

已有deploy脚本是五服务测试链，保留check/stage/activate/rollback逻辑。安装前只对stage的配置归属做审查后的最小加固：application.yaml持久文件改root:root0600；unit使用LoadCredential=application.yaml:<root路径>，ExecStart仅传file:%d/application.yaml。finger从systemd只读credential目录读取，不直接读持久秘密，不把秘密放Env/argv。全部release文件root持有且无group/world写。保留非root应用用户、固定systemd模板、MemoryMax、受限可写目录和真实actuator/health等待。

## 远端命令与协议

SSH_ORIGINAL_COMMAND只接受规范ASCII语法：

- `dell-publish-v1 status`
- `dell-publish-v1 stage RELEASE_ID ARCHIVE_SHA256 ARCHIVE_BYTES`
- `dell-publish-v1 activate RELEASE_ID`
- `dell-publish-v1 rollback RELEASE_ID`

release ID限定现有YYYYMMDDTHHMMSS，digest为64hex，stage大小上限1GiB。其他shell、SCP/SFTP、env前缀、引号、换行、目标地址、任意路径/额外参数全部拒绝。dispatcher始终sudo固定helper且无argv，将规范JSON头与stage原始tar转发STDIN；不得把配置秘密放命令行/日志。root helper再次限定字段与动作、角色/IP、调用者、锁和归档内容。

## Immutable stage

- stage只流式接收tar到root700临时目录，限制头/总大小/空闲及总接收时间并计算SHA，不在root内存读整包。
- canonical未压缩USTAR精确11个regular成员：manifest.json及固定五服务各app.jar/application.yaml；拒绝目录条目、重复、绝对/..路径、symlink/hardlink/device、任何脚本/unit/额外文件。
- manifest只能指向test240、test210数据、dell-test和已确定LAN issuer；五服务/端口/堆与MemoryMax固定白名单，不允许生产或自定义systemd内容；safe YAML、JAR格式和每文件SHA复核。
- root pending内容不可被deployer写，固定deployer check/stage后复核目标hash和root只读归属。已存在release ID拒绝覆盖；网络失败时先status确认，不能静默重写。
- stage不启应用，不迁移DB、不写Nacos。220只发送JAR/config数据包，不传执行脚本；制品来源/commit/test状态保留为审阅元数据，不能冒充真实验收。

## Activate / rollback / status

所有修改动作通过root固定锁串行，避免同时stage/切换；status不取修改锁，只读取过滤后的原子回执与busy marker，并显示当前真实health。activate/rollback只选择已管理的immutable release，使用固定root readiness marker；按System→COMS→Auth→BFF→Gateway启动并核对实际health，停止、指针切换和启动全包入恢复事务；先校验新旧core与固定LoadCredential unit可恢复，任一步失败均attempt stop、回指旧release并启动核对旧health。旧release保留，不自动清理。

status只返回release ID、有限健康状态、stage/事务回执，不泄露YAML、Env、秘密或日志。根回执持久化到root目录；处理中连接中断不能将半完成误报成功，调用者应重新status。实现将忽略SSH HUP并保持本次有界事务结束，root管理员仍可介入；数据库和Nacos不在回退范围。

## 审核后验收顺序

1. 主AI确认Gateway/240 QA与重建已结束并明确应用窗口后，核对现役release A和root marker；安装固定root代码、deployer限制与精确sudoers，验证sshd/sudoers语法；保留ub管理员入口。在该窗口对A做一次记录充分的权限/unit元数据迁移：先保存JAR/YAML/manifest SHA与旧owner/mode/unit，再仅改YAML root:root0600及固定LoadCredential unit，字节不变；受控重启A健康后才将其作为可信rollback A。失败恢复旧元数据和A，不改DB/Nacos。
2. 220本机生成新key，manager只传公钥到240；私钥不导出。验证220→240的实际SSH source为10.63.30.10。
3. 负向：普通shell/id/SCP/SFTP/端口转发、未知动作/目标/marker、tar穿越/链接/脚本、坏SHA、重复release、非许可端口/内存全部拒绝；不得借新key取得root shell。
4. 将已审JAR/config组成release B（可复用同字节新ID做发布链演练），由220 stage；真实activate B五服务health通过并记录当前指针；rollback A后五服务health和LAN关键接口复核。
5. 验证DB/Nacos未被回退、秘密未进argv/stdout、新key仅220、无原管理员密钥复制。只有真实正反向执行证据后签收，不把静态准备写成发布链完成。

边界：publisher有权执行测试应用代码，不能承诺阻止恶意JAR作为finger访问本来允许的测试资源；系统边界是不授予root、正式环境、数据迁移、Nacos改写或任意命令能力。数据库兼容性与配置审阅仍由manager控制。

当前状态：220专用身份/key和client、240 transport/精确sudoers/root固定代码已安装，原生校验与ub严格复连通过。A配置root:root0600+LoadCredential迁移前后core字节不变。由220实际stage/activate B=`20261106T124000`五health后rollback A五health通过；当前无剩余启停操作。

## 已修交叉审查项

- P1：stop_all/pointer纳入try，previous core和固定unit预检在停服务之前；离线故障注入已证明pointer失败与stop失败都尝试pointer(old)+start(old)。
- P2：特权解析不调用tarfile/getmembers。手动512-byte USTAR header检查，成员12在读取payload前拒绝，PAX/GNU/链接/设备/稀疏/压缩/超限一律拒绝；客户端规范生成有序11文件USTAR。
- P2：status无修改flock，过滤读取原子last-transaction及busy marker，断联可回读；stale pid marker有区分，不输出YAML、Env或日志。
- 当前121030契约已本地兼容校验：Gateway必须finger-gateway-mobile-lan-v2.yaml，COMS upload.domain使用/finger-bff-system/dell-test-files；Snowflake固定DC1，Gateway/Auth/System/COMS/BFF worker分别1/2/3/4/5。

发布链实际证据见ACCEPTANCE.md。12项真实SSH/RPC负测与2项原生sudo负测均通过；status busy也在真实B切换中通过。额外本Mac直连LAN公开OIDC/JWKS smoke得到errno65，主AI已确认这是Mac Python执行面限制（原生nc/curl可达，见LAN-entrypoint-cli-probes.json），原生公开smoke由主AI单独留证，不将Python结果标通过。

本地working fixed/adopt/root保留未部署的cgroup-quiescence候选及3项额外离线测试。自动审批拒绝删除候选的组合命令后，候选保留且未同步服务器；真实演练只调用已安装原审核RPC。不要据本地候选30项通过重装服务器。当前服务器27项原审回归对应的实际公开源码保存在deployed目录。
