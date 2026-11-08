# 2026-11-08 局域网与互联网测速

用户宽带：武汉湖北中国移动，下行标称1000M；上行额度未提供。测速在约21:02–21:23进行。用户公网IP未写入公开证据。

## 已得到的有效结果

| 路径 | 实测 | 解释 |
| --- | --- | --- |
| Mac有线en0 → PVE21.22 | **937.54Mbps** | 单HTTP流128MiB合成载荷，明确源21.230，接近千兆有效TCP吞吐 |
| PVE21.22 → Mac有线en0 | **571.40Mbps；复测709.60Mbps** | 128/256MiB单流、无PVE磁盘IO；方向不对称，原因未定 |
| Mac有线 → 路由21.1 / PVE21.22 | 平均0.489 / 0.586ms；各0/10丢包 | 小样本空闲ICMP，不是长期质量证明 |
| Mac有线 → Apple香港节点 | **下160.80 / 上58.56Mbps**，基础RTT101.86ms | 原生networkQuality顺序25秒；现有路由策略/远端路径，不是武汉移动裸线路验收 |
| PVE有线 → 腾讯云国内镜像CDN | **153.89Mbps**，4连接共64MiB全部206完成 | 国内跨网CDN实际下载，不等于运营商接入上限 |

[机器可读汇总](summary.json)、[有线LAN](LAN-wired-en0.json)、[反向复测](LAN-wired-download-confirm.json)、[有线延迟](LAN-wired-latency.json)、[有线互联网](Mac-wired-networkQuality.json)、[国内CDN](PVE-domestic-CDN-download.json)。

Mac原默认WiFi为21.116，用户后将默认改为有线en0/21.230，千兆全双工；PVEeno1与用户截图WAN也为千兆。测试没有修改接口优先级，是用户自行调整。Mac有线正向938Mbps说明这条LAN路径没有固定100Mbps协商瓶颈；反向较低不能仅凭HTTP单流定位为网线/交换机/服务器故障。

## WAN接收丢弃计数

用户两张OpenWrt截图：RX包约1.77M→2.24M，RX dropped约27.23K→30.07K，收发errors及TXdropped均0。估算增加47万接收包与2840丢弃，相比约0.6%；**不是互联网端到端丢包率**，不能归因仅为本次测速。Linux的rx_dropped可含资源不足、协议未处理、L2过滤等，且不同显示接口可能组合计数。[Linux官方统计说明](https://docs.kernel.org/networking/statistics.html)

目前不能凭累计rxdrop把原因定为光猫、坏线、运营商或CPU。应由路由器管理员先只读核真实WAN设备统计、CPU/softirq、softnet、队列、SQM/offload与代理负载，再决定变更。

## 路径限制与失败样本

- PVE访问常规speedtest配置时经198.18FakeIP并被识别为MicrosoftGB出口，而用户确认是武汉移动，说明该路径不能代表本地运营商。原生networkQuality的not_proxied仅表示应用未设置显式HTTP代理，不能排除OW透明分流。
- 中国移动旧武汉节点已无法解析；国内大学节点虽有真实国内目的IP，吞吐低且超时，不据此判定接入线路不达标。
- Ali官方镜像302到其HTTP对象存储，目标不可连接；没有有效测速，不能把结果零当作带宽为零。
- 后台Python的LAN socket、以及新装原生iperf3测试连接均遇本地访问限制；记录失败，未改macOS隐私权限。故使用原生curl配合限时内存HTTP传输，**不是完成了标准iperf3验收**。
- 原WiFi上行128MiB未完整完成；较小WiFi复核可能与WAN末段重叠，不作纯LAN基线。Mac优先有线后以明确en0结果为准。
- 有线源21.230 ping网关19.1受管理来源策略限制，但同源访问Penpot/Nexus/Jellyfin均HTTP200，不当作LAN链路100%丢包。

## 操作边界

仅一次性测速：不启用Mac外部探针、不改OpenWrt/PVE网络、防火墙或业务配置、不传业务数据。PVE测试内存监听绑定21.22且限已知来源/随机路径、限时自动关闭；本机临时合成文件自动删除。PVE已有5201 iperf监听不是本次创建，不擅自停止。Mac安装了iperf3 3.22及其OpenSSL依赖，无后台服务。

后续判断1000M套餐是否达标，需要已确认直连的本省/邻近移动节点、单独有线测试与路由端负载/丢弃增量；本轮**没有修改代理来强制直连**，故不下“运营商只给160M”的结论。
