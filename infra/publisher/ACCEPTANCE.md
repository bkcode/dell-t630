> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 受限测试发布链验收

范围：VM220 `10.63.30.10` → VM240 `10.63.20.20`，A=`20261106T121030`，B=`20261106T124000`。前置条件是用户知悉风险后的明确授权、主AI释放240 QA/启停窗口、A现役版本SHA与测试依赖健康。正式Java节点、数据库维护、Nacos配置改写不在发布RPC范围。

| ID | 前置条件 | 步骤 | 可观察通过条件 | 证据（dell/evidence/implementation） | 状态 |
| --- | --- | --- | --- | --- | --- |
| PUB-01 | 已审transport代码、信任的host key | 安装220 client和240 deployer/sshd/精确sudoers，原生校验后独立ub严格重连 | sshd/visudo exit0；ub仍能严格SSH；安装前后A core/owner/unit/PID不变 | publisher-limited-transport.json | 通过 |
| PUB-02 | 专用publisher身份与220本地产生新key | 只取公钥指纹和私钥stat；公钥只经私有STDIN | 私钥220 publisher0600；普通evidence只指纹；无私钥导出 | publisher220-identity.json、publisher-installed-code.json；最终元数据复核见publisher-final-security-audit.json | 通过 |
| PUB-03 | baseline=false、A manifest SHA已核 | 实际220 status被拒，再manager-only adopt A | 原始A JAR/YAML/manifest hash不变；YAML root:root0600、LoadCredential；五health UP | publisher-baseline-false-status.json、publisher-baseline-adoption.json | 通过 |
| PUB-04 | A已迁移且policy可信、B仅换release ID | 220构造canonical未压缩USTAR，经受限SSH真实stage | 精确11数据文件、536442880字节；不含部署脚本；目标immutable staged，未激活 | publisher-release-exercise.json#B_preparation/stage_B | 通过 |
| PUB-05 | A可恢复、B校验通过 | 从220实际activate B，再独立status | current=B；五systemd active且HTTP200/health UP | publisher-release-exercise.json#activate_B/B_status | 通过 |
| PUB-06 | B已真实健康 | 从220 rollback A，再独立status | current=A；五systemd active且HTTP200/health UP；A core与可信源hash仍相同 | publisher-release-exercise.json#rollback_A/final_status、publisher-final-security-audit.json | 通过 |
| PUB-07 | A/B演练完成、无并发修改 | 新身份真实shell/SFTP/转发/参数/归档/immutable拒绝测试 | 全部非零明确拒绝；前后core、unit、pointer、五服务PID/启动时间不变 | publisher-actual-negative-tests.json | 通过（12项SSH/RPC+2项原生sudo） |
| PUB-08 | 实际B切换持修改锁 | 第二个220客户端调用status | ok=true且busy=true；过滤原子回执，不需要修改独占锁 | publisher-release-exercise.json#status_during_activate | 通过 |
| PUB-09 | 本地纯合成单元测试 | 注入pointer失败、stop失败、不可恢复旧版本、PAX/压缩/成员12等 | 失败尝试回退并启动旧A；旧版本先校验；恶意归档在边界拒绝 | infra/publisher/review-evidence.json | 已部署版本27项通过；候选额外3项仅离线 |
| PUB-10 | 固定RPC仅test240 | 审代码和实际动作回执，检查最终scope | 无正式目标、任意root脚本/命令、数据库迁移或Nacos配置操作接口 | deployed/vm240、publisher-release-exercise.json | 通过（操作范围） |

这里的“未执行DB/Nacos回退/维护”指发布RPC没有这些操作；Java以finger身份运行后仍持有已授权的测试数据与Nacos namespace权限，启动注册/缓存等应用正常行为不属于数据库逐字节不变承诺。任意获准JAR的应用权限不能被误称为网络层完全阻断。

`deployed/`是从实际安装程序只读回收的公开代码，准确SHA在publisher-installed-code.json。本地fixed/adopt/root中额外的cgroup-quiescence候选未部署，不能将候选30项离线通过当成服务器使用该版本。自动审批拒绝删除候选的组合命令后，候选保留，演练仅调用已安装的原审核程序。

额外LAN观察（不属于受限SSH发布链的通过条件）：本Mac只读GET `http://192.168.21.22:19999/.well-known/openid-configuration` 和 `/oauth2/jwks` 得到URLError/OSError errno65，记录为Python执行面失败；主AI已通过原生nc/curl证实LAN可达（LAN-entrypoint-cli-probes.json），原生公开smoke由主AI单独留证，不能据Python errno65判定宿主故障。没有为了修复LAN而修改PVE宿主网络。完整业务QA不是本次发布链演练的重复验收，原121030 QA由主AI单独留证。
