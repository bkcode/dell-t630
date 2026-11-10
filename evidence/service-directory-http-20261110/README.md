# 服务导航：HTTP与紧凑全宽布局

用户后续明确不需要HTTPS，并要求移除顶部导航、减少页面外侧空白。本期只更新VM220已有导航，不改其它服务协议、路由或业务程序。

入口：**http://192.168.19.30:9080/**。无需账号密码，仍仅分组、搜索、筛选、复制、跳转；写接口405。当前源码提交`ddccc2b98bbb3dfdc9de649443dc3fcdc7b4860f`，HTTP模式先由`c141506`引入，两个提交均在管理机deploy/main本地，未代推原4条既有用户提交。

- [HTTP切换回执](applied.json)：仅导航重启，移除LoadCredential/证书启动参数，14入口读取正常，旧TLS材料仅留未使用的历史。
- [布局发布回执](layout-applied.json)：去顶部header，标题区紧凑，取消1430px居中最大宽度，按新提交5文件导出部署，原保护服务身份保持。
- [浏览器验收](browser.json)：1920px桌面main x0/width1920；390px手机无横向溢出；两者topbar0/14条入口/表单0。[桌面图](desktop.png)、[手机版](mobile.png)。
- [最终只读后检](final-postcheck.json)：HTTP200、14入口、自身链接HTTP、无HSTS、无凭据指令/运行时凭据目录或环境，文件摘要一致，原发布机服务不变；16targets与导航unit指标均UP。

完整日常操作、源码地址维护与GET-only排障见[导航使用手册](../service-directory-20261110/usage-manual.md)。首轮HTTPS的证书/浏览器回执保留为[历史交付](../service-directory-20261110/README.md)，不能当作当前访问要求；现在使用HTTP，无需接受导航证书。未改FileBrowser/PVE/iDRAC等目标服务自身的协议。

源码仍`bkcode/deploy/service-directory`，运行只读release新版本；原源码4条未推送用户提交保持，更新只在本地提交，不自动推送或重写历史。程序回退/源码清单维护按手册，不重跑fresh安装器。
