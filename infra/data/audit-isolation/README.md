> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# DATA001 目标环境隔离只读审计

当前证据：`evidence/implementation/data-environment-isolation-final.json`，`completed-for-manager-signoff`。本目录独占代码，不改源项目、服务、配置或SQL。仅读取新目标bundle/当前测试release/现役SELECT权限元数据；没有读取Mac旧源凭据。

`audit.py`固定200/201/210/240范围；普通证据只保存账号、host、namespace、vhost、权限和差异布尔，不保存秘密值/密码hash。MySQL仅SELECT，正确的新目标root口令经匿名FD3管道交给本地容器内native client，不进入argv/env，不写认证文件。五份运行YAML及六份实际引用的Nacos文档通过内存摘要比对，只输出一致性布尔。旧gateway-v1候选按要求保留，并未被当前A引用。

本次已完成且只完成两个精确非admin跨实例负测：201本机prod用finger_test一次；210本机test用finger_prod一次。前提由实际用户表确认，两实例应用账号集合各自唯一，正常nacos管理员不属于待负测集合；两个Nacos本环境正常readiness和业务账号登录成功。**两次实际均HTTP500，保持原码，不能写成401/403。** 官方2.4.3源码的缺失用户异常/通用异常映射与此一致，但该归因属于静态推断，没有采集服务器异常栈。第一次错误正文已弃，未解析其token字段；第二次错误正文/Authorization头仅在内存检查，未返回token。两次都没有成功登录响应。

`finish.py`只完成主AI单独批准的剩余210一次；现有结果不允许重发。两程序检测已存在/完成的尝试记录时拒绝运行且保持证据。不要删除或覆盖ledger以重复负测。整项DATA001由主AI结合结构、账号/namespace、最小SQL权限、30条网络允许/拒绝矩阵及响应语义限制签收。

本期正式Java230-232仅运行基础，正式业务schema未初始化，源业务数据未导入；测试为新建结构与合成身份。不声明源全量迁移或全量脱敏已完成。本目录的只读审计结束后不继续复扫runtime，后续live盘点由主AI协调。
