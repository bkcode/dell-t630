# Puyu专属Nexus空仓库与发布机配置对接

更新：2026-11-11，Asia/Shanghai。本次仅处理用户授权的第1、2项：在既有Nexus新增Puyu专属空仓库/受限身份，并将发布机统一私有YAML接入配置适配器。不迁移旧制品、不清旧库、不改Go/Java源码、不编译/发布业务、不创建或切换业务分支。

## 已完成：空仓库与权限

Nexus继续运行于VM220，入口http://192.168.19.31:8081，无新VM、服务重启或容器替换。原管理员、旧仓库/账号/权限/数据与密码保持，匿名访问仍关闭。[创建回执](provision-result.json)、[权限测试](permissions-result.json)。

| 仓库 | 类型与策略 | URL与用途 |
| --- | --- | --- |
| puyu-releases | Maven hosted；RELEASE / ALLOW_ONCE | /repository/puyu-releases/；正式版本禁止同路径重发 |
| puyu-snapshots | Maven hosted；SNAPSHOT / ALLOW | /repository/puyu-snapshots/；仅快照版本 |
| puyu-public | Maven group，仅含上面两个hosted | /repository/puyu-public/；Puyu内部制品统一读取入口 |

puyu-public不含旧Finger/imnull仓库或外部proxy。它是内部制品group，不是所有Maven公共依赖的镜像；项目既有Maven Central、Gradle plugin portal和JitPack直接访问合同保持，Nexus内部网络不开放出口。

| 身份 | 授权 | 禁止 |
| --- | --- | --- |
| puyu-reader | 只读/browse新group及两个hosted | 上传、删除、管理、旧区访问 |
| puyu-publisher | 新group/hosted读取，两个新hosted add/edit | delete/admin、旧区读取/写入 |

两hosted曾用本次专属fixture验证上传201、reader及group读取字节一致、reader写403/publisher删除403；release重复发布400。管理员仅清理本次测试fixture，最终0components/0assets，未迁入真实业务产物。[历史建库前基线](before.json)保留。

## 配置层对接：已完成并验证

新适配器artifact_exec.py已在独立bkcode/deploy-public main提交并推送`2d8f5410bfbc94f409d9f701592c61e39f9653b9`，配置来源是可选artifacts YAML，将既有NEXUS_URL、NEXUS_PUBLISH_URL、NEXUS_USERNAME、NEXUS_PASSWORD注入既有build.bash进程。只提供CLI显式入口，不改build/common执行实现，不把它自动接入MCP。

VM220两个新身份口令只存root受保护600文件，已写入/opt/deploy-public/config.local.yaml（ub600、ignored）；不输出真实值、摘要或提交Git。旧MCP APIkey、环境映射、源码目录、targets和Git身份保持。Mac完整75项测试通过（11.992秒），固定/bin/bash专项10项通过（0.995秒）；均为工具配置层验证，不是业务构建/发布。发布机已Git快进至同一SHA，Linux75项通过（39.161秒），统一YAML已接入且旧配置/MCPkey保持，show/check与固定build.bash的ls只列项目通过；没有运行Gradle/业务构建或publish。[连接后检](connected-postcheck.json)已验证私有YAML里的两组身份实际认证，MCP协议与保护行为保持；本次空仓库和配置对接已完成，真实业务构建条件仍未齐备。[使用手册](usage-manual.md)。

CLI原prod→main、dev→dev，MCP仍仅dev/loopback18765，真实deploy关闭，旧forced-chainfenced。新仓库/适配器不解除这些限制。

## 尚未具备真实构建条件

[只读构建输入盘点](build-inputs.json)表明：六个业务/公共库源码仍main/clean，未运行Gradle；若干当前版本为1.0.0，gateway为0.0.1，均不是-SNAPSHOT，不能因选择dev就直接发入SNAPSHOT策略仓库。私有gradle-conventions插件与公共库未导入新空group，需要后续明确供应和版本方案。

不从旧imnull/Finger区复制这些依赖，不为了构建通过给新账号旧区权限，不擅改版本或创建dev分支。六仓库此前dev远端缺失合同仍有效。今天配置就绪不等于依赖齐全、构建成功、业务已发布或Java/Nacos健康验收。

自动备份仍只正式MySQL/Nacos；新Puyu仓库不新增自动备份，220私钥不导出、不整机备份。旧221迁移/退役是上一阶段历史，本次不迁盘、不恢复221，也不清Nexus现有数据。

[发布机应用回执](publisher-applied.json)核ub600/ignored、两组凭据已配置、MCPdev-only/loopback且deploy关，Nexus/导航PID保持、Nexus未重启、无凭据导出。show/check明确network_checked=false，不能单独冒作实际连接验收；连接证明独立保存在connected-postcheck.json。

## 连接与保持性验收

[连接后检](connected-postcheck.json)使用真实私有YAML身份读取本次不存在资源路径，两组均返回预期404；这是通过认证后的空资源结果，不是资产读取成功或401/403。先前fixture上传/读取/拒绝测试证明权限，清理后仍0组件0资产。MCP认证协议通过，匿名401、浏览器Origin403，仍dev-only/真实deploy关闭、没有新任务，prod SSH未配置。

六业务/公共库工作树main/clean及HEAD保持，无fetch/checkout/build，没有数据迁移、Nexus重启或Go/Java业务启动，真实口令未导出。Mac75项（11.992秒）/固定binbash专项10项（0.995秒）、Linux75项（39.161秒）仅签工具适配与配置层；固定build.bash ls只列项目，不编译/发布。
