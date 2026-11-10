# VM220 Puyu local发布器：已安装与预检

2026-11-10，Asia/Shanghai。新bkcode/deploy-public main已提交/push，VM220由Git取码到`/opt/deploy-public`，最终`f3991ad5fb0788fc4925685bc287d2aa7e0ff8d8` clean；代码基线5be，最后a0为操作文档更新。5Puyu服务+commonlib main均已克隆。bff-admin最初排除，用户后续新增并登记DeployKey后已接入。

`puyu-deploy-mcp.service`以ub运行、enabled/active，仅监听127.0.0.1:18765；密钥仅服务器统一YAML600，代码/凭据分离。匿名401、Origin403、4工具、项目发现与五服务只读预检succeeded/validated5均实测；真实deploy关闭并验证拒绝。Linux60测试通过，未运行Gradle/Java/Go业务构建或启动。

构建盘`/srv/dell-build` UUID16dc6067-56ef-4687-a314-edc6421f9ed4，专属`deploy-public/{repos,build,mcp-state}`由ub持有700，带挂载UUID门禁。现役导航PID18640保持，旧restrictedpublisher链fenced，不读取/导出原私钥或整机备份。源端指派的7套Gitkey在ub700目录/600文件，服务器pushURL禁用。

[6项验收](acceptance.json)、[最终状态](final-postcheck.json)、[MCP真实协议与预检](mcp-protocol-and-preflight.json)、[源码交付](Git-delivery.json)。初次门禁目录因umask为700导致MCP无法读取已修正为root0755，秘密权限未放宽；失败诊断与修正证据保留。puyu-auth初次Git授权失败后用户补登记.pub，复用原key补拉成功；无身份重生成。

使用说明在源码仓库[发布机安装手册](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)与[完整操作说明](https://github.com/bkcode/deploy-public/blob/main/docs/OPERATIONS.md)。本期未启用真实业务部署：generic发布器尚未接入旧forced-command程序的Puyu业务权限，不能直接打开发布开关假定全链路可用。

后续bff-admin的[key与源码验证](bff-admin-source-cloned.json)、[仅项目目录项更新](bff-admin-config-added.json)及[五服务预检](mcp-protocol-and-preflight.json)为当前结果；[先前四服务预检](four-service-preflight-before-bff-admin.json)仅保留当时历史。服务器MCPkey和其它设置保持，真实发布继续关闭。
