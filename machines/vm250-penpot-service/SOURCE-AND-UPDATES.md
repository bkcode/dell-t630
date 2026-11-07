# Penpot源码与更新：bkcode/penpot · main

更新：2026-11-07。用户明确指定**使用`bkcode/penpot`仓库的`main`分支**。本页补充VM250的源码、版本和后续更新合同；当前服务器因UEFI0058内存错误暂停，本轮不取码、不构建、不部署。PAT保存/自动认证问题按用户要求留待以后处理。

## 1. 固定的项目来源

| 项目 | 约定 |
| --- | --- |
| 仓库 | [bkcode/penpot](https://github.com/bkcode/penpot) |
| 分支 | **main**，由用户明确指定 |
| HTTPS | `https://github.com/bkcode/penpot.git` |
| SSH | `git@github.com:bkcode/penpot.git` |
| 取码权限 | 服务器只读，不推送代码 |
| 来宾源码目录 | `/opt/dell/penpot/source`，部署适配目录与源码分开 |
| 运行实例 | VM250 `penpot-service`，19.50，入口9001 |

不会把官方`penpot/penpot`仓库当作本机改造版的直接部署源。仓库默认分支可能变化，取码必须显式指定`main`，不能省略分支后跟随默认分支，也不切到`develop`。

## 2. 最后已验收版本与未来main

最后部署验收使用`main`上的提交：

```text
ff1783e7865af7aae571c985f03e057631b7af63
```

该版本保留了改造前端、登录辅助及Worker/Import/MCP配套。历史采集时，本机源码比当时`origin/main`的`9aedbb0…`多两个已提交改造，并通过受控Git bundle移交；这解释旧证据，不代表当前远端main仍处于该位置。

后续更新从`bkcode/penpot`的`main`直接取码，部署前记录选定的完整commit SHA，并确认包含需要保留的改造。若改造只存在于Mac本地提交、尚未进入远端main，先停在版本核对，不用远端旧代码覆盖它，也不擅自向Penpot仓库推送代码。当前远端main最新提交尚未在本轮查询。

历史证据：[源码事实](../../infra/penpot/git-source-facts.json)、[运行来源](../../infra/penpot/application/git-runtime-provenance.json)。机器可读合同见[git-source.json](git-source.json)。

## 3. 取码示例与凭据边界

以下仅为将来硬件稳定且明确恢复任务后的示例，**现在不执行**。使用HTTPS的新独立目录应显式指定分支：

```sh
git -c credential.helper= clone --branch main --single-branch   https://github.com/bkcode/penpot.git penpot-main-review
```

如后续选择SSH只读Deploy Key，则使用同样显式分支的SSH URL；密钥选择、可信host key和凭据保存另行配置。示例不携带Token，不把密码、SSH私钥或.env放到源码、URL、命令参数或Git中。已经存在的生产源码目录不执行这条clone命令，也不直接pull/reset/clean。

取到main并不自动获得部署许可。已存在源码先检查origin、分支、工作区和当前commit；若有未归档改动、缺失历史改造或不可解释的版本差异，停止更新并处理版本归属。

## 4. 更新流程与可观察检查点

1. **恢复前置**：用户完成硬件处理并明确恢复后，先核内存、RAID/文件系统、VM250数据盘UUID和原服务状态，保留当前镜像、配置、身份及应用一致性回退点。
2. **源码选择**：只从`bkcode/penpot`取main；审阅与已验收版本的差异，锁定可从`origin/main`取得的完整commit。不要修改预期SHA以掩盖缺失改造。
3. **构建与兼容**：T630使用AMD64，按实际改造的构建上下文及锁定依赖构建，保留前端/Worker/Import改造。当前后端及数据库有独立版本合同，不能因源码中出现较新版本就顺带升级数据库、依赖或数据库schema。
4. **受控切换**：原11服务由`dell-penpot.service`的notify监督与数据盘挂载门禁管理。仅按审核差异更新程序及适配配置，不重跑fresh-init、不删除volume、不复制旧身份，也不执行PG整库覆盖。
5. **验收与记录**：核main选定commit与镜像/构建产物来源、11服务健康、19.50:9001、登录、原设计和素材、Worker/Import/MCP及查询日志不泄露凭据；检查原owner/worker身份与挂载UUID保持。真实设计写入或破坏性负测另定专用对象，不能把只读更新验收扩大到原设计修改。
6. **失败处理**：保留新证据与真实新增数据；回退程序版本不等于回退数据库。涉及schema/data变更时须另有兼容和应用一致性恢复方案，不能只换Git分支。

## 5. 数据与文档分工

Git负责源码；设计文件、PostgreSQL、素材、账号/MCP身份和部署秘密分别保管，不能靠git pull恢复。已有3设计/原971媒体保护与最后973总资产是历史验收基线，恢复后重新核实，不删除合法新增内容凑数量。

本机资源/网络/数据盘见[config.json](config.json)，服务维护见[README](README.md)、[人工手册](../../19-manual-operations.md)，源码与验收来源见[config-sources.json](config-sources.json)。本轮只更新文档与配置元数据，既不更新运行程序，也不处理PAT缓存或服务器认证。
