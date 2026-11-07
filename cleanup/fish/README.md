> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# fish install-only进度

已在root明确授权窗口完成8个保留guest：190、200、201、210、220、230、240、260，fish与fish-common均4.0.2-1，binary输出fish4.0.2。每台APT模拟无移除/已有包升级，仅新增fish-common、libpcre2-32-0、fish三包；no-install-recommends，NEEDRESTART_MODE=l，没有apt update/fullupgrade/autoremove。

每台安装后以ub在临时XDG目录运行fish --no-config --private smoke并清理；ub/root登录shell前后仍/bin/bash，没有chsh、用户shell配置、插件或主题。新的严格SSH连接全部通过，核心服务/容器PID、启动时间和Health前后相同，没有请求服务重启，网关190最后轻量安装也保持核心网络服务。

当前汇总runtime-status.json，逐guest原始元数据在evidence/guest*.json。初始只读盘点inventory.json/inventory-summary.json保留原时间，不覆盖成事后值。

220已在Nexus/DockerAPT释放锁后独立窗口安装完成；Publisher UID999/GID989、/bin/sh、仅publisher组、未进docker组及私钥stat完全保持，私钥未读/未备份、未改Docker daemon或启动Nexus。CF100、Penpot250、Ops270、待退役221/231/232、全部旧QA和PVE宿主均未安装/改shell。三模板9001/9010/9011仍停止且未开磁盘/安装，包状态unknown；更新方法见PLAN.md：root fullclone临时builder、安装封版candidate，再独立clone身份/SSH/JDK/Docker验收，不启动原template，模板firstboot生key策略与永久instance保key策略分开。

默认shell选择由root向用户集中确认；当前完成的是binary安装，不是默认fish登录。模板/220/默认shell不能用本次8guest通过签收。

2026-11-07补充：root明确开放221独立fish-only窗口后，221也完成fish/common4.0.2-1；当前共9guest，证据evidence/guest221.json。Nexus两容器与Docker的ID/PID/start/health保持，未停服/迁移；维护授权仍独立pending。模板三个candidate QA已通过且释放，见template-QA-summary.json，最终core VMID替换由root负责。
