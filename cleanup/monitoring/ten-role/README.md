> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../../11-live-handoff.md)；旧初始化器不得重跑。

# 当前10 guest /12永久角色 /15 targets一致性：已执行签收

221继续运行Nexus，停机维护授权仍pending；本候选不迁Nexus、不改220基础profile。只移除已退役231/232的监控注册行。活动exporter VMID为200/201/210/220/221/230/240/250/260/270；CF100/GW190独立路径保留，因此12个永久角色、10node+Ops5=15targets。root已经实际应用Java-only SD并15/15UP，receipt为`../interim/deployment-evidence/940e757ea48c4fc59e4413cd20a04b07.json`，本工具不重复修改fileSD。

## 本轮实际采样/候选

`live-source-inventory.json`对10guest逐个采样实际rootcatalog、installer、collector与各自healthSHA。所有实际catalog/installedinstaller仍是原12配套；collector同cfee…且保留。health只取SHA/无敏感元数据，没有复制或修改内容。

每guest仅两个候选文件：catalog删除231/232两行及scope元数据；installedinstaller仅ROLES移除java-prod-02/03、count guard改用len(ROLES)。其它函数AST不变，collector/health任何字节不改。20文件路径、old/newSHA与原owner/mode见`manifest.json`。当前旧版installed逻辑没有被本地新版覆盖。

source-candidates单独从本地当前**新版**做同一ROLES/catalog最小patch，role_health_profile对所有保留10角色逐项输出相等；Nexus仍artifact-service221/http31，publish-service220无Nexus/alias条目。Ops Lark、Java业务停用逻辑等不倒灌旧版。source两文件现已按明确窗口同步，模板/PVE未变更。原prepared manifest保留为不可变SHA契约，实际结果见execution-status.json。

## 后续root开窗后最小动作

`python3 cleanup/monitoring/ten-role/apply.py plan`纯本地；本轮只执行了plan和AST/本地函数校验。

每guest未来显式`... apply --vmid ID --execute`：

1. 核hostname、两文件正好旧12配套或已是同一10配套；health/collector SHA必须与实际采样逐机相同，drift/mixed拒绝。
2. root0700 `/root/dell-roster10/<nonce>`保存真实旧两文件/0600journal；只暂停guest-health timer并等待正在跑collector退出。
3. 成对原子替换catalog与installer；只执行installer `--check-private-ip`（只读）和prometheus用户collector `--check`（不写metrics）。不调用generic install/activate/mask、daemon-reload，不restart exporter/Docker/业务，不启动Nexus。
4. 复核health/collector SHA未变、exporter PID/启动时间/active未变，恢复timer原active/enablement状态。原timer未active时不自动开启。任何失败恢复原两文件；网络断或结果不明先读journal，不盲目重跑。
5. 显式`... rollback --vmid ID --nonce NONCE --execute`只按本轮原字节回退，未知外部变更拒绝覆盖；不会修改fileSD或复活VM。

单机已经10配套时可只读验证后返回no-write。中途出现12/10混合则必须检查journal/由root救援；不为凑通过手工替换SHA。

当前activeplan由root单独删231232并改12永久角色/85GiB/43CPU。本地`sync-source.py`仅plan默认，不覆盖mainplan；source真正同步必须root已把plan整理为此12物理VMID，并且原source SHA未漂移，才显式`--execute`成对同步。不要在旧mainplan下重跑Ops prepare把退休targets带回来。

## 签收/范围

开窗后要汇总十guest：两文件newSHA、native只读checks、health/collector原SHA、timer状态恢复/exporter未重启。Prom现有15/15UP与221条目须保持。普通apply已在10guest顺序执行并独立前后读回；故意失败/显式rollback未实演，不扩展成故障恢复保证。

Nexus221生命周期、包、凭据、权限和服务均不碰；没有Nexus220profile/新proxy/alias操作；Fish/Bash与Ops包安装排除不影响必要监控配置，默认Bash不变；WG full10/24、hostforward0、data auth全保持。本轮不改任何host或guest文件。

未来获用户Nexus维护授权后，新的10→9阶段必须以当前10catalog/installer/source和interim SD10的准确SHA为基线，再审220Nexusprofile/alias就绪与221退休。旧full9manifest基于12的SHA不能盲改后使用，参照`future-merge-contract.json`。

## 本次实际执行收据

- execution-window.json：10/10配对新SHA，20文件；各自health/collector SHA、SSH/QGA/Exporter/Docker/业务unit PID/启动时间、container身份/health、timer active/enablement前后完全一致。221Nexus保持active，220无Nexusprofile。
- 两文件本地新版source已最小同步，role_health_profile保留全部10角色原行为；source原bytes备份source-backups/a9637e83dcbc438baa93bf8123dc33db，原manifest不改SHA。
- final-Prometheus-readback.json：实际15/15UP（10node+5own），221UP，fileSD仍interim10的dc7cf1…，未覆盖回12或full9。
- 不读/改Larkhook/mode/secret、不send；不装包/重启业务或exporter、不动Nexus生命周期、不改mainplan/rootdocs。后续Nexus维护授权仍由父任务等待，不因这次监控收口而获得。
