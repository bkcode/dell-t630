# 21网可信管理LAN放行后：服务侧剩余限制清单

采集：2026-11-09T14:48:52.209941+00:00。本轮只读，未改任何ACL/密码/配置/schema/服务，未再执行源DB导出。root正在将21/24作为可信管理LAN访问19所有IPv4/GW自身；网络放行与账号授权、内部监听是不同层次。

| 层次/机器 | 实测剩余限制 | 对21客户端的含义 |
| --- | --- | --- |
| GW190 + PVEbridge | inet dell_gateway19与bridge dell19_acl为中央策略；宿主forward0 | 全LAN新策略/持久化由root单独验证，此清单只证表存在，不据此签完整规则已放行。角色东西向/MAC-IP隔离仍保留。 |
| GW190 SSH | WAN21.23/LAN19.1，SSH0.0.0.0:22/[::]:22；ub Match源21.164 pubkey=yes/password=no/kbdinteractive=no | 两IPv4都有SSH监听，但仍需原密钥；无需改密码或关闭hostkey校验。 |
| GW190 DNS/DHCP | DNS19.1:53与loopback，DHCP只eth1 | 应访问批准的19.1DNS，不等于21.23必须开放所有服务监听；不新增WAN DHCP。 |
| MySQL210 | Docker3306仅bind19.20；mysqld bind=*；root@%/nacos_test@%已存在 | 中央ACL放行后仍需原密码和grants，root%不是无密码。应用finger_*test账号Host只19.45及历史10.63.20.20，21来源使用这些账号仍受Host限制。 |
| 发布240 | deployer key仅from19.30、restrict、固定dispatch，sshd禁TTY/forward；baseline_migrated=false | 21可信不赋予发布账号任意shell或业务部署，fence保留。ub仍原key-only管理。 |
| NAS260 | 三share hostsallow已含21/24、19/24、127.0.0.1、VPN10/24，deny空 | 21CIDR无需额外NAS来源修改；账号、reader/writer与匿名拒绝仍适用，不改成ALL。 |
| Penpot250 | frontend19.50:9001；import9002只127.0.0.1；MCPhelper未publish | 使用前端及其认证MCP路由；不能把loopback9002/内部helper“不通”当网络故障或额外公开。 |
| Lark270 | bridge仅172.18.0.1:19093，DynamicUser/NoNewPrivileges，原LoadCredential路径存在 | 这是AM内部认证transport，不是普通LAN访问入口；不公开端口、不读hook/token、不增加接收人。 |

## 明确未做与后续判断

- MySQL只SELECT user/host/account_locked及bind_address，JSON包含这些允许的元数据，没有password/authentication_string/plugin/hash/grants或业务行查询。历史10.63Host条目未删；若以后清理需独立检查所有消费者，不因网络迁移直接DROP USER。
- 240仅选定sshd有效字段、authorized_keys选项布尔和fence布尔，没有打印公钥材料/私钥/完整配置。key-only不等于TCP不可达。
- Docker只读指定ports/Mounts等字段，无Env/Cmd/healthlog。Lark只核内部bind/原secret引用路径布尔及publicunitSHA，不读秘密或发送消息。
- root网络规则可能在本采样时继续提交。完整21/24放行/回程/持久化/role矩阵以root独立规则验证为准；本清单不替代实际客户端连接/登录验收，也不承诺现有应用登录权限全放开。
- 没有Java启动、Nacos配置写、源导出、数据库/schema改动、备份、密码修改或Git操作。所有后续写统一由root，用户本轮密码与业务认证保持原样。

机器可读证据：[restriction-inventory.json](restriction-inventory.json)。
