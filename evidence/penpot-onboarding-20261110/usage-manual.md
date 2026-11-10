# Penpot关闭首次登录引导：使用与维护

2026-11-10，Asia/Shanghai。**已部署验收通过**。源仓库bkcode/penpot main/`8a9b96154d9dd81dcc373155ae30dba094127cc8`，VM250当前Git clean，自建frontend image `sha256:6cbd1f7f3b90b77b3dcd4f6a65fa9c117861d2de0781df22bd8bad40f19c61bc`，基础固定官方2.18.5、其他10镜像保持。

## 使用

打开[Penpot](http://192.168.19.50:9001/)，现有原表单账号密码默认填入方式不变，按原继续登录后直接进入项目列表。欢迎/调研/创建团队首次引导不再弹出。已有标签页请刷新，必要时强制刷新。`puyu`项目及三个页面保留。手动创建团队功能保留；原生disable-onboarding也会关闭自动版本说明弹窗。

这通过Git中的selfhost wrapper追加原生flags实现，不是修改个人profile假装答完调研；不新增表单或保存逻辑。真实新会话已确认dashboard、nativeflag true、onboarding节点0、欢迎/团队弹窗false、Puyu可见，无Internal Error；密码预填登录仍通过。测试cookies/localStorage清理、会话关闭，截图仅private。

## 部署事实与权限

用户在得知AGENTS禁止代理push及默认分支影响后明确回复“进行推送”，覆盖本次较早约定；原AGENTS文件没有削弱。先推ec6f，再推权限修正8a，均非force。服务器从公开HTTPS拉固定提交，不复制GitHub私钥或Token。只构建frontend/selfhost包装，不声称全库CLJS/后端编译或升级到2.19。原sidebar、loginhelper、查询安全日志和只读mount保持。

所有公开COPY明确0644，避免root umask077检出导致运行UID1001无法读取。v2还用原生Docker BuildKit构建派生只读检查层，实际以1001读取wrapper/JS/CSS/NGINXconf；不启动额外Docker工作负载容器，不触发现役全容器守卫。readcheck镜像不是运行镜像。

## 首轮失败与恢复

首次ec镜像因Git工作树0600、Docker COPY保留权限，启动脚本不可读，未成功上线。保护事务恢复旧ff源码/旧lock后，服务已触发StartLimitBurst3；主AI核旧合同再仅reset-failed此unit并start，原ff11healthy恢复实证存在。不是清日志、删除设计或关闭守卫。首次自动事务的专门rollback receipt缺失，实际恢复以old-service-restored及rate-limit-reset证明；失败输出和诊断保留，不能称首轮成功或无中断。

v2新事务`/root/dell-penpot-no-onboarding-20261110-v2`，对应worker同前缀.py；正常停止原监督器后同步真实source目录、Compose和lock，再沿原notify unit恢复。旧source目录`/opt/dell/penpot/source-before-onboarding-8a9b96154d9d`及旧image保留用于审核后回退。v2启动/回退路径保留reset-failed处理速率限制，仍先跑原生check。完整证据见[交付](README.md)。

## 后续更新

取新main必须固定commit、保留既有改造、候选构建及UID1001读检、审核真实镜像/资源/mount/publicSHA，再按受控窗口切换。`no-onboarding.py`为本次一次性事务，不能重放prepare/apply或手改lock绕过验证；失败先查journal、源目录和真实服务状态。禁止fresh-init、down-v、PG覆盖或重新生成密码。

当前只签私有文件与资产字节聚合、DB对象计数、Puyu页面/图形/组件统计保持，未重验所有设计像素/交互或整库灾备。WG来源ACL仍配置允许，当前新浏览器为LAN验收，未冒签本轮异地E2E。备份仍仅正式DB/Nacos，不扩Penpot或其它服务。
