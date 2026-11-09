# 统一资源服务器交付

完成：2026-11-10T00:20:38.241841+08:00（Asia/Shanghai；目录名按11月9日开始的实施阶段保留）。用户明确正式/测试共用一台资源服务器、同一个目录。

| 角色 | 地址/路径 | 实际交付 |
| --- | --- | --- |
| VM280 resource-service | 192.168.19.80，server /srv/resources | 2vCPU/2GiB，32GiB系统盘＋100GiB新数据盘，原生NFSv4.1 |
| VM230 java-prod-01 | 192.168.19.40:/mnt/resources | 与测试同一个共享根，finger实际读写通过 |
| VM240 java-test-01 | 192.168.19.45:/mnt/resources | 同源19.80:/；保留/mnt/dell-artifacts原状态 |

直接阅读 **[资源服务器使用手册](usage-manual.md)** 与[机器目录](../../machines/vm280-resource-service/README.md)。

[8项验收](acceptance.json)全部通过：[独立NFS验收](native-acceptance.md)证明两机finger共享读写/追加/删除、root_squash拒绝与卸载后底目录写入拒绝，fixture全清；[新资源VM重启](reboot-exercise.json)证明UUID守卫、NFS自动恢复、fsync合成文件持久及客户端恢复，物理PVE没有重启，未重启两running OS。

[最终只读后检](final-postcheck.json)：13来宾运行、3模板停止，45vCPU/87GiB配置预算，保守125GiB余38GiB；16targets全UP，资源5服务指标均1、内部Lark原通道只增加新角色，不发人工测试消息。新资源继承fish4.0.2，root/ub默认Bash；不改变原排除对象。数据盘UUID57d8158e-5fcf-4dd2-8cb4-b47b1e54ed7b，实际文件系统约97.9GiB。

宿主只管理/L2且双栈各接口forward0；桥新增280身份与230/240→280 TCP2049、Ops→2809100，旧角色边界保持。资源本机只接受两精确NFS客户端，管理21来源和其它19peer的NFS TCP负测均拒绝，SSH管理正常。网关仅添加resource-service.dell.home.arpa记录，不改路由/NAT/网络接口。

## 交付边界和保留记录

资源是统一文件存储，**没有启HTTP图片入口、切换应用上传配置、启动Java或迁入旧文件**。Finger将来可使用file.upload.path=/mnt/resources并另配正确HTTP域名/访问控制；Puyu目前的MySQL内容/授权下载不会自动转成NFS。三组件测试凭据沿用用户指定设置，不因资源搭建重置。

资源文件不纳当前自动备份，现行仍仅正式MySQL/Nacos；Nexus仍221独立，不执行合并。模板本次未修改；客户端工具/disabled配置可作为将来模板预置建议，clone需逐机授权/登记再激活。

[首次DNS权限失误与恢复](DNS-recovery.json)保留：umask使新配置过严、DNS短暂启动失败，已先恢复原配置/0644，再以显式fchmod及service-user可读门禁完成唯一记录更新。没有路由/应用重启。客户端stack/共享数据根预检兼容性在启业务前修正，严格source/opts/UID/GID仍保持；[首次fixture断言失败](native-first-attempt.md)完整保留，新nonce按约定UMask0002重验，没有改权限凑通过。

本期不签应用上传/下载、真实用户访问、负载SLO、资源备份恢复或独立灾备；使用手册的后续扩容/新client步骤不是预先授权。
