# 每台机器的配置与文档

更新：2026-11-10，Asia/Shanghai。Nexus合并与221退役已按本次原生回执完成，现役PVE宿主＋12来宾＋3停止模板共16个目录。iDRAC属PVE管理面。配置是公开离线合同，不是现场秘密导出或完整恢复包。

[机器可读索引](index.json)与[plan.json](../plan.json)约束身份/资源；[Git来源主表](git-repositories.json)和[Git总览](GIT-REPOSITORIES.md)约束代码归属。每目录均有README/config/config-sources/GIT-REPOSITORIES，来源SHA只核仓库文件，不自动证明与guest逐字一致。

| 类型 | 机器入口 | 地址 | Git来源 |
| --- | --- | --- | --- |
| pve | [pve](pve/README.md) | 192.168.21.22 | [Git](pve/GIT-REPOSITORIES.md) |
| lxc | [cf-tunnel](ct100-cf-tunnel/README.md) | 192.168.19.5 | [Git](ct100-cf-tunnel/GIT-REPOSITORIES.md) |
| vm | [network-gateway](vm190-network-gateway/README.md) | 192.168.19.1 | [Git](vm190-network-gateway/GIT-REPOSITORIES.md) |
| vm | [data-prod-db](vm200-data-prod-db/README.md) | 192.168.19.10 | [Git](vm200-data-prod-db/GIT-REPOSITORIES.md) |
| vm | [data-prod-infra](vm201-data-prod-infra/README.md) | 192.168.19.11 | [Git](vm201-data-prod-infra/GIT-REPOSITORIES.md) |
| vm | [data-test](vm210-data-test/README.md) | 192.168.19.20 | [Git](vm210-data-test/GIT-REPOSITORIES.md) |
| vm | [publish-service](vm220-publish-service/README.md) | 192.168.19.30 / alias192.168.19.31 | [Git](vm220-publish-service/GIT-REPOSITORIES.md) |
| vm | [java-prod-01](vm230-java-prod-01/README.md) | 192.168.19.40 | [Git](vm230-java-prod-01/GIT-REPOSITORIES.md) |
| vm | [java-test-01](vm240-java-test-01/README.md) | 192.168.19.45 | [Git](vm240-java-test-01/GIT-REPOSITORIES.md) |
| vm | [penpot-service](vm250-penpot-service/README.md) | 192.168.19.50 | [Git](vm250-penpot-service/GIT-REPOSITORIES.md) |
| vm | [nas-media](vm260-nas-media/README.md) | 192.168.19.60 | [Git](vm260-nas-media/GIT-REPOSITORIES.md) |
| vm | [ops-service](vm270-ops-service/README.md) | 192.168.19.70 | [Git](vm270-ops-service/GIT-REPOSITORIES.md) |
| vm | [resource-service](vm280-resource-service/README.md) | 192.168.19.80 | [Git](vm280-resource-service/GIT-REPOSITORIES.md) |
| template | [tpl-docker-base](tpl9001-docker-base/README.md) | 未分配 | [Git](tpl9001-docker-base/GIT-REPOSITORIES.md) |
| template | [tpl-linux-base](tpl9010-linux-base/README.md) | 未分配 | [Git](tpl9010-linux-base/GIT-REPOSITORIES.md) |
| template | [tpl-java-acceptance](tpl9011-java-acceptance/README.md) | 未分配 | [Git](tpl9011-java-acceptance/GIT-REPOSITORIES.md) |

## 合并后的归属

VM220 publish-service为6CPU8GiB、primary30＋Nexus服务alias31，原build和Nexus各100GiB卷独立。31继续原Nexus8081，不另计VM/node；SSH管理使用30/220自身host key。旧221已移出当前索引与Git表，历史资料保留在[归档](../archive/machines-vm221-artifact-service-20261110/README.md)，禁止据归档启动第二个31所有者。

现役12来宾（11VM＋1LXC）、3模板，45vCPU87GiB，10node＋5Ops共15targets；资源280节点保留，仅NFS/5服务检查、FileBrowser退休/8080关闭。230/240统一/mnt/resources、精确双客户端exports/root_squash/UMask0002/挂载守卫保持。模板本轮不变。

Puyu工具来自deploy-public main213f，CLI prod/main dev/dev、MCP仅dev/loopback18765；六业务源仍main且缺上游dev，新预检按设计拒绝；prod目标未配、真实deploy关闭、旧链fenced、Java不启。Penpot8a与Puyu设计/MCP维持各自已验合同，NAS仍官方镜像。

## 备份和维护

自动备份仍只正式MySQL/Nacos，不含Nexus、资源或其它来宾；本次221冷备仅PVE。发布私钥只220，禁止整机备份/快照导出220或复制私钥；CF备份只PVE。秘密/private/数据库/VMA/上传文件不放此目录或Git。

[合并验收](../completion/20261110-nexus-merge/README.md)、[合并维护手册](../completion/20261110-nexus-merge/usage-manual.md)、[NFS手册](../completion/20261110-nfs-only/usage-manual.md)、[全局人工手册](../19-manual-operations.md)。旧13来宾/16UP与双机221只属于对应历史，禁止重放旧初始化器/迁移器。
