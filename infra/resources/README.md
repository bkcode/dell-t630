> 当前状态（2026-11-10）：资源服务器仅保留NFS；FileBrowser两unit已停用并masked、8080关闭、独立输入表及服务/HTTP健康检查已撤。NFS/共享文件/权限和批准客户端保持，原state/凭据仅受保护保留。当前[交付](../../completion/20261110-nfs-only/README.md)与[使用手册](../../completion/20261110-nfs-only/usage-manual.md)优先；下方原NFS实现与FileBrowser扩展过程按各自时间作为历史，不重放安装器。

> 历史扩展（2026-11-10）：同VM280已增加受认证FileBrowser HTTPS管理页，见[新交付](../../completion/20261110-filebrowser/README.md)与[管理使用手册](../../completion/20261110-filebrowser/usage-manual.md)。下方NFS阶段的“不启HTTP”指当时尚未部署管理页/仍不公开业务图片入口；NFS合同与旧验收保留，不据旧描述回退新功能。

# 统一资源服务工具与实施合同

当前已部署并验收：VM280 `resource-service` / `192.168.19.80`，两running共用同一资源目录。实际结果见[交付入口](../../completion/20261109-resources/README.md)、[8项验收](../../completion/20261109-resources/acceptance.json)，人工使用见 **[资源使用手册](../../completion/20261109-resources/usage-manual.md)**。

| 项目 | 现行合同 |
| --- | --- |
| 资源 | 2vCPU/2GiB，9010完整克隆32GiB系统盘，独立100GiB数据盘 |
| 数据 | `/srv/resources`，ext4 UUID `57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b`，root:resources 2770，default ACL |
| 导出 | fsid0，NFSv4.1/TCP2049，精确230/19.40及240/19.45，sync/root_squash/sec=sys |
| 客户端 | 两机`/mnt/resources`源`192.168.19.80:/`，hard/TCP/nodev/nosuid/noexec，systemd automount |
| 身份 | finger原UID999/GID989不变，附组resources GID2980；共用同根，不分正式/测试 |
| 限定 | 不启HTTP/Java、不迁旧文件、不改应用上传配置；资源不纳现行自动备份 |

## 工具所有权与用途

- [provision-pve.py](provision-pve.py)：主AI专用，固定创建全新停止VM280，已完成，**不能重跑**。现役onboot已另设1，order35早于两running，见[实际启动配置](../../completion/20261109-resources/PVE-startup-configured.json)。
- [bootstrap-storage.py](bootstrap-storage.py)：仅280内by-id scsi1、新空100GiB/无签名才可格式化。已有UUID数据盘会拒绝，**不要重跑或去掉门禁**。原盘/宿主/根盘不在范围。
- [policy.example.json](policy.example.json)：固定配置规范模板，UUID=null，不是当前运行状态。实际填UUID策略见[policy.json](../../completion/20261109-resources/policy.json)；运行状态由带时间验收证明，不修改模板status字段冒充部署。
- [prepare.py](prepare.py)：纯本地renderer，除实际UUID外严格约束拓扑/角色，不网络、不挂载、不启动服务。输出server、两clients、未启用HTTP与未来Java依赖候选。
- [install.py](install.py)：来宾固定路径安装器，默认仅准备；`--activate`仅启NFS或automount。root受信目录/hostname/IP/组/UUID/配置漂移均核验，未知现役配置拒绝接管；活跃NFS代码/配置变化需另审维护，不是批量重放入口。
- [guard.py](guard.py)：只读核真实挂载来源/UUID/版本/安全选项与身份。允许已知systemd autofs＋真实NFS叠栈，autofs-only仍拒绝。它不是挂载触发器。
- [gateway-dns.py](gateway-dns.py)：本次精确增加一个资源DNS记录的one-shot工具，已实施，不能重复执行；不改路由/nft/networkd。首次权限问题及回退有[完整记录](../../completion/20261109-resources/DNS-recovery.json)。

## 持久化和权限

server依赖真实UUID数据mount和自有输入防火墙，BindsTo及ExecStartPre守卫防止数据盘缺失时导出根盘。自有防火墙仅原子替换`inet dell_resources_input`，先native nft检查，不flush其它表；loopback保留，外部legacy RPC端口拒绝。精确PVE桥peer规则独立保留，不靠GW泛放行替代东西向授权。

Debian13 mountd默认manage-gids会依据server NSS改写附属组，本合同明确`manage-gids=n`，只信任批准的两客户端AUTH_SYS组2980；不为此创建server UID999，不all_squash、不放宽root_squash。AUTH_SYS不等于加密或抵御恶意client root的身份边界。

客户端underlay root0555，未挂载时finger拒绝写入。NFS客户端可能在CREATE前应用进程umask；要求共享组写入时采用UMask0002，default ACL不能强制放大0600/0644请求。未来Java依赖候选包含挂载guard和UMask，但**本次没有安装业务drop-in或启Java**。

新增client必须同时更新严格policy/renderer/guard/installer角色白名单、exports、输入allowlist、PVE MAC/IP/peer、机器合同及测试。当前安装器只接受server/client-230/client-240，不能仅修改exports后将同一脚本用于任意clone。三模板本次未改；未来可预置工具与disabled配置，逐机登记后再激活。

## 验证记录

最初[validation.json](validation.json)是14项本地候选阶段的历史，不能当最新原生结果。当前资源回归28项（含DNS umask）、installer自测8项；网关45项、桥6项回归通过。原生NFS双机读写/root_squash/缺挂载负测与VM280受控重启见[验收目录](../../completion/20261109-resources/)。两running OS未重启，应用上传下载、HTTP、负载及文件备份/恢复均未扩签。

```bash
python3 -m unittest discover -s infra/resources -p 'test_*.py' -q
python3 -B infra/resources/install.py --self-test
```

仓库只存公开代码/合同/脱敏证据；实际root私有恢复副本与known_hosts/客户端私钥均不进Git。不要重放旧whole-VM备份或把资源文件自动并入正式数据库备份。
