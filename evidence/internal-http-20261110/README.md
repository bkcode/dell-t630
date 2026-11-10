# 自建内网应用使用HTTP

用户明确内部服务无需HTTPS。本期将两项自建内网应用统一HTTP，保原账号/权限及访问来源；PVE与iDRAC系统自带管理HTTPS本轮不改，外部Cloudflare边缘也不在此内部应用变更范围。

| 应用 | 当前入口 | 登录 |
| --- | --- | --- |
| 服务导航（发布机220） | **http://192.168.19.30:9080/** | 免登录、仅预览跳转 |
| FileBrowser（资源机280） | **http://192.168.19.80:8080/** | 原resources/admin账号不变 |

Penpot、Nacos、Grafana、Nexus、OMV、Jellyfin等此前已经是HTTP，本期不另重启/改程序。导航仍无顶栏、全宽紧凑，14条入口；只将FileBrowser链接改HTTP，当前导航本地source提交d56cae553bf95ce0e2c3fe8f258a2f99389aae7c，未代push原4条用户提交。

## 实际证据

- [源码独立审阅](source-review.md)：HTTP renderer只改配置/launcher/app unit三产物，三个防火墙产物不变；40项离线回归通过。固定旧/新摘要、写前CAS和有界恢复已审。
- [FileBrowser应用回执](filebrowser-applied.json)：同8080改HTTP，原两账号密码fresh登录与scopes/permissions保持、匿名文件401/日常管理员设置403，JWT/marker/UID/GID/state/NFS不变，只重启新app、不读写已有资源文件。
- [HTTP真实浏览器登录](filebrowser-browser.json)：resources用原口令进入资源页；临时登录记录/Cookie/本地存储/测试会话已清，不输出秘密。
- [导航链接同步](navigation-links-applied.json)：新不可变source提交5文件发布，FileBrowser链接HTTP，14入口和全宽无顶栏保持，原发布机服务身份不变。
- [最终只读后检](final-postcheck.json)：两应用HTTP健康正常，FileBrowser仍认证、JWT保留、初始口令不注入、TLSkey未加载、NFSactive，导航正确保留PVE/iDRAC原生HTTPS地址；16targets/资源6服务/HTTP健康指标全UP。

原TLS证书与旧回执仅作为未使用的历史材料保留，不再由两个自建应用加载；系统全局信任没有变化，不批量删除唯一回退材料。HTTP切换不等于关闭认证、统一密码或开启SSO，导航也不会绕过目标服务自身登录。

当前操作手册：[导航](../service-directory-20261110/usage-manual.md)、[FileBrowser](../../completion/20261110-filebrowser/usage-manual.md)。旧HTTPS证据按原时点解释，不能据其回滚当前HTTP。源码变更不自动发布到GitHub，deploy管理机已有4条用户未推送提交保持，本任务4条导航提交均只本地；Dell运维文档另行经扫描交付。

最新导航画面：[1920桌面](navigation-desktop.png)、[390手机](navigation-mobile.png)，记录HTTP入口及已同步的FileBrowser链接，保留无顶栏/全宽布局。
