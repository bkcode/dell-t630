# 每机Git来源独立审阅

审阅时间：2026-11-10T13:22:57.693138+08:00，Asia/Shanghai。结论：**仓库归属合同通过，无阻断项**。这是本地合同与已有带时间证据的审查，不是部署或服务器拉取能力验收。

17台记录与plan一致：1宿主、13运行来宾和3停止模板；机器目录、配置目录及repository引用均存在。27条仓库记录分为1个Dell配置仓库、8个用户应用或构建输入仓库、18个上游参考，不代表27套已部署业务。

- 全部机器的公开基础设施来源为bkcode/dell-t630；组件官方上游只是参考，不把数据库、Nacos配置正文或身份数据登记成Git业务库。
- 220的deploy＋五个后端是后续构建来源；没有声称已在220 clone、配置新key或适配Puyu。common-lib仅共享库。230/240只接收将来审定制品，不要求放Deploy Key或直接拉源码；当前Java业务仍关闭。
- Penpot管理Mac通过定向key读取main并临时checkout 9aedbb011cd803eb615225ca21f7f47cb8c2fa09；服务器现役仍为main/ff1783e7865af7aae571c985f03e057631b7af63、clean、无origin，11服务healthy。监督器NRestarts=22是累计值，未冒称零重启。取码结果不授权用远端旧main覆盖现有改造，也不证明服务器已有GitHub拉取配置。
- NAS现役是官方Jellyfin镜像；bkcode/jellyfin仅服务端fork候选，默认master的观察不是部署选版，电视客户端也不是此server仓库。Nexus、Ops、FileBrowser与各模板未虚构独立用户业务库。
- 仅对管理Mac八对key执行lstat：private600、public644，均regular、非symlink且当前用户所有；没有读取private/public key正文。这不验证pair匹配、GitHub只读开关或服务器安装，合同中的read-only为权限政策。

本审阅只写review.json/md，未连接服务器、运行Git取码、安装key、部署、迁移数据或改SSO。17份逐机GIT-REPOSITORIES.md、README入口、config映射、JSON pointer及repository IDs已逐一独立核对；机器总览及索引链接均存在。最终结论仅签文档与有限管理Mac读取证据，不签部署或其余key读取。

最终增量审查：冻结validator SHA256 `6738545de49c9a1d868e3d59dffc557052ba6147542485ce0efc2a2023c7b1ef`，原始与public-only隔离副本均通过。12项隔离负例全部拒绝，涵盖旧7项、template单独pull=true、config错误JSON pointer/document path/usage mode/source role。此前两个非阻断建议现已关闭；本次仍只签文档与已有Penpot管理Mac有限读取证据，不签服务器拉取/新部署或其余7个key读取。无SSH、密钥读取或Git操作。
