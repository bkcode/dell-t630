# 发布机服务导航

用户明确仅需免登录预览与跳转。现采用独立Python标准库GET-only服务，来源bkcode/deploy/service-directory，地址清单为该项目services.json。当前部署状态以[evidence/service-directory-20261110](../../evidence/service-directory-20261110/)实际回执为准，未签收阶段不得称已上线。

目标入口https://192.168.19.30:9080/，只允许LAN21/24、WG10.66.66/24与本机。页面提供分组、搜索、环境筛选、复制地址和noopener打开链接；没有账号、密码、增删改接口、可写状态或目标健康探测。各目标服务自己的认证保持。

固定源码release仅含server.py、web3文件、services.json，来自已提交Git SHA，不打包原发布配置、MCP、Git私钥或凭据。专用UID/GID2001运行，系统只读，除systemd临时TLS私钥外无凭据；publiccert用于首次指纹核对。独立自有nft表只限制9080，不改路由/PVE或现有publisher/Java/Nexus/Penpot。

`install.py`为仅新VM220目录/账号/端口的首次安装器，已存在则拒绝，不能用于重复覆盖或升级。地址修改在源码JSON审核提交后，以新不可变release发布并重启新导航服务，保留旧release与证书；本期不启Java、不迁Nexus或Penpot、不扩自动备份。

原登录/CRUD草稿未部署，已按用户收窄从最终代码移除，不生成门户账号密码或数据库。初始14入口只是现有Web地址，不表示即时健康；非Web的MySQL/SSH/NFS地址不混作网页链接。
