> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# move-guest-os.py 只读review

复核当前42行版本，SHA256 `830676c2a29fd0694d0713a38c62cc5816e30c8c8f223fb81d9ef104b1750e1d`。没有修改该脚本或宿主/来宾状态。

已认可：stage使用旧net0契约核对，通过原严格SSH安装/准备guest helper；apply只hotmove指定net0，再走独立于IP网络的QGA apply，修改CI/DNS后严格新地址SSH验证，再登记新target。应用状态明确由其它事务管理，没有把network-only成功冒充业务已ready。

先前发现的“CI metadata改新后late failure不恢复”已修：当前行20捕获原ipconfig0/nameserver（包括missing），行30–36独立尝试NIC、OS、CI三项恢复，收集errors，任何未完成都标rescue-required；不再报告为未修。missing字段通过qm --delete恢复，非missing原值恢复，避免硬编码替换自动失败路径。该路径仍须实演才算回退验收，本次未诱导失败。

剩余P2：显式rollback分支行37–41还未更新/删除migrated-access.json中的new target；在成功apply后主动rollback，OS回旧而ledger仍指新IP，会误导后续管理工具。建议同一次回退更新target状态/撤销新entry。该分支也仍按契约oldIP/oldGW并硬编码DNS1.1.1.1恢复CI，而没有使用apply时捕获的missing/原值；本次11台原DNS均1.1.1.1且CI固定，当前scope值正确，但通用“精确原样恢复”声明应限定或补相同原始快照。若ledger写入失败/中断后触发rollback，也应让ledger进入unknown/reverted，不能保留看似已迁成功的target。

其它限界：备份before/vmID.conf每次apply会覆盖，适合单次编排；若希望跨重试保留第一份原始状态，应使用nonce/immutable第一份。stage/apply不替代外层独占编排、PVE console/QGA救援或业务启动顺序。以上没有必要扩大为全网renderer重构或更换SSHkey。

实际包验收与清理清单分别见packet-acceptance.json、packet-test-plan.md、final-host-cleanup-checklist.md。230计划停机不作为故障处理。
