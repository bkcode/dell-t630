# 独立空测试Nacos基础：只读postcheck

采集：2026-11-09T12:29:51.466405+00:00。本收据只读，all_passed=true（限定下述实际可比范围）。没有调用m.cfg/preflight/run/auth/bootstrap或fixture，没有数据库/配置/账号写，没有Java/Git动作。登录只使用guest内既有受控凭据，token/password/hash不进入输出。

## 新空间与权限

- 新namespace：`23836f2e-9553-5948-84cd-431b2f241bd6` / `finger-test-empty`，配置COUNT0。
- 数据库配置元数据覆盖该tenant所有group，COUNT0；官方catalog未加group/service筛选，count0且serviceList空，含零实例持久service的检查范围。
- 原client关联角色保持；该role权限列表**精确只有原namespace:*:* rw和新namespace:*:* rw两条**，没有全namespace通配/额外resource。
- 原client对新namespace固定不存在config只GET，HTTP404；同probe到无权限namespace HTTP403。没有请求存在配置正文，不用发布/删除假配置来验权限。

## 原数据与身份保留

| 项目 | 本次观察 |
| --- | --- |
| 旧finger-test namespace | 原ID10719261-2641-590a-b821-c8484ca955ac，仍7份配置 |
| 旧配置元数据 | 7项，均DELL_TEST/yaml，7项MD5字段存在 |
| 配置历史COUNT | 9，与preflight相等 |
| schema表数 | finger_auth_test3、finger_coms_test10、finger_system_test6、nacos_test12，与preflight相同 |
| 用户/角色/权限COUNT | 用户2/角色2保持，权限1→2为root批准的精确新grant |
| 四原容器 | ID/image与preflight同，running/healthy/restart0/OOMfalse |
| Nacos readiness/UI | HTTP200，仅状态，不保存响应正文 |

**元数据比较限制必须保留：** 初始preflight保存的是count/group/type与schema表数，没有逐项dataId/group/MD5集合。所以本独立postcheck只签counts/group/type及当前MD5字段存在，不能声称独立比过没有保存的旧集合。逐项旧配置metadata完全不变的证据来自root producer真实before/after比较，见[创建收据](empty-namespace-created.json)。本次没有读取content，也没有业务行读取或密码重置。

“空”限定为新namespace配置/全group服务都是0，不是整台210或MySQL/旧namespace无数据。保留原19张业务测试表与旧7配置；client复用原测试身份，所以仍有旧空间能力，不能称完全独立身份/物理隔离。rw是已读回授权元数据，实际仅只读404及越权403验证，没有测试配置写/服务注册或启动Java。

机器可读记录：[postcheck.json](postcheck.json)。所有写动作由root的producer独立记录，本postcheck不执行任何初始化、迁移、发布、角色变更或清理。
