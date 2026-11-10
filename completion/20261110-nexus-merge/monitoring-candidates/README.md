# Nexus并入220：实际运行基线的最小监控候选

**本目录顶层现在以 fresh 运行文件为准，未安装。** 来源是主AI只读保存的 `vm270-monitoring-before.json` 和 `vm220-monitoring-before.json`。没有连接服务器或修改canonical源，也没有对280/NFS/FileBrowser做操作。

此前按仓库canonical生成的比较版整体移至 `canonical-reference/`，仅供源码差异审查，不能用来覆盖本轮运行文件。尤其不能把包含新resource profile的canonical整体下发到仍运行旧配对baseline的客机，或把旧runtime整体提升为canonical而回退其它profile。

## 1. 顶层实际候选

[manifest.json](manifest.json)列出精确before/new SHA和目标路径，`before/`保留本次捕获的原公开字节：

| 候选 | 实际捕获主机/目标 | 最小变化 |
| --- | --- | --- |
| guest-node.json | Ops270 `/opt/dell/ops/config/prometheus/targets/guest-node.json` | 只删VM221的19.31:9100行；11node→10node，其它行逐项保持，280保留 |
| guest-targets.json | Ops270 `/opt/dell/guest-monitoring/guest-targets.json` | 原runtime有10行且没有280，只删artifact/221成9行，其它字段保持；不从canonical擅加280 |
| install-guest-baseline.py | Ops270 `/opt/dell/guest-monitoring/install-guest-baseline.py` | ROLES与runtime catalog配对9项，移除artifact，publish候选包含Docker/Nexus/MCP/nav，Nexus HTTP仅本机alias31 |
| publisher-health.json | VM220 `/etc/dell-guest-monitoring/health.json` | 原4units前缀完整保持，追加Docker/Nexus/MCP成7units；只新增NexusHTTP31，MCP仅unit检查 |

运行installer没有独立role_health_profile函数，不能套仓库canonical的patch位置；本候选按实际candidates函数精确改动。其它保留角色的candidate对象和unit文本纯函数比较完全相同。

物理node exporter仍只在220的19.30:9100，不创建31的第二个物理node。已确认当前11node+5Ops，删221后为10node+5Ops=15。运行baseline内部registry只有9项，不等于Prometheus少了280：280 target仍在独立fileSD中，其自身运行代码/健康配置不由本次覆盖。

## 2. VM220 profile保持性

原实际profile含ssh、qga、node-exporter和导航4个unit。顶层新profile完整保留这4项及role/private_ip/textfile目录/notes，追加：

```text
docker.service
dell-nexus.service
puyu-deploy-mcp.service
```

只新增无凭据的 `http://192.168.19.31:8081/service/rest/v1/status`。MCP接口带认证，不将127:18765当匿名HTTP健康检查，也不把key写进监控配置。

`merge_publisher_health.py`是纯函数，要求真实publisher/primary30/已有nav检查，保留原列表，拒绝同名Nexus URL冲突。parent实施时仍必须按manifest对fresh profile做CAS，不能把旧合成fixture复制过去。

## 3. 纯验证

[validation.json](validation.json)记录8项本地纯检查通过，使用实际捕获字节与公开源。没有执行Docker、HTTP、unit、包管理或SSH。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 completion/20261110-nexus-merge/monitoring-candidates/validate_candidates.py
```

验证包括实际before/candidate SHA、只删221 node/280精确保留、配对runtime enum/catalog、其它role与unit文本不变、publisher7units、Nexus只31、MCP无HTTP、以及alias31未实际绑定时collector校验应拒绝。collector校验用仓库源纯函数；运行collector本身仍需由主AI读回并在guest内做原生`--check`，不能把这里的通过冒充运行兼容性。

## 4. 最小CAS实施建议

1. 先按捕获主机核before SHA、root owner和不可组写/真实文件属性；不是同一SHA就停止重新审查。顶层installer/catalog的before来自**Ops270**，不能据此假定220的同路径同版本；若要更新220对应两源，须另捕获220实际字节后做其自己的配对候选。
2. 221已停、磁盘与IP归属已交接、220已绑定alias31且Nexus实际unit/HTTP健康后，才激活220新检查。健康URL不能临时改primary30凑过。
3. Ops270若替换installer/catalog，先短暂停自己的collector timer并等待oneshot完成，精确CAS两文件成一致配对9项，做语法/当前role/primary-IP纯验证，再恢复原timer状态。node exporter不mask/reinstall；其它客机不重装。
4. VM220只对实际health.json做before→new CAS，保留可信root owner/原mode，使用原collector做本机地址/配置`--check`后恢复原collector调度。不要运行旧install-only，它会mask exporter、停timer和重写unit。不要用新默认profile覆盖已有nav/MCP项。
5. Ops270 guest-node fileSD只做已列的一行移除，保留280及其它全部node，Prom配置检查前后都通过后等fileSD自然刷新，不重启Prom。若另有Nexus HTTP fileSD条目，则fresh读取后仅变归属标签到220/publish，仍保31 URL；当前未捕获该文件，不在此候选伪造。
6. 校验原4units与新3units各active、Nexus HTTP31健康、采集成功、node仅30；Ops总15target稳定UP，280保持可采集。规则、告警receiver/Token和NFS/FileBrowser配置不改，不发人工告警测试。
7. 失败时仅恢复本次文件前置字节与原timer状态，不动Nexus数据卷/凭据/构建盘。历史artifact标签与证据不全局替换。

canonical源正式切换在实际安装后另审。`canonical-reference/`保留了对当前canonical的最小retarget（含原resource默认profile保持）；canonical before SHA仍需匹配，不能把运行旧版的其它默认profile逆向覆盖canonical。所有安装成功和Prom目标结果由主AI实际回执签证。

## 本次实际应用补充

九个原节点以顶层runtime-family候选成对CAS；资源280经新鲜SHA证明原文件等同canonical原版，因此仅280使用canonical-reference候选，保留其resource白名单和NFS profile。应用均通过本机guest_gate/privateIP/collector原生check，未运行installer或重启业务/导出器。最终见../monitoring-guests-applied.json和../monitoring-final.json；初始candidate状态只代表准备时点。
