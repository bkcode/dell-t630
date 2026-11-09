# 本机Nacos来源命名空间清单：等待用户选择

采集：2026-11-09T13:02:18.572737+00:00。只读来源`/Users/yangzhaohui/work/nacos`，实际Nacos容器running、host网络，入口`http://127.0.0.1:8848/nacos`，readiness与namespaceGET200。未猜密码、未尝试默认登录；本机loopback只读GET直接成功，此事实不等于所有接口/来源均不需认证。

用户要求先列真实来源namespace与数量再选择；当前没有选定任何来源，**未清理目标、未导入/发布任何配置**。

| 来源名称 | 真实namespace ID | 配置数 | group与数量 |
| --- | --- | ---: | --- |
| public | `(public空ID)` | 0 | 无 |
| finger-cloud-dev | `08e7191f-3ccd-411a-be00-56798d237533` | 32 | `DEFAULT_GROUP`: 32 |
| finger-trascan | `7bfe03c6-0590-4ff0-8def-e07015016b54` | 4 | `DEFAULT_GROUP`: 4 |
| broker-base-local-20260922 | `broker-base-local-20260922` | 1 | `DEFAULT_GROUP`: 1 |
| Broker OMVA Local 20260917 | `broker-omva-local-20260917` | 1 | `DEFAULT_GROUP`: 1 |
| puyu-local | `puyu-local` | 5 | `DEFAULT_GROUP`: 5 |

共6个namespace、43份配置，所有namespace分页list的count与实际列数一致。按最新范围普通证据只保留name/id/count/group counts；dataId逐项元数据与配置正文在来源选定后才作必要导入准备。配置list响应可能携带content，本次只在程序内解析，未输出正文、token、密码、composeEnv值或落配置内容文件。

Docker只读元数据确认Nacos镜像reference2.4.3/实际imageID、containerID、hostmode和公开mount。仅logs目录挂载，不把logs/未知Derby目录拷贝称配置导出或整库迁移。没有停/重启源容器、读取MySQL业务表、改源文件或目标服务。

目标最新意图为测试Nacos实例所有namespace内“配置项全部清理”，**不是删除namespace/账号/权限，也不改业务schema或正式Nacos201**；此处只记录范围，尚不执行。必须先有用户来源选择，再由root形成目标删除清单/私有可恢复导出/导入映射和明确窗口，不能自动把同名namespace、所有来源或public当选择。

本轮不启动Java、不动正式数据，不重置账号、不上传无关凭据，不做数据库整体迁移。来源现役容器和配置保持。机器元数据见[source-inventory.json](source-inventory.json)。
