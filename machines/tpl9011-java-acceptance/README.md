# 9011 · tpl-java-acceptance

这是保留模板的配置与文档目录，**不是运行服务器**。最后02:35综合盘点确认模板存在且停止；当前T630因UEFI0058暂停，本次没有连接服务器或新建clone。

| 项目 | 最后登记配置 |
| --- | --- |
| VMID / 名称 | 9011 / `tpl-java-acceptance` |
| 基础资源 | 2vCPU / 2GiB；来自PVE历史盘点，停止模板不计持续运行资源 |
| 系统 | Debian13 AMD64 |
| 网络 | vmbr19，通用Cloud-Init DHCP；模板无服务IP |
| SSH与Shell | clone用ub与批准公钥，fish4.0.2-1已装，默认Bash |

JDK21.0.13、非root java、通用验收脚本；不含业务JAR、Nacos/数据库配置或发布秘密，exporter默认masked。

## 文件

- [config.json](config.json)：模板配置合同和来源，不保存实际密钥。
- [config-sources.json](config-sources.json)：当前合同与历史验收来源，`path`相对仓库根目录。

首次clone必须分配唯一VMID、hostname、MAC/IP及ACL，确认新machine-id和SSH host key；不能复用旧QA身份，也不能在现役VM执行clean脚本。模板有归档回退点，归档不在Git。

操作前读[模板说明](../../03-templates-and-access.md)、[人工手册](../../19-manual-operations.md)、[当前暂停交接](../../11-live-handoff.md)。本目录不是可一键重新部署的安装包。
