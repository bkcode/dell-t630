# 逐机Git仓库文档与Penpot验证

本期用户要求每台机器明确Git来源，并先验证Penpot专属Deploy Key；已授权子AI协同。**只做文档与限定只读验证，未安装服务器Git私钥、改origin、拉取现役工作树、构建、部署或启动业务。**

入口：[Git来源总览](../../machines/GIT-REPOSITORIES.md)、[机器可读主表](../../machines/git-repositories.json)。PVE＋13来宾＋3模板共17份GIT-REPOSITORIES.md，README与config精确映射齐全。配置仓库是bkcode/dell-t630；8用户应用/构建输入与18组件上游参考分开，共27条定义，不是27套已部署业务。

[本期4项验收](acceptance.json)为独立文档验收，不替换现行FileBrowser8项运行验收。独立review覆盖17归属/指针/链接及隔离变体；sourceindexes只锁本地文件，不证明各来宾已clone/自动部署。

## Penpot实际结果

[管理Mac身份/临时clone](penpot-deploy-key-verification.json)：重命名penpot_ed25519 key读取成功，临时main单分支浅历史、完整工作区检出成功且已清，未转发agent或输出/复制私钥。远端main实际9aedbb0，本地及[现役VM250](penpot-runtime-readonly.json)为ff1783e，仍缺两条现役改造。先由用户补齐远端版本，再另行确认不可变提交与构建/更新，不能以读验证自动回退现役。

VM250 source clean/main、无remote；11容器running/healthy、frontendID匹配，容器RestartCount0。监督unit当前active、累计NRestarts22如实保留，不据此推断当前故障或宣称从未重启；本期未扩大诊断。没有核设计/素材内容，也不扩大签收数据一致性。

## 其他角色与密钥

220仅计划bkcode/deploy＋5Puyu后端；common-lib为库，部署工具是否适配Puyu/受限链未验。230/240只收审定制品、Java继续关闭，不直接拉源码或放key。260当前官方镜像，bkcode/jellyfin是服务端fork待接入，不是电视客户端；本轮未clone。基础组件按固定包/镜像，官方仓库只作上游参考。模板无业务源码/密钥。

8仓库密钥在管理Mac受控目录，用户报告GitHub已配置，本期只验证Penpot读取；不通过实际push探测write权限。server未由本任务分发密钥，读权限仍须按实际GitHub配置/后续每仓库验证；新deploy key和全局SSH配置不在本Git仓库。

```sh
python3 scripts/validate_git_repositories.py
python3 scripts/validate_machines.py
python3 scripts/validate_docs.py --json
```

## 用户确认的后续部署范围

用户进一步授权仅Penpot机Git取码与部署，其他服务器不做运行变更，逐机文档继续。用户选择保留ff1783e两条改造，先由用户推入bkcode/penpot main并通知后再继续；当前停在版本核对，不配置服务器私钥、不构建或切换现役。见[部署等待状态](penpot-deployment-state.json)。文档与管理Mac读取验证已完成，不将等待中的部署签为完成。
