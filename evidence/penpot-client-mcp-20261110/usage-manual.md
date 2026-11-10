# 本地Penpot skill MCP连接服务器

2026-11-10，Asia/Shanghai。**配置已切换，实际新进程验收通过；当前聊天仍缓存旧连接，需要客户端重载。**

## 当前连接

| 名称 | 连接方式 | 服务器能力 |
| --- | --- | --- |
| penpot | Mac /usr/bin/ssh → ub@192.168.19.50 → 受控stdio中转 | 4项设计MCP工具 |
| penpot_import | 同一SSH路径，独立import模式 | import_penpot_file/get_import_status |

配置文件为用户私有`~/.codex/config.toml`，原工具审批设置及其它配置保持。已去掉这两项旧localhost URL/旧静态Authorization，服务器MCPkey只在VM250现有导入容器中读取，不复制到Mac、不出现在argv/普通文档/Git。Mac SSH仍用原`~/.ssh/yang_local_rsa`，严格校验`~/.codex/penpot-server/known_hosts`中已有可信VM250公钥，不转发agent或关闭校验。旧完整配置仅保存在`~/.codex/backups/penpot-server-20261110-191823/config.toml`，目录700/文件600，不能提交。

Skill本身由`~/.penpot-ai-kit`及已安装的`~/.agents/skills/penpot-*`提供，未复制或重写设计规则；本次改变的是Codex MCP连接配置。官方配置参考：[Codex MCP配置](https://developers.openai.com/codex/mcp)。

## 生效步骤

1. 在Codex客户端重载MCP连接；若没有重载入口，退出并重新打开Codex。
2. 再开始一次MCP调用，首工具仍为high_level_overview。
3. 只读核对currentFile.id应为`01b580ec-b5e6-8057-8008-ec70da4cd212`，名称puyu。

当前聊天已经实测仍返回Mac旧文件`9eb8678d-764d-810b-8008-e237712e9048`；新配置独立启动的两项进程却已成功连接服务器。两者不能混为一谈。GUI工具明确禁止操作com.openai.codex，因此没有绕过限制自动点击重载，也不杀/重启宿主客户端。最后一项验收保持pending，收到重载结果后再签通过。

## 默认工作文件

用户选择刚导入的puyu。现服务器常驻编辑器默认打开`puyu-components`，避免默认渲染56,852对象的主页面；同文件仍含puyu-mobile、puyu-components、puyu-mobile · 商城三页。MCP真实只读返回的file/page IDs均匹配，未创建、删除、重排或修改图层。只改变.env的PENPOT_WORKER_FILE_ID与PAGE_ID，team和所有秘密保持；worker原有成员权限可访问，不添加授权。沿原监督器短停重启，11服务健康，Puyu统计/版本保持。

## 服务端实现与维护

公开代码`/opt/dell/penpot/runtime/client-mcp/{launch.py,relay.mjs}`由本仓库infra/penpot/client-mcp管理。launcher限定VM250/root、root-owned不可组写的真实文件和两种mode；在已有penpot-penpot-import-1内按需运行固定SDK1.30.0，连接同机原MCP，透传tools/list、tools/call及instructions/cancellation。stdout仅MCP协议，异常脱敏，EOF退出并清理HTTP session。没有新增容器、端口、HTTP监听或修改防火墙，也不重编镜像。

两个客户端连接会各增加一个短生命周期Node进程，仍受导入器1GiB/512PID限制；测试关闭后原生统计约32.62MiB/1GiB、12PIDs。此时点不是满负荷保证。服务器需在线且Mac能经LAN/WG访问其SSH；本次实际测试为当前Mac LAN，不冒签其它设备/VPN端到端。

回退客户端时先备份当前配置，只恢复这两个MCP区块及原审批策略，避免覆盖后来其它设置；完整私有备份只供精确差异恢复。回退服务端默认文件需先核当前任务空闲/私有事务`/root/dell-penpot-client-context-20261110`，不能重放switch-context.py、旧fresh-init或整库覆盖。Mac原Penpot实例仍保留运行，当前不会自动停止它。

证据见[五项验收](acceptance.json)，已通过4项，当前客户端重载1项待办。[配置回执](local-config-applied.json)、[新进程RPC](configured-client-probe.json)、[Puyu切换](context-applied.json)、[最终健康](final-postcheck.json)、[缓存区别](current-session-cache.json)。
