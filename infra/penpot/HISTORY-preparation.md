> 文档状态（2026-11-08）：本页为阶段实施/技术记录，旧网段、角色数和通过结果按原时点解释。基础已恢复；本轮仅补齐与清理，用户暂不迁移/合并，Mac外部探针不需要。当前配置见[访问清单](../../12-service-access-and-operations.md)，范围与恢复证据见[最新交接](../../11-live-handoff.md)；旧初始化器不得重跑。

# 已退役的迁移准备记录

以下为历史准备过程，不是当前执行入口。旧.env/worker身份传输与PG整库恢复路线已被用户最新的Git+官方应用导出导入决定替代。当前入口见README.md；不得据历史命令导出旧身份或停止Mac源服务。

# Penpot AMD64 迁移准备包

状态：`artifacts-built-not-deployed`。已核对源环境、捕获必要私有身份并独立构建三个新的AMD64目标镜像；未导出业务数据、启停源容器或部署目标。

本包保留现有 Penpot 2.18.5、定制 sidebar、resident worker、MCP 和异步文件导入。`images.lock.json` 固定当前源索引对应的 linux/amd64 子 manifest；没有使用 latest。源镜像标签为 2.18.5，部分镜像内的 label 写 2.18.5-RC1，因此迁移以当前 digest 为准，不在迁移中换成新的同名标签。

## 目录与隐私

- `compose.yaml`：11 个服务，平台固定 AMD64；删除登录默认值 secret/脚本端点，Mailpit 不发布主机端口。
- `contexts/frontend`：基于相同官方前端镜像，仅保留 CSS 定制；不包含登录默认值代码。
- `contexts/worker`、`contexts/import`：从现有项目复制源码、锁文件和轻量 Dockerfile，在 AMD64 重新构建。
- `configure.py`：捕获/配置必要身份。源 `.env` 和 worker 凭据只读，内容不输出。
- `target.py`：目标来宾检查、pull/build/create/start/status；变更动作要求 Linux AMD64，不会操作 Mac 源 Docker。
- `backup-source.py`：只在 source backend、worker、import、admin-console 已停写后导出一致快照；该脚本自己不启停源。
- `restore-target.py`：只向空目标数据库和空素材/任务卷恢复，校验快照后执行；不接触源。
- 私有文件在 `dell/private/penpot`，目录 700、文件 600，不放进本包公开配置。应用密钥、数据库密码、worker UUID 和账号/MCP 身份需随一致快照保留。

Linux 下 worker 为 UID/GID 1001，import 为 1000。原 Mac/OrbStack 能让同一 bind 文件对两个用户可读，不代表 Linux 同样成立。`configure.py` 生成两个内容相同、分别 owner 1001/1000 的 600 秘密文件供各自容器挂载；目标需以 root 执行配置，禁止用放宽到 644 解决。

## 当前已核实与依赖

- PostgreSQL 源为 15.19/aarch64，数据库约 47,037,799 bytes，PG 卷约 150,968 KiB；素材约 247,280 KiB，导入任务 5 文件/2,122 bytes。这是单点容量，不是后续增长承诺。
- 所有官方核心/依赖的源 digest 均找到 AMD64 子 manifest；定制上下文依赖锁文件齐全。三个新目标镜像已独立构建并验证AMD64；worker 21项、import 29项测试通过，仍不能替代Intel来宾上完整浏览器、数据恢复和应用验收。
- 主 AI 拟分配 VM 250 / `10.63.30.30`；最终以 plan 和主 AI 分配为准。来宾可按 ub 登录后 sudo 管理 Docker 和配置。
- 当前 LAN 入口方案是 PVE `192.168.21.22:9001` DNAT 到来宾 9001，仅家庭/管理 LAN；来宾不自行设置宿主 DNAT。
- HTTP LAN 阶段显式使用不安全 cookie 标志，`PENPOT_PUBLIC_URI` 为上述真实 LAN URL，worker 使用内部 `http://penpot-frontend:8080` 防止 hairpin。**HTTPS、真实 SMTP 和公网验收仍 pending**。切 HTTPS 时需移除不安全 cookie 标志，并使 worker 的浏览器访问能够正常使用安全 cookie 的可达 HTTPS origin。
- 预留 role 的 16 GiB 内存；Docker 数据建议放已确认的来宾数据盘或足够大的来宾文件系统，至少准备镜像/构建缓存和后续素材增长空间。Docker root、volume 路径与挂载依赖由主 AI 在来宾部署前登记，不能让缺失数据盘时写进系统盘。
- guest 到 Docker Hub、pnpm registry、必要镜像仓库、DNS 与时间服务需要可达；专用 DNS 子网 `172.30.250.0/24` 上线前核对冲突。MCP 经前端同源路由，import 9002 仅来宾 loopback；外部管理用 SSH 隧道或受控入口。
- PVE RAID 当前正在重建，主 AI 要求缓建大写入；本包未开始这些操作。

## 已执行的安全准备

本机执行过 `configure.py --capture-source`，然后按主 AI 给的实际 LAN URL 配置；此命令不把 source 的登录默认值复制到目标。`target.py check` 已通过：11 服务、AMD64 固定、无前端凭据默认值路径、Mailpit 不发布端口。源服务继续运行，数据没有迁移。

后续在目标来宾，以 root 把私有目录放到约定位置（示例 `/etc/penpot`，不含真实值的示例文件见 `.env.example`）。复制完成后先检查文件权限，并重新执行配置以更新私有路径和 Linux UID：

```bash
sudo python3 configure.py --private-dir /etc/penpot --storage-mode rootfs \
  --public-uri http://192.168.21.22:9001 --bind-address 0.0.0.0 \
  --worker-base-url http://penpot-frontend:8080 --allow-insecure-lan
sudo python3 target.py check --private-dir /etc/penpot
sudo python3 target.py preflight --private-dir /etc/penpot
```

准备环境通过且 RAID 允许写入后，按顺序执行；不得并行大型构建：

```bash
sudo python3 target.py pull --private-dir /etc/penpot
sudo python3 target.py build --private-dir /etc/penpot
sudo python3 target.py create --private-dir /etc/penpot
```

上述 root 管理身份与应用容器内部非 root 用户是不同职责。镜像构建需要官方 exporter 中的 Node/pnpm 和浏览器环境，但不需要完整 CLJS 前端编译。

## 一致快照与恢复步骤

1. 本机先运行 `python3 source_guard.py`，核对原 OrbStack daemon ID、所有锁定 source-index、实际容器 Image ID/RepoDigests 和版本；有漂移先更新迁移计划，不能盲目重新锁定。主 AI 记录源和目标状态、通知维护窗口，限制源端新会话/导入请求；等待现有任务完成或明确记录其中断恢复边界。
2. 在源项目仅停止 `penpot-backend`、`penpot-worker`、`penpot-import`、`penpot-admin-console`；保持 PostgreSQL 运行。此停写动作由主 AI 统一执行，不由准备脚本自动执行。
3. 本机以新的私有目录作为输出执行下例；脚本核实每个 writer 已停止，否则在创建快照目录前失败。

```bash
python3 backup-source.py --confirm-quiesced \
  --private-dir /Users/yangzhaohui/work/www/harness/dell/private/penpot \
  --output /Users/yangzhaohui/work/www/harness/dell/private/penpot/snapshot-cutover
```

4. 快照含 pg_dump custom archive、assets tar、import jobs tar、私有部署身份、SHA-256 清单。tar 使用只读卷挂载的临时本地 helper 读取，不会修改源卷。
5. 目标接收完整快照并核对校验值。目标前端、backend、worker/import/admin 不得先运行；不要用空数据库先启动应用制造另一套对象。
6. 在目标执行下例（`/srv/penpot-snapshot` 为主 AI 最终登记的真实收件目录，部署时替换）：

```bash
sudo python3 restore-target.py --confirm-empty-target \
  --private-dir /etc/penpot --snapshot /srv/penpot-snapshot
sudo python3 target.py start --private-dir /etc/penpot
sudo python3 target.py status --private-dir /etc/penpot
```

7. 验证旧文件、素材、团队权限、协作、导出、worker ready/busy、MCP 和异步导入幂等后，再由主 AI 确定切换与源恢复安排。源卷和源配置始终保留；产生新写入后不能只改回 URL 就宣称完成数据回退。

`restore-target.py` 先校验全部文件和 tar 路径，只恢复到空数据库/空卷；中途失败保留目标用于诊断，不自动删除再重试。`restore-complete.json` 只证明脚本完成，功能、HTTPS和完整验收仍需独立留证。

## 当前目标与存储门禁

`assignment.json` 只接受主 AI 分配的来宾 IP（10.63.30.30），目标变更首先拒绝 `/etc/pve`、非 root/Linux/AMD64、IP 不属于本机、远程 Docker context/DOCKER_HOST、非本机 Unix daemon。命令强制使用 `/var/run/docker.sock`，并核对 daemon Name 与来宾主机名；PUBLIC_URI 不能代替来宾身份。

存储模式当前刻意为 `pending`，因此 pull/build/create/restore/start 均不得执行，直到主 AI 在实际来宾明确选择：

- **rootfs**：上面的 `--storage-mode rootfs` 仅在 DockerRootDir 确实位于根文件系统时通过，表示主 AI 明确接受将这些数据放在来宾系统文件系统，不能误指向外部未挂载目录。
- **dedicated**：先由主 AI 将 Docker data-root 安排到实际独立数据盘，再使用 `--storage-mode dedicated --data-path <实际DockerRootDir> --mountpoint <实际挂载点> --filesystem-uuid <实际UUID>`。脚本核对真实 mountpoint/UUID 和路径，拒绝 symlink/.. 逃逸。不要照抄占位值。

独立盘模式自动合并 `compose.mount-gated.yaml`，所有容器 restart=no；`start` 只接受带 systemd invocation 的 mount-gated 启动。恢复后运行 `sudo python3 install-mount-gate.py --private-dir /etc/penpot`，安装并 enable 但不启动；再由主 AI `systemctl start dell-penpot`。unit 使用 RequiresMountsFor/BindsTo 数据 mount 与 Docker，同时给 Docker daemon 本身安装数据挂载依赖（其 DockerRootDir 位于独立盘），停止动作允许在挂载丢失后执行，避免错误地因挂载丢失而拒绝停服务。不得用裸 Compose up 绕过该流程。

恢复脚本在任何素材解包前先检查数据库为空，再检查 **全部** assets/jobs 卷为空；任一卷非空时不开始第一个卷的解包。备份 receipt 包含当时重新校验的源 daemon、source indexes、容器镜像和实际版本，版本/镜像漂移会在创建快照目录前拒绝。

## 已完成的本机制品构建

`local-build.py` 是单独的Mac artifact-prep入口，不调用 `target.py`，不会绕过其来宾保护，也不读取.env用于构建。只允许创建 `dell-penpot-frontend:2.18.5-amd64`、`dell-penpot-worker:2.18.5-amd64`、`dell-penpot-import:2.18.5-amd64` 三个新标签；已有标签若上下文不匹配就拒绝覆盖，不执行push。

编译阶段使用同一锁定版本的原生ARM64 exporter，限制Node old-space 512 MiB、依赖child并发1、网络并发4，按镜像顺序构建。运行阶段仍固定AMD64镜像；worker只复制架构无关的JS dist，import在复制生产依赖前检查3658个文件，无原生addon/ELF/Mach-O。若以后出现原生依赖将构建失败，不能跳过检查。构建客户端auths为空、没有私有仓库凭据；不挂载源卷。

已完成验证：worker21/21、import29/29测试通过；三个镜像在隔离network-none容器中完成AMD64模块/静态资源烟测，登录默认凭据资源不存在；源17个容器的ID、镜像、运行状态、启动时间、OOM/重启次数及源标签映射前后未变。

制品位于 `dell/private/images/custom-penpot-amd64-images.tar`，2,637,143,552 bytes，SHA256 `6d27b16c5bd9e9cecbd4c825734ac2e1bc9cee2d10a8f38d5f26da32bd7036d1`。同目录JSON记录镜像ID、上下文文件hash、构建参数、源前后快照和未部署边界；sha256文件用于传输核对。归档manifest只包含上述3个允许的新标签，全部linux/amd64。目标加载和运行应由主AI在已验明来宾/存储后执行，未在本次artifact-prep中执行。

## 已批准的MCP日志运行时补丁

目标准备包已接入 `runtime/logging/templates` 的两条只读模板挂载，不改变已审镜像或归档。全局access日志不再记录请求query或Referer；仅两个MCP location禁用会含完整URI的Nginx error日志，仍保留脱敏access状态/上游耗时。代理、认证和查询转发不变。离线dummy测试复现原泄漏，修正后无dummy日志、查询转发保持，HTTP502仍返回。

详细证据、原/新hash和最小diff见 [日志补丁说明](runtime/logging/README.md)。`target.py check` 会验证文件和挂载，缺失、被改写、非只读或路径不符时拒绝。小包 `runtime/query-safe-runtime-overlay.tar.gz` 用于主AI分发，无秘密；不能据此宣称实际MCP/认证已验收。

## 2026-11-06 目标公共准备与审批状态

VM250 `penpot-service` / 10.63.30.30 已安装最新无秘密公共包，包含query-safe日志模板；classic overlay2、DockerRootDir=/srv/penpot/docker和独立盘UUID经严格SSH核对，11个固定AMD64镜像已齐备。10:43 +08:00复核无应用容器，目标/etc/penpot私有配置文件均不存在，未启动writer。

向该来宾传输源`.env`和worker身份的单次动作被自动审批在执行前拒绝：目标虽已批准，但具体源身份导出尚需明确用户许可。没有改用其他协议、路径或来源重取；该依赖已交主AI集中确认。用户选择新独立实例或明确批准迁移之前，不执行私有配置、create、源停写或数据迁移。证据见 `guest-preparation.json`，不把“镜像就绪”标为服务或认证验收通过。
