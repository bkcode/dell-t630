# 免登录服务导航源码独立审查

审查时间：2026-11-10 13:49，Asia/Shanghai。结论：**源码 PASS，未发现当前范围内 P1/P2 阻断**。

本记录仅适用于用户最终收窄的匿名只读服务导航。现役范围是预览、分组、关键词搜索、环境筛选、复制地址与外链跳转；没有登录、应用账号、口令、会话、CRUD、版本 CAS 或 JSON 运行状态写入。之前可编辑目录草稿的源码、测试与审查结论已由本次结果替代，不能用于最终服务验收。

本次审查只覆盖当前源码与本地检查。目标机器原生安装、TLS 实际链路、LAN/WG 门禁、浏览器操作和重启持久性由主任务另行验收；本记录不把启动回执冒称上线完成。

## 审查范围与发现

- bkcode/deploy：`service-directory/server.py`、三个固定 Web 文件、维护清单 `services.json` 和重写后的 `tests/test_service_directory.py`。
- Dell：`infra/service-directory/install.py` 的固定五文件 release、UID/GID2001、TLS 私钥凭据、原生 unit 和自有 nft 输入表。
- 初始维护清单为 14 个已登记 Web 入口，只有名称、地址、分组、环境、说明、显示状态和固定 UUID，不含第三方密码、token、DSN 或签名 URL。不是目标健康检测结果。
- 无剩余 P1/P2 阻断；源码符合最终只读范围。审查未读取凭据、SSH 私钥或原有 deploy 配置，未连接远端、运行 installer/发布脚本/nft，也未请求清单中的服务地址。审查者仅写本文件。

## 后端边界

`--catalog` 在启动时只读加载与验证一次，将 enabled 的记录序列化为不可由请求修改的快照。`GET /api/services` 无需 cookie 即可返回 `{services:[...]}`；另有 `/health` 和四个固定静态入口。POST、PUT、PATCH、DELETE、OPTIONS、HEAD、TRACE、CONNECT 进入统一 405 且 `Allow: GET`，旧登录与会话 GET 路径已不存在。未注册的未知 HTTP 方法沿标准库返回错误，同样没有写入执行路径。

请求只接受与监听 IPv4 地址及端口精确匹配的 Host；loopback 开发另允许 localhost。拒绝查询参数、未知路径、目录浏览与路径穿越；静态资源不映射任意请求路径。响应含 no-store、CSP、nosniff、frame deny、no-referrer；TLS 模式有 HSTS，无 Set-Cookie。程序未导入外部请求客户端或 subprocess，也无数据库或目录 JSON 写入函数，不会探测、代理或执行链接目标。

目录最多 100 条、512 KiB；顶层与行字段精确校验，拒绝重复 JSON 键、无效枚举/UUID/布尔值、过长文本、控制字符与非法 Unicode。链接仅绝对 HTTP/HTTPS，禁止 userinfo 和危险字符。公开目录应只维护可向内网使用者展示的信息。

生产模式强制 TLS，HTTP 仅显式 loopback 开发可用。SSL listener 禁止在 accept 阶段执行握手；worker 内先设置 10 秒超时后握手。BoundedSemaphore 最多接受 16 个 worker，握手失败与请求线程退出释放容量。单连接 socket 超时是 I/O 空闲超时，不将其表述为整个请求的绝对截止时间。

## 前端与部署边界

前端仅一次 GET API 读取，明确 `credentials: omit`，未保存口令或会话。没有登录、增删改按钮或抽屉。所有数据文本以 textContent/DOM API 展示；未发现 innerHTML、动态脚本执行或 localStorage。链接再次校验 HTTP/HTTPS，使用新窗口与 noopener noreferrer；复制只写本机剪贴板。刷新失败保留上次数据并明确提示，不把失败展示为健康状态。

安装器只接收固定五个 release 文件与提交 SHA；源码字节由主任务在提交后通过 `git show <committed SHA>:<file>` 导出，安装器记录每文件摘要。它不会复制整个原 deploy 仓库、现有 config、MCP jobs 或源私钥。清单随 root-owned release 部署；专用 UID/GID2001 的程序只读，unit 没有 ReadWritePaths 或应用状态目录。没有应用密码/账户文件；唯一新 secret 为服务 TLS 私钥，经 root-only 目录与 systemd LoadCredential 传入。OS 专用服务用户不等于应用登录账号。

HTTPS 固定 `192.168.19.30:9080`，专属 nft 仅处理该端口，允许 LAN21/24、WG10.66.66/24 与本机，拒绝其他来源。helper 精确校验自身规则，原子替换自身表，不 flush 全局 ruleset。安装器不调用 publisher、Java、Nexus、Penpot 业务操作；保留原保护服务的前后快照比较，回执明确 native acceptance pending。

## 本地验证与实际限度

- 独立运行 `python3 -B -m unittest discover -s tests -p test_service_directory.py -k CatalogTests -v`：**2/2 通过**，覆盖 URL/schema/容量边界及生产 TLS/非 loopback HTTP 启动拒绝。
- 独立运行 `node --check service-directory/web/app.js`：通过。
- AST 编译安装器与生成的 firewall helper；分别断言自身 nft 表不存在/存在时的精确事务字节：通过。没有实际执行 nft。
- backend owner 与主任务均报告亲跑重写后的完整 **6 项测试通过**；本审查未启动监听器，没有把旧草稿 15 项测试作为当前证据，也没有把 owner 的 HTTP 测试转述为独立亲跑。

实际页面分组/搜索/复制/跳转、匿名 HTTP 200、写入方法拒绝、TLS 慢握手并发、专属输入策略与只重启新服务的验收，仍以主任务后续带时间的原生/浏览器记录为准。

## 审查文件指纹

审查时 deploy HEAD 为 `81148e8614ee5c49e6f9e4d1b85aebef8adfb33d`；最终源码提交与部署 revision 由主任务后续记录。生产目录清单路径说明已复读，与实际 release/services.json 一致；安装回执字段明确为 application_accounts_or_passwords_created，区分 OS 服务用户。下方摘要只绑定本次已读源码，不绑定之前的可编辑草稿。

| 文件 | SHA-256 |
| --- | --- |
| service-directory/server.py | bc6136fc70b1bdfb46ce372556d49206b7ae2642f0ecb81211bf6a1c26fc05db |
| service-directory/web/index.html | a270c400d10ba1279246f4063242eff0bf11c1b1fb3a96da89af5af7d3bcb111 |
| service-directory/web/app.js | 7bce82e498b9134525e44307edfdb18427ba147671a5d4c2ce75bc43a3da6d5c |
| service-directory/web/style.css | abb5cf0c46be2c1dca14ea9f2f775a503b2ff0d428f587a3519d4fb408301d80 |
| service-directory/services.json | 75da2126ec648a4f6c364846b26480833552d358080cb0e031da7771afad8a8f |
| tests/test_service_directory.py | 0b276b3118fb33ebec724a3f6376b0b28ded981c5e902d4a1f2e80b281b56489 |
| Dell infra/service-directory/install.py | fd266464f2aafc5d405361e1707c6983f041b931be5b5929de7886bae0cc1c33 |
| service-directory/README.md | 18ce4f293d4eeb369d86324acb223cf4ee5617b258db9a8c9f33811c5087e186 |
