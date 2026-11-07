# Nexus 同版本 AMD64 准备包

状态：`target-prepared-writers-stopped`。已向 owned VM221 复制公共包、建立无秘密目标配置并创建停止状态容器。源 `nexus3` 保持运行，未发布制品、修改源仓库、停服或复制源数据。源 HTTP Server header 证明版本为 **3.84.0-03 (COMMUNITY)**；源旧配置使用可变标签，但本目标已固定对应 AMD64 子 manifest，见 `images.lock.json`，不拉取 latest。

源数据约 457,660 KiB，数据库为 H2 (`nexus.mv.db`)。首次迁移保持相同版本和完整数据，升级单独安排。目标角色资源来自 plan，Nexus容器设3 GiB上限，入口Nginx额外64 MiB，仍在4 GiB来宾预算内（约960 MiB留给OS/运行时）；JVM 改为 Xms512m/Xmx1536m/direct768m，实际解析/上传并发仍待验证。

## 文件

- `compose.yaml`：固定 AMD64 digest，内部 UID/GID 200，持久化 bind mount，目录缺失不自动创建，健康探测和日志外的应用状态仍需验收。
- `.env.example`：只含非敏感路径和绑定示例；正式 `.env` 放受控目录。
- `prepare.py verify-image`：只读查询源 index，验证当前固定 AMD64 digest，既不 pull 也不写 registry。
- `prepare.py init-target`：仅允许 root/Linux/AMD64，准备空目录并赋予 UID/GID200，不更改已有数据目录。
- `backup-source.py`：仅在源容器已停止的冷备窗口打包全量 `/nexus-data`，不自动停源。
- `restore-target.py`：仅恢复到已准备的空目录，核对版本、SHA和 tar 路径后还原并赋予 UID200。

## 目标依赖与执行顺序

主 AI 拟分配 VM221 / `10.63.30.20`，LAN 入口 PVE `192.168.21.22:8081` DNAT 至来宾8081，最终以主 AI 分配为准。来宾安装 Docker Engine/Compose，数据目录建议放持久数据盘 `/srv/nexus/data`，为制品增长预留容量和告警；开机先确认数据盘挂载，再启用 Compose，不能因目录存在而误写系统盘。

示例步骤均待主 AI 在获分配的目标执行，不在 Mac 源环境执行：

```bash
sudo python3 prepare.py init-target --data-dir /srv/nexus/data --storage-mode rootfs
# 在受控 env 文件设置 NEXUS_DATA_DIR=/srv/nexus/data 和 NEXUS_BIND_ADDRESS=0.0.0.0。
sudo python3 prepare.py check --env-file /etc/nexus.env
sudo python3 manage.py check --env-file /etc/nexus.env
sudo python3 manage.py pull --env-file /etc/nexus.env
```

RAID 重建期间先不进行镜像下载、数据恢复或大型写入。数据导出时由主 AI 安排源 Nexus 写入暂停并正常停容器；只备份 H2 文件或只复制 blob 不能代替完整一致快照。

```bash
python3 backup-source.py --confirm-quiesced --output /private/controlled/nexus-snapshot
```

上例输出路径需要主 AI 指定真实私有路径，目录700、文件600。脚本在源仍运行时会拒绝执行。快照传到目标之后：

```bash
sudo python3 restore-target.py --confirm-empty-target \
  --snapshot /srv/nexus-snapshot --data-dir /srv/nexus/data
sudo python3 manage.py start --env-file /etc/nexus.env
```

恢复后先执行只读健康检查和已有制品下载校验，再验证发布机对版本锁定 API 包的解析。源仓库不做写测试；目标如需发布验收，只使用专门验收仓库和可丢弃坐标，避免覆盖真实版本。账号、仓库配置和权限跟随受控数据恢复，不输出原密码。

HTTP LAN 是临时入口阶段；正式 HTTPS、仓库访问策略、备份目的地和恢复演练仍待验收。源和回退点在目标验收前保留，回切须考虑新上传制品，不能只改 Maven 地址。

## 目标、源版本与挂载门禁

`assignment.json` 固定主 AI 分配的来宾 IP（10.63.30.20），存储模式初始 pending。init/restore/manage 变更均拒绝 PVE 宿主、错误 IP、非 root/Linux/AMD64、远程 Docker endpoint/context，以及 Name 不属于本机的 daemon；PUBLIC/绑定地址不作为来宾身份证明。所有 Docker 变更显式使用本机 rootful Unix socket。

`init-target --storage-mode rootfs` 是主 AI 明确选择根文件系统存储的动作，脚本核实实际目录确实属于 `/`。如果使用独立数据盘，应改用 `--storage-mode dedicated --mountpoint <实际挂载点> --filesystem-uuid <实际UUID>`；脚本核对实际挂载 UUID，拒绝路径逃逸和未挂载目录。

独立盘模式自动合并 restart=no overlay。恢复后由 `sudo python3 install-mount-gate.py --env-file /etc/nexus.env` 安装带 RequiresMountsFor/BindsTo 的 unit，再 `systemctl start dell-nexus`；不通过裸 Compose up 启动。没有 systemd mount-gated invocation 时脚本拒绝 dedicated start。磁盘缺失时可执行受控 stop，防止停服务也被 mount 检查挡住。

停写之前先在源端运行 `python3 source_guard.py`。它核对原 OrbStack daemon ID、固定 source-index、实际容器 Image ID/RepoDigest、镜像 version 标签；备份前再次检查。冷备 receipt 的 source_version 来自重新检查的实际镜像 version 标签，不是写死的说明文字。源版本/镜像漂移或 Docker context 指向别处时，备份在创建输出目录前拒绝，不自动升级或重新锁定。

## 默认无公网出站模式

恢复的 Nexus 数据可能含旧 proxy 仓库和上游认证，因此默认禁止 Nexus 本体连接公网：它只接 `backend` internal 网络，没有普通出站网络，也不直接发布主机端口。hosted 仓库和已有本地制品保留，旧 proxy 配置不代表允许调用；远端拉取在审查和明确授权前保持不可用。

轻量 Nginx gateway 双接 ingress 与 internal backend，发布8081并只向固定 `http://nexus:8081` 转发，不挂载秘密、Nexus数据或Docker socket。它不能由请求参数选择外部上游，也不是通用正向代理。这样避免依赖internal-only容器对LAN DNAT回程的实现细节。内部Nexus即使尝试使用恢复的旧认证，也不能经gateway作为外网代理外发。

上线仍需验证：LAN/来宾通过发布端口访问本地hosted制品正常；Nexus网络声明确实为internal-only；无源凭据的独立网络探针证明backend无公网出站。**不通过访问旧proxy仓库来做拒绝测试，也不发送原上游认证请求。** 有公网网络的gateway不含源代理凭据，不能把它作为给Nexus开放出站的理由；默认网络隔离不得为追求proxy仓库可用而解除。

## 2026-11-06 目标准备实测

10:43 +08:00 只读复核：VM221 `artifact-service` / 10.63.30.20 使用 classic overlay2，DockerRootDir=/var/lib/docker；独立 `/srv/nexus` ext4 UUID 为 assignment 中实际值，`/srv/nexus/data` owner/group200、0750、内容为空。无秘密 `/etc/nexus.env` 为0600。

Nexus和gateway仅created、均未启动。Nexus只接`nexus_backend`，该网络Internal=true；gateway接backend+ingress。固定AMD64镜像已缓存且精确引用可解析。证据见 `guest-preparation.json`。没有源凭据或数据迁移，也没有真实proxy请求；实际hosted/网络拒绝/应用认证均pending。

主AI正在集中等待用户选择“新独立实例”或明确授权迁移指定源数据/必要身份。选择确定前不启动writer，不对源做停写、备份或凭据传输；不要把空目录准备等同于已完成源仓库恢复。
