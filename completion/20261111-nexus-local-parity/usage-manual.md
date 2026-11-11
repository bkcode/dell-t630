# Nexus本机配置对齐操作说明

更新：2026-11-11，Asia/Shanghai。当前方案只对齐配置，保留服务器全部额外库和数据。服务器配置、发布机YAML及实际YAML读取后检已验证通过；本文不是删除或批量重建入口。

## 地址与映射

Nexus保持http://192.168.19.31:8081/，服务器管理SSH用19.30/220自身host key。当前统一YAML使用：

```yaml
artifacts:
  base_url: http://192.168.19.31:8081
  read_repository: maven-public
  publish_repositories:
    dev: imnull-snapshots
    prod: imnull-releases
```

仅合并上述公开映射到/opt/deploy-public/config.local.yaml，保留其credentials节原puyu-reader/puyu-publisher口令以及原MCP/APIkey、paths、targets、环境和Git身份；不要用示例覆盖私有文件。真实值只在服务器600受保护来源和ub600/ignored YAML，不打印、写命令行或进Git。

读取：http://192.168.19.31:8081/repository/maven-public/；dev写imnull-snapshots，prod写imnull-releases。group成员有顺序：imnull-snapshots → imnull-releases → maven-releases → maven-snapshots → maven-central；同坐标多仓库时优先来源受顺序影响，不按字母重排。

## 仓库策略与保留清单

- imnull-releases是RELEASE/ALLOW，按本机约定允许覆盖既有路径；本轮只改配置，不实际覆盖或删除制品，后续覆盖必须有明确发布范围。
- 默认maven-releases仍RELEASE/ALLOW_ONCE；不能把imnull策略套到默认仓库。
- imnull-snapshots新增SNAPSHOT/ALLOW，不复制旧库内容。
- Puyu3、Finger3、dell-acceptance共7库全部保留，额外库不是待删除清单。服务器15库加1后共16库，本机9只是配置参考，不是数量目标。
- 原50components/1347assets的ID和校验元数据需要保持，NuGet与默认Maven数据也不迁、不清。

旧reviewed-target.json的remove_extra_repositories是审批前历史；approval-status.json已记录用户明确安全选择，当前以approved-safe-target.json保留方案为准。禁止重放带删除旧候选，禁止按通配符或“多余”标签删库/组件/文件。

## 身份与权限

沿用puyu-reader/puyu-publisher原密码。reader在新标准6个Maven仓库追加browse/read；publisher保留这些读取并对imnull-releases/imnull-snapshots追加add/edit。原Puyu3读取/发布权限保留；无delete/admin，不扩大其他角色，不重置管理员。权限追加不等于允许立即业务构建/发布。

## 配置检查与实际读取

服务器已同步main/bba3542并完成私有YAML合并，可执行离线检查：

```sh
cd /opt/deploy-public
.venv/bin/python artifact_exec.py show
.venv/bin/python artifact_exec.py check
```

show/check不输出密码、network_checked=false；只证明配置完整性，不证明服务器内容/代理可用。实际读取应在受保护服务器会话中使用已存在的imnull资产，经新group读取比较原ID/大小/校验元数据，不将口令放curl参数或终端。新group包含central但Nexus隔离网络不放开，不主动请求未缓存公网坐标，本次不签远端proxy cache-miss下载。

只显式CLI适配器向原固定build.bash注入NEXUS_*环境，工具实现不改、不自动接MCP。MCP仍dev-only、真实deploy关闭，旧forced-chainfenced。今天不运行build/publish、Go/Java或创建/切换dev分支。现有release版本不是SNAPSHOT，仓库配置对齐也不会改版本；业务构建前置与后续供应需另验。

## 验收与故障处理

配置读回应核9个本机参考库的目标字段，额外7库配置/数据保持，总16库；group顺序精确、imnull ALLOW与默认maven ALLOW_ONCE分别正确。对原资产比较ID及校验元数据；实际已有资产读取正常，新账号不能删除/管理，旧角色/密码不变。服务器源码/私有YAML应用、MCP认证与无新job、原服务/挂载/源码保持均需独立回执，不以Mac75项测试代签。

401/403时先区分身份和目标权限，不给admin追过；404可能是空库缺资源，不能一律当网络失败。重复发布行为按具体仓库策略判断，不通过删旧文件凑过。任何额外库或旧资产消失，立即停止写入、保留日志与原生回执，不用重新迁入/重建掩盖差异。

无需回滚或重建旧221；Nexus保持现役220。自动备份仍只正式MySQL/Nacos，本次不纳Nexus或220整机，不输出/复制原发布私钥。源码提交、服务器应用与最终验收以[本次记录](README.md)为准；只有明确回执齐全后才称配置对齐完成，仍不等同业务发布成功。

## 已应用回执

[服务器配置](configuration-applied.json)确认16库，额外7库、原50components/1347assets的ID/路径/checksum均保持，DELETE调用0；其他角色/原密码与Nexus/导航PID不变。

[发布机应用](publisher-applied.json)确认main/bba3542、Linux75项37.158秒通过，YAML只改read/dev/prod三个库名，ub600/ignored、原口令/MCPkey/所有其他设置保持；show/check与固定build.bash ls通过，MCP仍loopback/dev-only/真实deploy关。[实际连接后检](connected-postcheck.json)已通过：两组私有YAML身份经maven-public读取现有imnull对象均200/字节一致，9参考定义语义对齐、16库及原50/1347保持；没有新写制品或测试proxy cache miss。

本次9库参考定义比较只规范化proxy API附加的空authentication字段，实际认证必须仍未配置；不是将HTTPclient差异全部忽略。MCP协议已验，匿名401/Origin403，仍dev-only/真实deploy关且没有新job。配置对齐完成不等于真实构建/上线成功，Nexus公共proxy缓存未命中的下载能力未签。
