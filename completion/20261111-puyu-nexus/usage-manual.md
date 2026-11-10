# Puyu制品仓库与配置适配器操作说明

更新：2026-11-11，Asia/Shanghai。今天仅空仓库、权限和发布工具配置对接；真实构建/发布不在本次范围。适配器源码已提交推送main/2d8f541，Mac75项回归及固定/bin/bash专项10项通过；发布机已同步同SHA、Linux75项回归通过；[配置连接后检](connected-postcheck.json)已通过，仍不代表真实业务构建已就绪。

## 入口与选用

NexusUI：http://192.168.19.31:8081/，管理SSH仍ub@192.168.19.30/220自身host key。31是同一机器服务alias，不是新VM。

- 读取：http://192.168.19.31:8081/repository/puyu-public/。
- Release发布：http://192.168.19.31:8081/repository/puyu-releases/，仅RELEASE，ALLOW_ONCE，重复路径拒绝。
- Snapshot发布：http://192.168.19.31:8081/repository/puyu-snapshots/，仅SNAPSHOT，ALLOW。

puyu-public只聚合这两个Puyu仓库，不含旧区或Maven Central proxy。项目原有公共仓库配置继续工作，不改业务仓库settings，也不开放Nexus内部容器网络出口。原Finger/imnull制品保留，不能导入/删除来填充Puyu空库。

普通读取用puyu-reader；只有未来明确批准发布时使用puyu-publisher。后者对两个新hosted有add/edit、没有delete/admin或旧区权限，不应冒充管理员。权限回执确认reader写403、publisher删403、release重复400，专属fixture已清，当前0组件0资产。

## 凭据与统一YAML

两个新口令最初由VM220本机生成，受保护来源为/root/dell-nexus-secrets/puyu-reader-password及puyu-publisher-password，root600；现已接入发布机/opt/deploy-public/config.local.yaml（ub600、Git ignored）。真实值、私有摘要、APIkey不写文档/Git/聊天或命令行；不要cat整个YAML、使用set -x或把完整环境dump到日志。

artifacts是统一YAML的可选节，保存base URL、group/release/snapshot名称和两组受限身份。维护只修改该节，保留原MCPkey/settings/targets/路径、CLI prod/main与dev/dev，不重新bootstrap、不生成新APIkey、不覆盖私有文件。具体字段名以同版本deploy-public公开example及[源码操作说明](https://github.com/bkcode/deploy-public/blob/main/docs/OPERATIONS.md)为准；服务器已应用2d8f541，不抄其它未锁定版本进行发布。

公开字段形状如下，两个null仅是占位，不能覆盖服务器已有密码；配置保持同一份YAML：

```yaml
artifacts:
  base_url: http://192.168.19.31:8081
  read_repository: puyu-public
  publish_repositories:
    dev: puyu-snapshots
    prod: puyu-releases
  credentials:
    reader:
      username: puyu-reader
      password: null
    publisher:
      username: puyu-publisher
      password: null
```

不创建另一份runtime.env或包含凭据的业务environments.env。`base_url`只取HTTP(S) origin，不包含认证、路径、query或fragment；执行时所选reader/publisher身份须完整。

## 配置检查与显式执行入口

适配器设计只调用固定的既有build.bash，不接受任意可执行文件或脚本路径；通过可选artifacts将NEXUS_URL、NEXUS_PUBLISH_URL、NEXUS_USERNAME和NEXUS_PASSWORD注入子进程。口令不出现在CLI参数，不因读取配置自动连接网络、构建或发布。

服务器已同步同一提交，日常只读配置检查使用：

```sh
cd /opt/deploy-public
.venv/bin/python artifact_exec.py show
.venv/bin/python artifact_exec.py check
```

show/check只报告配置完整性、公开URL与凭据是否存在，不展示口令，也不证明网络/权限/依赖/实际构建通过。最终实现CLI语法以锁定版本帮助为准。今天不执行exec/build/publish；后续显式执行必须先获得对应业务构建/发布范围授权，并确认版本、分支和依赖准备，不能将配置测试当发布许可。

publisher访问模式必须显式选择，dev→puyu-snapshots、prod→puyu-releases；读取统一puyu-public。reader不应获得发布权限。已有业务版本1.0.0/0.0.1不是快照，选择dev不会自动改版本，SNAPSHOT仓库会拒绝release版本。不要用放宽版本策略、重新发布覆盖或借管理员权限追过。

MCP不自动接入这个wrapper：仍dev-only、真实deploy disabled，原forced-chainfenced。prod SSH目标仍未配置。配置适配器不是绕过MCP、业务分支或发布链门禁的办法。[本次实际后检](connected-postcheck.json)已确认协议可用、匿名401/Origin403且没有新任务。

## 依赖缺项与排障

新group为空，私有gradle-conventions与puyu-common-lib尚无批准供应。缺插件/依赖时先记录所需坐标/版本和批准来源，安排后续供应，不复制旧区、不改Go/Java、不凭空创建dev或改版本。现有公共Maven仓库/插件门户/JitPack直接访问保持；Nexus连不上外网不是本次要改网络的依据。

- 401/403：检查使用reader/publisher哪一身份及目标是否新Puyu区；不修改旧管理员密码或给宽泛权限。
- 发布400：先区分release重复部署与版本不符，不删除旧文件凑成功。
- show/check配置不完整：检查统一YAML节结构与600/owner，避免打印含秘密的解析错误原文；不重生成MCPkey。
- 构建失败：本次未实际构建，不能归因为已验业务故障；先核dev分支、私有插件/公共库供应和版本策略。

## 修改、清理与备份

仓库/角色创建器和fixture验证脚本是本次事务记录，禁止反复运行来重建同名对象或清空仓库。已有旧库/用户/权限/EULA/密码保持，Nexus本次未重启。后续出现真实产物后，清理由单独授权的精确对象决定，不能套“空服务”全清。

本次不增加自动备份。自动备份仍只正式MySQL/Nacos，Nexus/Puyu库与220整机不纳入；发布私钥只220、CF档只PVE。不得为了保存新密码导出220整机或复制原发布key。独立DR/RPO/RTO和真实构建/业务上线均未签。

## 本次完成的证据与未签部分

[发布机应用](publisher-applied.json)锁定main/2d8f541，Linux75项通过，原YAML全部先前值和MCPkey保持、ub600/ignored，Nexus/导航PID保持。真实固定build.bash只执行ls列项目；未编译/发布业务。

[连接后检](connected-postcheck.json)直接使用服务器私有YAML两组新身份，读取不存在资源得到预期404，证明身份通过认证而空库无该资源；不是授权失败或真实资产可读证明。权限内容证明另见[fixture验收](permissions-result.json)，测试数据已清。现有Nexus旧区/身份不变、六main源码保持、无业务启动。后续私有插件/公共库供应、dev分支和SNAPSHOT版本准备仍须单独处理。

## 工具版本回退的配置配对

旧213f及更早loader不认识artifacts字段。将来若需回退，须在无任务且MCP停止的窗口审查服务器本机config.local.yaml.before-puyu-artifacts-20261111（ub600）与对应旧代码，配对恢复私有YAML后再启动并验收；不能在带新字段的配置上直接启动旧版本。不重建仓库、旋转密码或导出该备份；Nexus的现有仓库和账号保持。此处只记录人工维护要求，本次没有执行回退。
