# 免登录服务导航原生只读验收

结论：**PASS**。验收完成于 2026-11-10T13:53:19.244904+08:00（Asia/Shanghai），只覆盖 VM220 新增导航与一个未授权 VM210 TCP 负测，不签整个基础设施或目录链接目标的可达性。

目标为 `https://192.168.19.30:9080/`。部署源码锁定 `bkcode/deploy` 提交 `63b8c0873936e94f8483c4f1f8747aedb0180d43`。完整机器可读检查、HTTP 状态、文件 SHA256、systemd 属性、自有 nft 规则和时间见 [native-acceptance.json](native-acceptance.json)。

## 实证结果

- 使用 guest 自有 `/etc/dell-service-directory/tls.crt` 作为专属 CA，以标准库 HTTPS 验证证书与 IP；没有使用跳过证书验证。GET 首页、index.html、app.js、style.css、health 及 API 均 200。
- 不发送 Cookie 或 Authorization，`GET /api/services` 返回 14 个 enabled 入口，响应不设置 session cookie。程序只有只读导航；未对清单链接目标发送请求。
- POST、PUT、PATCH、DELETE、OPTIONS 至 API 均 405。旧 login/session/logout GET、query、路径穿越、目录浏览及直接 catalog 路径均 404；错误 Host 为 400。
- API 负请求前后 services.json SHA256 相同。五个 release 文件逐一精确匹配本机 `git show <commit>:service-directory/<file>` 取得的提交字节与 guest manifest，不把当前工作树冒充部署源码。
- 固定 release 文件为 root-owned 且非 group/other writable；服务为 UID2001 `servicedirectory`，active/running，MemoryMax 为 128 MiB、TasksMax32、ProtectSystem=strict、NoNewPrivileges=yes、无 ReadWritePaths。未创建应用状态目录、密码或登录凭据文件。
- 9080 仅监听 `192.168.19.30`，未监听所有地址。只读取自有 `inet dell_service_directory_input`：五条规则均限定 9080，精确允许 LAN21/24、WG10.66.66/24 与本机，其他 TCP/UDP 丢弃。没有执行或重载 firewall helper，也没有修改其它 nft 表。
- VM210 对 `192.168.19.30:9080` 的一次 TCP connect 负测约 3.005 秒超时；没有发送 HTTP 或凭据。此现象证明该测试路径未建立连接，不单凭超时归因于某一层设备。
- SSH、Docker、node exporter、guest health timer、networkd 的 PID/启动时间/active/substate 与安装 manifest 中保护基线完全一致。没有重启、重新发布或修改这些服务。

## 方法和边界

通过 `scripts/control.py` 的 guest 封装与已存在 target info，使用严格 host key 校验访问 VM220/VM210；未调用 trust_guest、更新 known_hosts 或读取私钥正文。VM220 远端脚本仅做专属 CA HTTPS 请求、公开 catalog/release/manifest 摘要、systemctl show、ss 和自身 nft table 读取；VM210 只做一次 TCP connect。

命令族为 `sudo -n python3 -I -B -` 内的 `http.client.HTTPSConnection(..., ssl.create_default_context(cafile=...))`、公开文件 SHA256、`systemctl show --property=...`、`ss -H -ltn sport = :9080` 和 `nft -j list table inet dell_service_directory_input`。没有读取 TLS 私钥、secret 环境、发布密钥或其他服务配置；没有运行发布脚本、installer、nft helper 或 restart。测试 write-method 请求被拒绝，没有写 catalog 或运行状态。

本记录未做应用重启、浏览器交互、WG 真实客户端登录路径、其它 nft 表全量前后差异、PVE/所有来宾库存或监控验收；这些由主任务另记。对 14 个入口的 HTTP/健康状态没有做探测，不将目录展示解释为目标服务健康。
