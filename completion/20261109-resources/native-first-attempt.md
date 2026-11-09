# 首次资源fixture尝试（保留failed）

230新nonce目录/marker创建成功后，在后续权限metadata断言处停止；未进入跨机读写、root_squash或240停挂载负测。该runner使用umask0022却要求groupwrite，疑与已定义业务UMask0002不同；首轮未捕获失败前具体文件mode，所以不把该推断当已证实权限根因。

所有自有fixture按createdflag已清理；三节点最终guard成功、既有service身份不变、Java0、240artifact挂载状态不变。没有chmod绕过。完整原始失败与步骤见[native-first-attempt.json](native-first-attempt.json)，后续以新nonce、实际契约umask0002重新验证，不覆盖本记录。
