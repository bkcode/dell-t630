> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# MCP 查询参数日志修正

状态：目标准备包已接入，真实来宾应用/认证验收未执行。此变更不重建三个已审镜像，不改原镜像归档、源容器或源配置。

## 已确认的问题

已构建目标前端 `dell-penpot-frontend:2.18.5-amd64`（ID `sha256:fa395b809ed21c53a01387567264100fb28c553f1dd4af113f38c50de3b739bc`）的 `/entrypoint.sh` 会以 `/tmp/nginx.conf.template` 渲染实际 Nginx 配置，并按 `enable-mcp` 渲染 MCP location 模板。

原主模板的全局 `penpot_upstream` 格式包含 `$request` 和 `$http_referer`。两处 `access_log off` 分别在 `/readyz` 和独立 8082 健康 server，不能覆盖 `/mcp/stream` 或 `/mcp/ws`。这两个 MCP location 没有自己的日志覆盖，继承全局格式。离线 dummy 请求复现了 access 日志中的 userToken 查询；上游连接失败时，Nginx error 日志还会同时记录完整 request 和 upstream URI。

## 最小运行时修正

- 主模板仅将 access 请求行改为 `$request_method $uri $server_protocol`，移除 Referer 字段；状态、字节数、User-Agent 与上游状态/连接时间/响应时间/地址保留。
- 两个 MCP location 各增加 `error_log /dev/null;`，避免 Nginx 固定错误格式再次输出查询。仅影响这两个 location；其他路由 error 日志保持原样。
- 所有 MCP proxy_pass、Upgrade/Connection、HTTP 版本、`$is_args$args` 原样保留；没有改认证、权限、token、请求或响应状态。
- `templates/` 是有效模板，`templates.lock.json` 记录原/新 SHA256，`runtime-template.diff` 是最小差异。
- `compose.query-safe-logs.yaml` 提供独立 overlay；相同两条挂载已接入基础 `compose.yaml`，避免普通目标启动漏用补丁。两条均 bind 到镜像读取的 `/tmp/*.template`，read_only=true、create_host_path=false。entrypoint只读模板、写生成配置，不覆盖已挂载模板。
- 模板是无秘密公共配置，权限0644，确保 Linux 容器内 penpot UID 可读。秘密文件仍独立保持0600。
- `target.py check` 通过 `runtime_logging.py` 校验原/新hash、文件权限、精确源/目标挂载、只读和不自动建路径，并核对MCP路由除日志行外未改变。

## 离线验证与边界

`audit.py` 只使用已审目标镜像，创建 network-none、无端口发布、无secret或源卷的短时容器；仅注入明确虚构的 `DELL_LOG_AUDIT_DUMMY_NOT_A_REAL_TOKEN`。镜像没有curl/wget，fixture通过容器内Bash TCP访问自身loopback。测试的单worker和外部字体空配置仅限fixture，不进入有效运行时模板。

结果见 `audit.json`：

1. 原模板：两个MCP URI的access和上游失败error日志均包含dummy查询。
2. 修正模板、上游失败：两路仍返回HTTP502，脱敏access保留502和耗时，access/error均无dummy。
3. 修正模板、loopback stub：两路HTTP200，dummy查询原样到达stub，access/error无dummy。

这不是实际MCP/SSE/WebSocket协议或真实认证验收；只证明Nginx路由/查询转发保持、失败状态未掩盖和此两类日志不包含dummy查询。MCP应用、Backend及其他日志面仍需按实际部署独立核查。

所有fixture容器在结束时按新建ID和专用label清理。原17个源容器/标签状态与制品构建证据一致，原归档SHA256保持 `6d27b16c5bd9e9cecbd4c825734ac2e1bc9cee2d10a8f38d5f26da32bd7036d1`。

## 主AI应用方式

小包 `../query-safe-runtime-overlay.tar.gz` 仅含公开Compose、目标检查代码、模板、hash/diff和此审核证据，不含.env、凭据、assignment或业务数据。先在准备包副本校验清单，保留已有配置备份，再复制到已核实的目标包位置；不要覆盖实例私有目录或地址/存储分配。由主AI在合适窗口执行目标check及必要前端重建容器，实际生效验收仍pending。

## Git最终运行镜像补充

当前最终frontend从Git ff1783e构建，ID为bd020fb6bddfd77449c26f76ee04ca7b2b50a0ffe8562ebc7b9e294bfcd38b89，保留登录辅助但只提供空密码example。它使用相同锁定2.18.5官方base，运行时模板hash相同，fresh Compose已接入本补丁，实际新MCP key日志检查无泄漏。前文fa395预审镜像与小包只保留审核证据，不是当前完整Git部署包；不要用旧base Compose/target.py覆盖fresh流程。
