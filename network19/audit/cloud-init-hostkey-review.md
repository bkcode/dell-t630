> 文档状态（2026-11-07）：本页为阶段实施/技术记录，文中“当前”、网段、角色数与通过结果以原执行时点为准。服务器现因UEFI0058内存错误暂停，Nexus合并已授权但未执行；当前配置入口见[访问清单](../../12-service-access-and-operations.md)，恢复门槛见[最新交接](../../11-live-handoff.md)。旧脚本、stage/commit或初始化步骤不得直接重跑。

# 已部署VM hostkey保留独立复核

结果：`hostkey-profile-independent-verification.json`为passed。PVE内旧profile与当前实际cicustom引用snippet在RAM逐字节比较，13/13只有`ssh_deletekeys: true`→`false`这一个字段值改变，其余bytes相同；当前refs正确、snippet及旧备份均root0600，没有嵌入`ssh_keys`。完整userdata/公钥内容没有返回或写入普通证据。

两核心模板的**实际引用snippet**9001/9010仍明确`ssh_deletekeys: true`。`qm cloudinit dump user`显示自动生成内容，并未展示对应自定义字段，因此本审计另读实际snippet布尔，不用generated dump误判custom配置。其它模板/真实数据未修改。

230原machine-id为`346f97d644174e89a3fe8dbe9fa7039f`，已在旧正常重启证据行207/726/784三处找到；当前QGA读回完全一致，同时hostname java-prod-01、原MAC bc:24:11:1c:20:00、新IP19.40/24均匹配。当前可信ed25519指纹为`SHA256:KeItAegZqF5lSTCA3fAzKUFYuLAbnG9Pt1AqWskXMlM`，原指纹仍留在旧证据，不覆盖它；本次rotation由主AI可信QGA链确认并留host-key-rotations ledger。本agent未改known_hosts/trust文件，也没关闭严格校验。

按cloud-init SSH模块语义，已部署实例false保留现存host keys，缺失key的生成与删除是两件事；模板初克隆仍须独立生成身份，不能为便利复制旧VM私钥。实际重复CI/重启是否保留仍以主AI当前canary读回为证，不能把静态字段配置当作所有13VM都已重启验收。[cloud-init官方SSH模块](https://docs.cloud-init.io/en/latest/reference/modules.html#ssh)
