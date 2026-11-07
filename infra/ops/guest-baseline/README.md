> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# Guest-only 监控基线准备

状态：脚本与离线检查已准备，并经主 AI 精确授权，已在12个新来宾完成 **install-only安装停放**；没有激活exporter或collector，没有修改PVE或源Mac。目标只包括 `guest-targets.json` 中的 12 个新 Debian 13 AMD64 KVM 来宾；PVE、CT100 和源 Mac 明确排除。角色/IP来自当前 plan.json 的配置，不把候选地址当成已启用网络。

文件必须作为一个目录一起复制到获准来宾：`install-guest-baseline.py`、`collect-guest-health.py`、`guest-targets.json`。本次已由主 AI审核并通过已有SSH管理通道调用；以后仍不得把这些脚本作为PVE或本机后台任务执行。

## 安装停放模式

在角色名与 hostname 一致的指定来宾，以 root 执行：

```bash
python3 /tmp/dell-guest-monitoring/install-guest-baseline.py \
  --install-only --role data-prod-db
```

脚本依次执行：

1. 核对 root、Debian 13、AMD64、12角色 hostname 白名单和 KVM/QEMU，拒绝 `/etc/pve`、CT/LXC、物理宿主或其他角色。
2. 获取 guest-local 独占操作锁；先 mask+stop exporter service/socket，停放本包 collector，验证9100没有TCP/UDP监听。
3. 检查APT/DPKG锁空闲，最多等待120秒，不删除锁文件、不杀APT进程。APT本身也设置120秒锁等待。
4. 仅在这个隔离来宾的包操作窗口临时设置 `policy-rc.d` 返回101，阻止maintainer脚本启动daemon。原文件/符号链接被完整保留；try/finally恢复原对象及权限，不输出其内容。没有原文件时，结束后移除临时文件。
5. 使用 `apt-get install --no-install-recommends --no-upgrade prometheus-node-exporter`，避免顺带安装 collectors 包及其额外调度。不自动启用DBus或其他推荐服务。
6. 在临时拒绝策略仍有效时，安装结束/失败均再次stop+mask，移除监控enablement链接，验证9100无监听，然后恢复原策略。
7. 安装私网绑定drop-in、本机只读collector及禁用的service/timer定义。collector timer保持disabled/inactive；不执行collector，不写任何健康样本文件。
8. 保存 `/var/lib/dell-guest-monitoring/state.json`，记录实际包版本、mask状态、enablement链接、9100监听和collector停放状态。只有全部检查通过才成功返回。

此模式不 unmask、不启动 exporter、不 enable collector，不改变PVE桥接/nft/NAT。已有基础服务之外没有激活本包的任何监听或定时任务。

`policy-rc.d` 的临时全局拒绝仅适用于这些业务尚未启用的新来宾。若发生SIGKILL/断电或其他管理员同时改变策略，`.policy-rc.d.dell-active.json` / `.policy-rc.d.dell-backup-*` 会保留恢复线索，下次操作拒绝自动覆盖，须由主 AI 审核恢复原策略。不要盲目删除原策略或备份。正常失败路径已通过离线异常恢复测试。

## 未来私网激活模式

仅在宿主网络变更已批准、该角色实际10.63地址已配置、Ops到该来宾9100的规则已获准后使用：

```bash
python3 /opt/dell/guest-monitoring/install-guest-baseline.py \
  --activate --role data-prod-db
```

激活前要求白名单中的精确私网IP出现在UP、global、/24的来宾接口上；临时192.168.21管理地址不能满足条件。通过后才unmask并启动exporter，绑定精确 `10.63.x.x:9100`，不会绑定0.0.0.0、IPv6通配或临时LAN地址。drop-in包含相同的ExecCondition，VM开机时缺少私网地址也不能启动。脚本检查实际9100监听；错误绑定会重新mask并失败，不杀占用端口的其他进程。

此命令默认只激活exporter，collector仍未启用。需要本机服务/HTTP指标时，先核对下述配置，再显式添加：

```bash
python3 /opt/dell/guest-monitoring/install-guest-baseline.py \
  --activate --role data-prod-db --enable-collector
```

启动collector前，会用非特权 `prometheus` 用户执行只读检查，确认systemd状态读取权限；不读取/放宽Docker socket，不因权限不足自动提权。如来宾缺少可用systemd状态读取通道，保持collector未启用，交主 AI处理。安装脚本不修改任何防火墙规则，私网绑定仍需受控ACL才能限制抓取来源。

## 本机只读健康 textfile

配置为 `/etc/dell-guest-monitoring/health.json`，root管理、非敏感0644。install-only 默认只检查SSH、Guest Agent、exporter三个service，`http_checks=[]`，不自动激活应用检查。`role_health_profile()` 为已审核的真实角色候选：数据单元及Nacos readiness、Nexus、测试Java五服务、Penpot、NAS的OMV/SMB/Jellyfin、Ops三项HTTP；正式Java和发布机没有业务单元候选。候选须在应用部署后显式验证并激活。

主AI授权后，在管理工作区运行 `python3 infra/ops/guest-baseline/activate-role-health.py --role ROLE --apply`（本期仅200/201/210/221/240/250/260/270）。helper使用既有严格SSH别名，先核对hostname/IP、root配置权限、实际unit active和无凭据本机HTTP200；保留原有列表顺序与base检查，仅追加已审核目标。原配置备份在来宾 `/var/backups/dell-guest-monitoring/`（目录0700、文件0600），新配置root:root0644原子替换，再start已有 `dell-guest-health.service` 采样，不重启业务。需另外确认Prometheus通过原9100抓取到新指标；不新增跨区HTTP/ACL，不加入尚未部署的通知单元。

collector只读取 `LoadState` 和 `ActiveState`，不读Environment、进程命令行、日志、密码或token；HTTP仅无凭据GET本机接口/loopback的root/health/actuator等白名单路径。拒绝跨来宾地址、认证URL、query、header参数和业务操作路径，不跟随重定向，不关闭TLS验证，不保留响应正文。受保护actuator若返回401/403，只记录失败状态码，不绕过认证或加入秘密。

输出只包括：

- `dell_guest_service_present`、`dell_guest_service_active`；
- `dell_guest_http_up`、`dell_guest_http_status_code`；
- `dell_guest_health_collection_success`、`dell_guest_health_collection_timestamp_seconds`。

数据原子写入 `/var/lib/prometheus/node-exporter-textfile/dell_guest_health.prom`，URL、响应体、Env和日志不进入label。collector以prometheus用户运行，文件系统严格只读，仅允许写该textfile目录；timer约60秒触发，尚未启用。node_exporter从同一目录读取文件，通过既有9100指标端口让Ops读取，不需要为HTTP跨区额外开口。

旧样本不能被当作当前健康：需结合采集时间戳/`node_textfile_mtime_seconds`判断新鲜度。HTTP200和service active也不替代资金、交易、协作或完整应用验收。

## Ops侧配合

`infra/ops/prepare.py --activate-role NAME` 现在只激活该来宾9100，不再隐式启用跨来宾HTTP。HTTP直探保留为独立 `--activate-http-role NAME`，仅在另有明确授权时使用；推荐通过本机collector提供HTTP状态。PVE和CT100不属于此安装清单，其指标仍待未来受控push或单独批准接口，不开宿主监听。

## 当前验证边界

33项离线回归覆盖hostname/PVE/Debian/虚拟化门禁、私网IP前置、APT前mask、临时policy先后顺序及失败恢复、原文件/权限/符号链接保留、并发修改不覆盖、APT锁不删除、监听识别、只读属性及HTTP限制。测试中APT/systemctl/HTTP均为隔离模拟，policy文件仅在private/ops的临时测试目录操作。

本次真实安装记录：`2026-11-06T07:05:31.920668+08:00` 完成VM200/201/210/220/221/230/231/232/240/250/260/270，包版本均1.9.0-1+b4；每台exporter/socket masked、无9100 TCP/UDP监听、无enablement链接、collector/timer未启用。policy原对象inode/权限/内容指纹前后相同，恢复记录无残留；Docker包版本和服务状态未变。232最后执行，首次SSH即就绪，没有重试。

汇总见 [guest-monitoring-install.json](../../../evidence/implementation/guest-monitoring-install.json)，每台另有guest-monitoring-vmID.json的原始脱敏记录。这是安装窗口的停放快照，不代表未来仍处于同一状态。

未验证：私网激活、collector实际只读权限、VM重启、跨区9100可达与监控告警。没有执行这些后续动作。

## 官方依据

- [Debian 13 node exporter及推荐包](https://packages.debian.org/trixie/amd64/prometheus-node-exporter)
- [Debian node exporter手册](https://manpages.debian.org/trixie/prometheus-node-exporter/prometheus-node-exporter.1.en.html)
- [Node exporter textfile collector](https://github.com/prometheus/node_exporter#textfile-collector)
