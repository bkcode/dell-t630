> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# Auth隔离部署适配补丁

该目录不含新运行秘密。`apply-auth-config.py`校验原AuthorizationServerConfig SHA，只修改private/java-build中的Auth副本；原仓库不变。脚本按方法名确定四个client初始化块，去掉原内嵌secret变量，替换为外部属性，保留clientId、grant、scope等逻辑。不同上游版本会拒绝重放，升级时需审查。

`AuthBootstrapProperties.kt`绑定必填issuer、四客户端secret和回调，异常与toString不输出secret。相同secret复用既有编码结果以保证重启稳定。没有DB触发器或post-start覆盖。

`AuthBootstrapPropertiesTest.kt`为5项纯单元，不加载Spring应用上下文，也不访问DB/Redis/Nacos；已在offline、loopback-only、1GiB/2workers下通过。测试输入均为固定单元fixture，不是目标秘密。

原/新配置与源树hash、实际修改和未嵌入秘密声明保存在private的auth-deployment-patch-manifest.json；最新JAR与测试结果在 [build-status.json](../build-status.json)。真正运行秘密由 [runtime准备工具](../runtime/README.md)写到private/java，issuer候选为LAN测试端口19999，仍待OIDC目标验证。


## Gateway Redis bootstrap import

2026-11-06 的目标首次启动暴露 `redisTemplate` 重名：本次冻结的 `common-redis-1.0.0.jar`（SHA256 `0285f1638de714dffdb14f8d6adb038963b8d8d2ffb868632e12866e97a67182`）中的 RedisConfig 方法没有当前原源码已有的 ConditionalOnMissingBean。Redisson 3.50 的同名缺失条件在较早的自动配置阶段评估，随后旧共享配置注册导致启动失败。

`GatewayRedisConfiguration.kt` 仅在隔离 Gateway 中作为用户配置显式 Import 原 RedisConfig，使 JSON key/value/hash 序列化模板先存在，Redisson 的 fallback 正常退让。保留 RedissonClient 和连接工厂，不改共享库、不发布API、不启用全局bean覆盖。

应用与验证入口（仅 private/java-build 隔离副本）：

```bash
python3 infra/java/patches/apply-gateway-redis-import.py
python3 infra/java/patches/run-gateway-redis-regression.py --run-id <unique-run-id>
python3 infra/java/offline-build.py probe --service finger-gateway-mobile --action bootjar --timeout 600 --run-id <unique-run-id>
```

回归使用实际缓存 Redis/Redisson 类、断开连接的接口代理和真实 DeferredImportSelector，既验证普通自动配置，也按目标观察到的 Redisson-before-legacy 顺序验证；关闭bean覆盖，断言共享JSON序列化和Redisson保留。未Import基线失败，Import后2项通过。最初直接把第三方配置注册为用户配置的测试改变了配置角色，已由Deferred用例替代；原失败日志保留，不将它作为生产修复失败或通过依据。

本次新Jar与基线Gateway全部162个嵌入库SHA一致，批次20个内部库名没有同名异内容冲突。新Jar和证据见 `evidence/implementation/gateway-redis-bootstrap-fix.json`。轻量上下文和bootJar通过不替代VM240实际启动与业务链验收，目标激活由主AI负责。
