# 合并后发布机与Nexus操作手册

更新：2026-11-10，Asia/Shanghai。最终切换已按本目录实际回执签收；本文提供人工维护合同，不是自动执行或灾备证明。

## 入口与身份

- 管理SSH：`ub@192.168.19.30`，沿用受信220 host key、管理端原私钥。primary30默认出站源保持；31不是另一台机器。
- Nexus：`http://192.168.19.31:8081/`，原账号/权限/EULA保持，密码不修改，不写本文或命令行。
- 服务导航：`http://192.168.19.30:9080/`，匿名只读，目标各自认证；导航不执行部署或健康监测。
- Puyu发布MCP：`127.0.0.1:18765`，仅服务器loopback，使用原私有YAML/APIkey。MCP仅dev，真实deploy关闭，prod覆盖拒绝。

31直接SSH将呈现220自己的host key。不要沿用dell-vm221 alias，不复制221 host key伪装或关闭StrictHostKeyChecking。

## 每次维护先只读核对

在已有受信SSH会话中执行：

```sh
ip -4 -br addr
ip route get 192.168.19.45
findmnt /srv/dell-build
findmnt /srv/nexus
systemctl is-active docker.service dell-nexus.service puyu-deploy-mcp.service dell-service-directory.service prometheus-node-exporter.service
curl --noproxy '*' --connect-timeout 4 --max-time 10 -fsS http://192.168.19.31:8081/service/rest/v1/status
```

构建卷UUID为16dc6067-56ef-4687-a314-edc6421f9ed4；Nexus卷为239dc45a-b1f3-408b-a8ef-7afa77b52204，各100GiB。卷缺失时停止相关写入，不能将根盘底目录当挂载继续用。Nexus数据/srv/nexus/data，原数据库/blob必须一同保持；不format、不按sd字母猜盘、不递归改所有权。

查看异常仅截取非秘密状态；Compose/env/config.local.yaml、secrets与密钥不能cat进日志或聊天。管理员按原guard/manage流程检查Nexus，不能绕过UUID/身份门禁直接compose up或fresh-init。

## 正常启停

维护前先排空真实构建队列、制品上传/下载和客户端写入。只在需要的服务范围内操作。重启Nexus使用现役`dell-nexus.service`；原监督单元负责依赖、挂载与身份校验，不手工启动第二栈。不因Nexus维护重启导航/MCP或更换APIkey。

整VM220停机会同时影响导航、构建工具、MCP与Nexus，需排空后正常关机。旧221不再纳启动顺序，禁止启动旧31所有者。PVE整机启动未由本次迁移重新演练，不能拿unit就绪当物理启动全流程验证。

deploy-public更新走已审查Git提交的clean快进，保留ignored私有YAML和数据盘目录。CLI prod/main、dev/dev；六业务仓库仍main且无远程dev，dev预检拒绝是预期，不能fallback main或自动代建分支。prod SSH目标未配置、发布关闭、旧forced-chainfenced；本次没有业务构建或Java上线许可。

## 监控与验收

Prometheus只保留220的19.30:9100一个node，Nexus健康HTTP访问本机alias19.31，MCP仅unit检查。220 SSH/QGA/exporter/导航原4项加Docker/Nexus/MCP共7项；退221后10node+5Ops=15targets（包含资源280）。不能删除资源280或把31重复计算为新node。规则/Lark接收方和秘密保持，不发送人工告警测试。

内容验证使用本次源受保护全量基线12repos/7hosted/50components/1347assets和完整资产SHA比较，不能只看健康200。账号/权限、匿名拒绝、原镜像ID、凭据保持、唯一卷与双IP、私有配置/MCP guard、Java停用均须逐项留证。8项本地监控候选测试不等于现场采集器和15UP验收。

## 故障与备份

发现Nexus数据库/blob/身份/镜像或卷异常，停止写入并保留journal。禁止重跑stage/mount/commit/start来覆盖部分安装，禁止删初始化marker、重置密码或重建空库。管理员先核当前安装manifest与generated mount，再决定受控修复。

本次曾出现systemd单独验证unit找不到generated srv-nexus.mount：在13项目标SHA均匹配后daemon-reload，并把真实/run/systemd/generator/srv-nexus.mount与unit共同交给systemd-analyze verify。该经验不能简化为关闭验证或伪造mount单元。

迁移冷备仅PVE受保护目录，原档2,400,054,202字节且SHA/zstd/VMA已验证；不下载Mac，不自动删除。221退役后的恢复应在独立受控地址/隔离网络按真实备份重新评估，不盲反向move给已不存在VM。回退步骤未执行，未签恢复/RPO/RTO/独立DR。

自动备份继续只正式MySQL/Nacos，Nexus不新增自动任务。发布私钥只留220，绝不wholebackup/snapshot220或导出key。CF备份仍只PVE。归档旧221机器文档只留历史，不能作为现役部署入口。

最终退役回执确认：VM221配置与原OS盘已删除，活Nexus数据盘在220保持；原221恢复点为仅PVE保留的2,400,054,202字节冷备，不再声称保留源OS盘。见[退役回执](retirement-result.json)。

## 独立仓库写入验收

在现有专用dell-acceptance库，仅创建本次随机坐标的微小POM并读回原字节，随后精确核对repository/GAV/资产路径后删除该组件，原组件及资产集合恢复。未对业务仓库上传或删除，也不是Java构建/业务发布。立即search查询存在异步可见性，清理改用有界components列表；资产API的前导斜线按现有规范归一化后仍严格校验路径，未绕过身份门禁。详见[写入与清理回执](baseline-write-canary.json)和[原资产集合核验](baseline-canary-cleanup.json)；本次intent/journal只在220受保护路径，禁止重跑脚本再上传。
