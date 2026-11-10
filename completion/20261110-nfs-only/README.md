# 资源服务改为仅NFS

2026-11-10，Asia/Shanghai。用户明确确认“仅保留NFS，停用FileBrowser并移除导航与监控”。本目录记录VM280的受控停用与NFS现状验证；VM220导航运行部署和VM270最终Prom读回由主AI在合并维护窗口统一完成，不在本子任务冒签。

已完成：

- VM280 `resource-service / 192.168.19.80`保留原NFSv4.1及独立数据UUID，230/240继续真挂载`192.168.19.80:/`到`/mnt/resources`，正式/测试共用同一根。
- `dell-filebrowser.service`与`dell-filebrowser-firewall.service`停用、取消自启并masked。原unit已移出现役systemd定义，受保护副本仅留本机root回退目录；TCP/UDP8080无监听，独立`inet dell_filebrowser_input`表已撤。
- 280健康配置精确去掉FileBrowser服务与HTTP检查，原5项资源角色服务均active。NFS配置、exports、版本、原输入规则和受保护服务PID/启动身份保持，未重启NFS或客户端。
- FileBrowser原state、账号/JWT等凭据保留原保护路径，不导出、不改密码、不重置、不读秘密内容；共享资源文件未迁移或清理。
- 单次server专属canary由两个client以finger只读读回后已清理。当前测试没有client写入；早先双client写入验收单列为历史，不拿来冒签新的写测试。
- 原Finger导航源码精确移除FileBrowser入口，14→13项，其它条目行保持；仅补模块README，没有Git提交、推送或VM220运行部署。

证据入口：[停用回执](retirement-result.json)、[NFS当前验证](NFS-verification.json)、[最终只读后检](final-postcheck.json)、[导航源码变化](navigation-source-change.json)、[操作手册](usage-manual.md)。当前健康规范为[health.nfs-only.json](health.nfs-only.json)。

首次只读审计脚本原名inspect.py与Python标准库冲突，退出1但完成了只读回执；没有服务器写，之后本地重命名为audit-nfs.py。用户随后暂停，期间未执行停用；再次明确确认方案后fresh审计到before-resume.json才执行本轮事务。before.json保留暂停前事实，不能当变更证明。

本目录脚本是本轮固定身份/配置的一次性审计及事务资料，不是通用一键卸载器。已有事务目录时停用器拒绝重放；不要因FileBrowser缺失而重新运行历史fresh初始化/安装器。资源仍未纳入自动备份，本轮未修改模板、Nacos/Java、NAS或公网服务。


当前FileBrowser已按后续明确授权从现役安装路径移除（不再只是masked停用），专属闲置账号删除，NFS及资源文件保持；旧说明仅阶段历史。详见[移除后NFS使用说明](../20261110-filebrowser-remove/README.md)。
