# CLI双环境与dev-only MCP操作说明

2026-11-10，Asia/Shanghai。发布器在VM220 `/opt/deploy-public`，源码main/213f1f4 clean；MCP以ub运行，只监听127.0.0.1:18765。此处只记模式/分支准备，不是应用发布手册。

| 入口 | 业务分支 | 当前限制 |
| --- | --- | --- |
| CLI DEPLOY_ENV=dev | dev | 六个上游均缺dev，真实同步/预检应失败 |
| CLI DEPLOY_ENV=prod | main | 正式SSH目标未配置，不能发布 |
| MCP | 仅dev/dev分支 | 拒绝prod覆盖，deploy-services关闭 |

发布器自身仍从deploy-public/main取源码，与业务DEPLOY_ENV独立。

## 只读查看

```sh
cd /opt/deploy-public
.venv/bin/python config_loader.py validate --mcp
bash deploy-select.bash --list --json
DEPLOY_ENV=dev bash deploy.bash targets puyu-auth
DEPLOY_ENV=prod bash deploy.bash targets puyu-auth  # 正式身份为空时预期拒绝
```

source_ready仅表示受管理Git目录存在；expected_branch是配置要求，current_branch是实际检出分支，target_branch_available仅本地origin跟踪引用。列表不联网fetch，不能仅凭本地无引用断言上游不存在。本轮另有独立ls-remote审计证实六仓库main存在/dev缺失；当前工作树仍main/clean，未切换或创建业务分支。

## 新预检的真实结果

MCP initialize/list_jobs/list_services正常，认证规则保留；实际validate-services任务3294416b9b754af5879ce96fd1c4a79e为failed，原因origin/dev not prepared，发生在构建/SSH前。此失败是正确阻止未就绪分支，不能与之前dev/main阶段的成功混为一谈。prod参数覆盖和真实发布任务也在执行前拒绝。

本轮修改的私有配置仅为环境映射与新增空prod目标，原MCPkey、私有路径和测试目标保持。不要cat私有YAML、输出key或用旧样例覆盖实例配置。修改YAML后需要在无任务时重启MCP，项目发现与新任务才使用新配置；既有任务保留原快照。

## 后续准备分支

业务维护者应先明确准备所需dev分支。本轮没有代建或push分支。只有远端所选分支存在、身份/目标已核对且有相应操作授权后，才显式同步：

```sh
DEPLOY_ENV=dev bash sync.bash get puyu-auth    # 会联网并可能切工作树，当前缺dev时失败
DEPLOY_ENV=prod bash sync.bash get puyu-auth  # 取main，不代表正式目标已配置
```

同步入口显式获取配置的refs/heads分支，兼容初始single-branch main clone，不静默回退main。--validate和真实流程首轮预检则只检查本地引用，不自动fetch。旧dev/main产物元数据不能手改复用为dev/dev，后续构建与运行机权限/旧受限链Puyu适配须单独验收。当前旧链仍fenced、Java不启，真实发布开关保持false。

源码库的[完整操作说明](https://github.com/bkcode/deploy-public/blob/main/docs/OPERATIONS.md)与[发布机安装说明](https://github.com/bkcode/deploy-public/blob/main/docs/PUBLISHER.md)补充安装/更新步骤。受控一次性实例更新脚本set/apply/probe/collect-standard-modes保留为本轮证据，不能盲重跑或据其操作其它实例。
