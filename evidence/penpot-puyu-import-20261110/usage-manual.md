# Puyu设计项目导入与使用

2026-11-10，Asia/Shanghai。已通过本机官方导出、SSH私有传输、VM250官方导入完成，源为本机“Penpot MCP 验证”文件的rev2821快照；该文件的三个页面全部是Puyu，因此只导入该文件，不导两份无关UI Kit。源设计与本机账号保留。

## 访问

在服务器owner账号工作区选择项目 **puyu** → 文件 **puyu**。也可[直接打开组件页](http://192.168.19.50:9001/#/workspace?team-id=13a31dab-5204-818d-8008-e6fd5e2efc53&file-id=01b580ec-b5e6-8057-8008-ec70da4cd212&page-id=0c6166a2-b4f0-8093-8008-e31e54275406)。原登录表单默认填入仍按已授权LAN/WG来源生效。

| 页面 | 对象数（含页面根对象） |
| --- | ---: |
| puyu-mobile | 56,852 |
| puyu-components | 435 |
| puyu-mobile · 商城 | 956 |

全文件共58,240个图形、19个组件、零外部库依赖。源团队/文件内部旧名称不作为目标项目名；目标新增puyu项目，ZIP导入器原名若保留则仅重命名新文件为puyu。服务器旧“Penpot MCP 验证”和其余六文件保持，未覆盖。

## 验收

[API回执](api-result.json)核三页顺序、对象数、图形类别/组件/颜色/字体/库统计一致，并逐一比对旧7文件的项目、名称、revn/vern与完整设计data哈希。[浏览器](browser-acceptance.json)已登录并打开组件页和商城详情画板，图片与布局可见；未逐图检查58,240对象或验收原型交互。页面可能保留很小的视口缩放：可在左侧选择画板，再按Shift+2缩放至选区，仅改变浏览视口。

[最终后检](final-postcheck.json)记录11healthy、原监督器及Git版本保持；这是数据导入，不包含此前等待明确推送授权的首次引导代码部署。测试浏览器cookies/localStorage清理、会话关闭。

## 数据和维护

本机归档仅保留`private/penpot/puyu-import-20261110/`，服务器归档位于`/srv/penpot/application-import-puyu-20261110/`，目录700/文件600；归档与截图不进Git。目标事务journal为`/etc/penpot/puyu-import-20261110.json`，记录源/目标映射与已验证状态；旧`application-id-map.json`保持。用户账号、密码、Token、源session与整个PG库均未迁移。

本次是快照副本，之后本机修改不会自动同步。再次导入先核journal/目标项目与当前版本，明确作为新副本还是更新范围，不能盲重跑`target.py import`或旧全量迁移器。启动客户端20秒回执等待曾超时，但实际后台事务继续，已通过只读systemd/journal确认并等待成功，没有重发导入。今后启动这种oneshot应使用非阻塞回执。

当前自动备份仍仅正式数据库/Nacos，Puyu设计与本次归档不因此加入备份。没有修改Java、Nexus、NAS或其它服务器。
