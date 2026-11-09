# FileBrowser API与NFS独立原生验收

状态：**passed**。API/NFS验收、主AI独立浏览器预览和本次fixture最终清理均已完成。

验收时间：2026-11-09T21:57:00.342895+00:00 至 2026-11-09T21:57:48.714642+00:00，UTC。最终清理及保护状态读回时间：2026-11-09T22:05:57.491564+00:00。目标仅VM280、230和240；strict SSH使用既有可信hostkey，HTTPS使用VM280本机公开证书验证链与IP，未关闭TLS校验。登录凭据和JWT仅在VM280进程内存中使用，未导出。

- 日常operator在专属目录创建、上传有效96×96 PNG和文本。目录实测UID2000/GID2980/mode2770；API文件均为2000:2980/mode660。
- 两台客户端分别以现有finger999:989＋附属组2980读取PNG原样、顺序追加独立文本。230创建新文件由240读取，API随后下载PNG、追加文本及NFS新文件，均与合成预期字节完全一致。NFS新文件为999:2980/mode660；没有修改原资源目录权限或ACL。
- operator删除、带override覆盖、PUT编辑、分享、提升用户权限均返回403；匿名资源请求返回401。之后原样本与operator权限保持不变。
- 前后记录显示NFS、FileBrowser、防护unit、SSH、网络及exporter身份不变，挂载metadata一致。客户端mount/automount与原/mnt/dell-artifacts挂载状态保持，两台Java进程数均0；没有重启服务或机器。

浏览器预览样本：source `resources`，路径 `/__fb_qa_41c99127351245a68262ef891453e0db/fixture.png`。主AI已完成独立浏览器登录、四文件列表及PNG渲染，见browser-acceptance.json。其明确释放后，仅以finger核对owner.marker及精确四文件集合，逐一unlink后rmdir；未递归删除。VM280、230、240均读回本nonce不存在。

首次尝试在230尚未切换finger时以root读取660标记文件，触发PermissionError。原failed回执独立保留于native-first-attempt.json/md；仅将runner改为先切finger再读同一标记，后续通过。不能把首次错误说成finger权限故障或修改首次状态。

限制：这是合成样本的API/组共享与权限负例，不代表真实业务上传集成、所有历史文件内容、业务静态图片公开入口、备份恢复或独立灾备。未启动Java、未改Nacos应用配置、未改PVE或客户端服务、未发送通知。最终保护状态与最初基线一致，两客户端Java仍为0，未新增测试或服务操作。

最终清理：4个合成文件＋1个空nonce目录，fixture_cleaned=true；三guest最终服务PID/启动时间、挂载metadata及客户端artifact挂载/units均与起始记录一致。
