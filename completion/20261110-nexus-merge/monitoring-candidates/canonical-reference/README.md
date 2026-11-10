# Nexus并入220：最小监控源候选（未安装）

范围仅此目录。没有修改canonical源，没有连接服务器，没有对VM280/FileBrowser/NFS做任何操作。候选以当前仓库 `infra/ops/guest-baseline/{guest-targets.json,install-guest-baseline.py}` 为底；它不是现役配置导出，也不是可直接执行的安装包。

## 精确变化

- guest-targets只移除`artifact-service`/VM221/19.31的物理节点行，保留其余10行的顺序和全部字段；描述性scope计数改为10。其余历史元数据原样保留，不把resource280旧pending字段冒充今天运行结论。
- 安装器ROLES移除artifact-service；把Nexus默认service/http profile从artifact-service retarget到publish-service。
- publish-service的Docker候选角色启用。Nexus组件为`dell-nexus.service`，HTTP必须是`http://192.168.19.31:8081/service/rest/v1/status`；publish-service物理地址/唯一node exporter仍是19.30。
- 其余角色的profile、candidate对象和unit文本语义保持。resource-service行/defaultprofile保持，collector源码完全未改；没有恢复或覆盖FileBrowser TLS/HTTP配置。

before/new SHA在[manifest.json](manifest.json)。[validation.json](validation.json)记录7项本地纯函数检查通过；验证程序没有执行installer动作、unit、Docker、HTTP、包管理或SSH。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 completion/20261110-nexus-merge/monitoring-candidates/validate_candidates.py
```

## 不能重跑旧install流程

`install-guest-baseline.py --install-only`会mask exporter、停timer并安装unit，超出本次最小增量；不能为了替换两个源文件而运行它。现役220已有导航和puyu-deploy MCP等监控项，不能用候选默认profile覆盖整个`health.json`。

本目录没有复制collector；若直接在该目录执行install动作还会缺少预期同级文件。只把此目录当源候选审查，不当服务器bootstrap。

## 最小CAS安装建议（由主AI执行）

1. 先fresh读取目标220现役两份监控源、`/etc/dell-guest-monitoring/health.json`、collector源码与timer/exporter状态，并记录public SHA、owner/mode和私有恢复副本。**运行文件SHA不一定等于仓库before SHA**；不匹配时先审查差异并按运行字节重新形成精确候选，不能force覆盖。
2. 在原221已停、磁盘/IP归属已交接、220 alias31已实际绑定且Nexus unit/HTTP健康之后，才激活新Nexus检查。collector的纯validate要求31确为本机地址；primary30-only时应拒绝alias31检查。
3. 若替换220的installer和guest-targets，必须作为一致的配对版本CAS安装：新枚举10和新catalog10需同时生效。父目录/文件保持可信root所有、不可组写；只短暂停止本次collector oneshot/timer以避免读到半对配置，写后做语法/target_for/current-role校验再恢复原timer状态。不要mask/reinstall exporter或改变其30:9100绑定，不重装其它客机。
4. `merge_publisher_health.py`提供纯函数，输入fresh现役220 profile，只追加docker/Nexus单位和alias31健康检查；原导航/MCP/HTTP/候选项/notes保留。已有同名Nexus检查而URL不同则拒绝，不能偷偷替换。先对生成候选做collector validate及无副作用`--check`，然后CAS原子替换本profile。测试中的publisher profile只是合成fixture，**不能复制到服务器**。
5. Ops270的fileSD另做fresh最小delta：只移除221的物理19.31:9100 node target，保留220的30:9100和其它所有行；原Nexus HTTP若在fileSD中保留31 URL，仅将归属标签并入220/publish-service。不得把31当第二个220 node exporter，也不得用旧全量targets覆盖当前列表。已有280 target只保留，不对280部署代码或改配置；总targets以真实before减一个物理node核算。
6. 其它现役客机目前可继续用各自一致的旧installer/catalog配对版本；不为全局角色收缩而重装所有客机。canonical源正式切换由主AI在安装验证后完成，历史证据不全局替换artifact-service字符串。Prom规则/告警接收对象/Token、资源/FileBrowser配置不因此变化，不发人工告警测试。
7. 复核220 collector输出包含原服务与新Nexus且总采集成功，Nexus HTTP来自31，node只30；270 Prom配置检查通过并稳定scrape。失败恢复这两源/profile各自前置字节和原timer状态，不改数据卷或凭据。

[merge_publisher_health.py](merge_publisher_health.py)只构造JSON对象；没有安装入口。源候选与实际安装成功分别签证，不把本地7项通过当作服务器监控已生效。
