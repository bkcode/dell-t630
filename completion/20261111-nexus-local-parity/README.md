# Nexus本机配置对齐：保留服务器额外仓库

更新：2026-11-11，Asia/Shanghai。用户在说明此前自动审批拒绝原因后，明确选择“只对齐本机配置，保留服务器额外7库”。本轮不删除任何仓库、组件或制品，不迁移本机数据，不清库/重建，不重置账号密码。服务器变更与最终连接后检已由根任务执行并留证。

## 现有基线与选定方案

[本机只读配置](local-repository-configs.json)有9个参考库：默认Maven4、NuGet3、imnull2。服务器[修改前基线](server-before.json)有15库，缺少imnull-snapshots；已有Puyu3、Finger3和dell-acceptance共7个额外库全部保留。已新增原缺失的imnull-snapshots，现为**16库，不是9库**。

| 范围 | 本轮处理 |
| --- | --- |
| maven-releases | 默认RELEASE/ALLOW_ONCE保持，不能误改为覆盖 |
| maven-snapshots | 默认SNAPSHOT/ALLOW保持 |
| maven-central | 保留已有proxy，不放开Nexus隔离网络 |
| maven-public | 按本机顺序聚合imnull-snapshots、imnull-releases、maven-releases、maven-snapshots、maven-central |
| imnull-releases | 对齐本机RELEASE/ALLOW，允许后续授权覆盖；本轮不重发/删除旧制品 |
| imnull-snapshots | 缺失时新增SNAPSHOT/ALLOW，初始空库 |
| NuGet3 | 保留本机参考语义及服务器现有数据，不迁数据 |
| Puyu3、Finger3、dell-acceptance | 全部保留，不删除、不清数据、不改这些仓库配置 |

原50components/1347assets已验证原ID、路径与校验元数据保持；不以“同本机布局”推导服务器额外库可以删除。本轮读取验证优先取已有imnull资产，不主动制造远端proxy cache miss。group包含central不等于Nexus外网代理已可用，真实远端下载未签。

## 当前发布机映射与权限

统一私有YAML的读取入口改maven-public，dev发布映射imnull-snapshots，prod映射imnull-releases。仍用原puyu-reader/puyu-publisher账号和密码，保留原Puyu权限；只追加标准6个Maven仓库的读取，publisher另加imnull两个hosted的add/edit。无delete/admin，不修改其他角色。账号名称保持不代表继续使用旧puyu-public映射。

Nexus服务仍在220 alias19.31:8081，管理primary19.30；MCP仍dev-only/loopback、deploy关、旧链fenced，原APIkey、paths、targets、SSH/Git身份保持。业务源码、Go/Java、版本和分支不改，既有公共Maven/pluginPortal/JitPack定义不改，不构建/发布业务。

## 当前状态

[服务器配置已应用](configuration-applied.json)：16库、额外7全保留，新增imnull-snapshots，仅更新maven-public与imnull-releases；原50components/1347assets的ID/路径/校验元数据保持，DELETE调用0。原密码/其他角色、Nexus与导航PID/容器保持，无网络改变或数据导入。

deploy-public公开example/test/docs默认值已提交并推送main/`bba3542d5f28adc0377a6ef8745bf9aa17423544`，实现不改；Mac75项通过（12.566秒），[发布机](publisher-applied.json)同步同SHA、Linux75项通过（37.158秒）。私有YAML仅改3个仓库名、ub600/ignored，原口令/MCPkey/其他配置保持；show/check及固定build.bash ls只列项目通过，无Gradle/Go/Java构建发布。[实际连接后检](connected-postcheck.json)已使用私有YAML两组身份，经maven-public读取现有imnull对象，两组均HTTP200且原字节校验一致；9个本机参考定义按已审字段语义相等，16库及旧数据均保持。离线check与实际读取证据分别保存，不相互代签。[操作说明](usage-manual.md)。

[reviewed-target.json](reviewed-target.json)保留了最初含remove_extra_repositories的历史候选，[approval-status.json](approval-status.json)记录自动审批拒绝历史及用户后续安全选择；现行[approved-safe-target.json](approved-safe-target.json)明确保留额外7库。旧reviewed-target不是当前执行计划或删除许可。用户后来明确选择保留额外库，任何执行器都不得读取旧remove列表进行删除。当前授权以本页及新执行回执记录的保留方案为准，旧文件仅审计留存。

本次没有数据迁移、Nexus网络放开、整机备份或自动备份扩围。220发布私钥仍只220，CF档只PVE，自动备份仍只正式MySQL/Nacos。

## 最终签收范围

[连接后检](connected-postcheck.json)确认原50组件和1347资产保持，两组真实YAML身份经新group读取同一已有imnull资产均200/字节一致；只忽略proxy接口返回的空authentication字段形式差异，未忽略真实认证配置。MCP协议通过，匿名401、浏览器Origin403，仍dev-only/deploy关且无新job。

没有重新发布/覆盖旧资产、写入新业务制品、执行DELETE或本机数据导入；没有Nexus网络改变、远端proxy cache miss或外部下载测试，没有Gradle/Go/Java构建或业务部署。配置对齐已完成，真实构建与外部依赖可用性未签。
