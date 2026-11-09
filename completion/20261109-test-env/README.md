> 后续范围变化：用户随后授权清测试Nacos配置项并原样导入本机选定36份。旧finger-test7项已清、新两source域32/4；finger-test-empty仍0、账号/权限/业务DB保持。当前见[配置导入交付](../20261109-nacos-config-import/README.md)。下文为先前空服务阶段时点记录，不反改原回执。

# 空测试基础服务：已就绪

2026-11-09（Asia/Shanghai）。用户最终范围：不做数据迁移，只搭空服务，保留现有数据、不导入业务SQL或配置、不启动Java业务。复用了VM210现有MySQL/Nacos/Redis/RabbitMQ，没有重装、重启或新增VM/容器。

## 使用入口

| 项目 | 当前值 |
| --- | --- |
| Nacos UI | http://192.168.19.20:8848/nacos/ |
| 新空namespace | finger-test-empty |
| Namespace ID | 23836f2e-9553-5948-84cd-431b2f241bd6 |
| 配置数 | 全group为0 |
| 注册服务数 | 全group catalog为0 |
| 测试应用账号 | finger_test，使用既有受保护密码，不重置 |
| 授权 | 原finger-test-client角色仅新增本namespace:*:*的rw，原关联与旧权限保留；无global/admin扩权 |

“空”仅指新逻辑隔离域，不是清空整台机器或数据库。原namespace finger-test（10719261-2641-590a-b821-c8484ca955ac）的DELL_TEST 7份YAML和历史计数9保留；finger_auth_test 3表、finger_coms_test 10表、finger_system_test 6表、nacos_test 12表均保留。本次没有读取配置正文或业务行，更没有迁入Mac数据。

现役基础bundle的NACOS_NAMESPACE_ID仍指旧域，供既有监督/健康兼容，不改旧profile。未来业务连接空域时必须显式选择上面新ID；当前不发布任何Data ID、不注册服务、不启动Java。新域rw是权限声明与读回，未通过发布再删除配置来验证写功能。

账号/密码仅在VM210的/opt/dell/data/test-data/.env（必要非secret键）及secrets/nacos-admin-password、secrets/nacos-client-password受控文件，由ub通过sudo管理，不在聊天或Git展示密码/token。管理账号与应用账号职责不同，不把Nacos管理端经CF公开。

## 实际验证

- [只读预检](preflight.json)：原UUID/IP/GW/DNS、4容器健康、旧数据与namespace实形。
- [只读dry-run](dryrun.json)：新固定ID当时不存在，所有写前门禁已过。
- [新增回执](empty-namespace-created.json)：唯一持久变更是新namespace与其精确权限，原config MD5元数据/历史COUNT/业务schema表元数据在guest内前后相等，4容器完整frame不变。没有SQL写、账号/密码reset或业务初始化。
- [独立后验](postcheck.json)：配置0、跨组服务0，client缺配置404、无关域403，权限精确为旧/新两resource rw，用户/角色计数保持；旧数据计数和容器ID/Image/health/restart0/OOMfalse保持，UI/readiness均200。独立预检没有存逐项MD5，故逐项不变只据producer真实前后比较，不伪造独立对照。
- [API能力](api-capabilities.json)、[设计复审](design-review.md)、[本地来源及禁止重跑清单](local-source-map.md)。

实现：[固定域管理脚本](../../infra/data/test-empty-namespace.py)。默认是只读dryrun；apply只允许固定namespace/权限两个POST，不DELETE、不重置。属于本轮实施记录，日常不要盲重跑apply或旧deploy/bootstrap/fixture/businessinit脚本。

## 边界

正式环境、网关/网络、备份机制和历史归档均未改。测试数据仍不加入自动备份；正式DB/Nacos自动备份范围保持。Java/发布baseline继续停用，Nexus不合并、Penpot不升级，无Mac外部探针。当前只签空基础与权限，不签业务配置、业务数据/应用E2E、写入功能或全业务RPO/RTO。

验收：[当前四项](acceptance.json)。
