# Nexus合并：管理恢复后的最小resume清单

更新：2026-11-07。**用户“授权短时停机合并”的知情维护许可已满足**，见maintenance-authorized.json及AGENTS最新追加；旧approval-block.json保留历史，不能再把同一许可写成pending。当前用户已暂停硬件处理与Nexus合并，转做文档Git交付；DIMM_B1/UEFI0058问题尚未签为修复，迁移尚未开始。下文仅是将来明确恢复执行后的人工复核清单，不授予当前远程、停服、备份停机或迁盘动作。

## 1. 将来恢复执行时，先确认硬件与管理稳定，再交接窗口

- 先保留iDRAC SEL/Lifecycle与POST证据，按T630维护规程在正常关机、断开电源并采取ESD措施后由合格人员诊断DIMM_B1路径；不把F1继续启动视为修复，不清日志掩盖错误。用户当前暂停，文档不要求立即动硬件。只有硬件稳定后，root才核PVE21.22与GW21.23、受信SSH/QGA；21.1可达本身不等于T630恢复。不能重跑旧网络初始化器猜修，也不把一次连接超时改写成已停服。
- 因可能发生过物理断连/电源事件，先读实际bootID、RAID/存储健康、各guest挂载/文件系统状态、原Nexusunit/两容器健康；未恢复干净状态时先给root处理，不直接照旧stage激活。
- 用户停机授权记录继续有效，不重复索要；但后续明确“暂停”控制当前执行。实际stop/复制须等用户/管理员明确恢复本任务，并由root确认硬件稳定、可信管理恢复及具体窗口；不能借旧授权越过暂停。

## 2. 新鲜核对source和standby，勿重建/重新安装

- source221仍应为artifact-service、19.31/24、原数据/srv/nexus ext4 UUID239dc45a-b1f3-408b-a8ef-7afa77b52204、UID/GID200及原db/blobs；实际先读，不假设它一直运行或已停。
- target220仍应publish-service、原MACbc:24:11:2a:01:ad、primary19.30；此时**不能**提前拥有31。Docker29.9.3 classic-overlay2/featuresfalse、原两AMD64 SHA-ID已缓存、无stack；不要重跑install-docker220.py，也不blind重建standby。
- nonce仍为cb01b8582f544381b0461001dfa3ccb4，target `/root/dell-nexus-merge/<nonce>` 的incoming/prepared/journal应root700/600、phase prepared-no-active-install；按私有manifest比较source当前13项。env/三个Nexussecret的hash比较只在同owner受控内存/guest600记录，不输出值/私有hash，不做含秘密Mac归档。若source已被管理动作更改，停止沿用旧prepared，明确新差异后再stage。
- 核source实际repo/所有现存GAV和原234主SHA、EULA/用户roles/group。旧验证器预期49组件；如果源新增了合法数据，不删除或回退到49来凑通过，应冻结新的全量基线并评审期望。只读GET，不调用初始化/import/upload/rebuild。
- publisher私钥只stat元数据与原准备记录比，不读取内容、不wholebackup220。source221三新Nexus凭据可按既有明确最小SSH管道搬，同owner root600；不搬220key/任何SSH hostkeys。

## 3. root冷备与唯一所有权交接

1. 新窗内先source GET-only基线/两imageID与身份私有hash，再正常stop原dell-nexus、确认2容器停止；保留OS给root最后metadata。此步骤此前未执行，不得把prepare receipt当quiesce receipt。
2. 在原unit已停止、两容器不再写之后，root先正常关机221并确认stopped，再对**已停止的221**做受保护完整vzdump --mode stop，完成SHA/zstd/VMA校验并再次确认它仍off；归档仅PVE root700/600，不exportMac。随后才进入220停机/盘与31移交。不能先对运行源做stop模式备份后假定它不会自动恢复运行；220永不wholebackup，不能复制其发布key。
3. root正常停220，设6CPU/8GiB；执行已核本机语义的`qm move-disk 221 scsi1 --target-vmid 220 --target-disk scsi2`，**不传storage，不把rename/move称保留拷贝**，同盘不能并挂RW。两scsi0及源备份保留。
4. root给220同MAC加31服务alias、primary30/default源30保持，默认GW/DNS19.1；PVE L2/网关/IPAM把31从221转220。保留VPN10/24既有已授权路径及业务认证，不重做无关网络。
5. 管理仍用220/19.30自己的hostkey；SSH31会变成220身份，不复制221hostkey伪装。scripts/control.py本地**已实现additional_ips严格同NIC白名单支持**，无需再开发该补丁。恢复任务时先按唯一角色所有权更新plan：220主ip19.30、additional_ips声明19.31，221不得同时active claim31，再fresh验证实际同NIC/声明地址和受信指纹；未知/重复或跨NIC地址仍拒绝，expected_ip与SSH固定primary19.30。不能关闭hostkey，也不能以dell-vm221 alias连220。

## 4. 必要本地toolfix（尚未同步target）

本轮只做两项小补充，未上传/执行：

- target.py final guard增加`ip -j route get 192.168.19.45`的prefsrc/src必须19.30。双IP存在不等于发布SSH实际源正确；这是纯路由查验，不用发布key、不发SSH/publish。保留原6CPU/8GiB/MAC/双IP/UUID/classic/image guards。
- verify220.py增加无凭据GET原hosted资源必须401/403，保持认证边界；原验证仍拒绝所有非GET方法，不跑PUT/DELETE负测、bootstrap或重接受EULA。

本地py_compile与原6pure tests通过。恢复后上传必须按preparation-readback.json里已上传旧SHA作精确CAS，先给root复核；不能未经核对覆盖远端改动。当前已上传target.py旧SHA为c7839413765d1bd62faed4d51260cc60f99de5822d3ad45ca605029aeac51cab。

## 5. 再开放mount/commit/start

root确认冷备/源off/唯一盘所有权/别名及双IP管理后，按PLAN原nonce调用target.py mount→commit→start，加显式handover确认。别在管理断连期间试探这些动作。

- Mount按原UUID239定位且校唯一设备/非根盘，保留/srv/dell-build UUID16dc...；不format，不按sd字母猜，不递归chown整个盘。首次commit前target无active Nexus路径/unit/secret目录；如发现部分旧安装，要先读journal与manifest，不绕guard盲重跑。
- commit只hostname合同和两image引用变化，其它源/env/身份不变；start原unit有限等2healthy/原ID。若unit已active而journal未收尾，只先读事实再幂等确认，不能重复移盘或重复初始化。
- verify220仅GET验证全量新鲜基线+原49GAV/234主SHA、35元数据语义/1076checksum、EULA/身份/角色/group、匿名拒绝、30发布profile/非docker组/socket拒绝。publisher仍fenced、Java业务仍停，不以测试模板重新激活旧5服务。

## 6. 10→9监控阶段是独立配套窗

最新已验基线位于cleanup/monitoring/ten-role/future-merge-contract.json：**当前10 exporter guests /12永久物理角色 /15 targets，221仍在**。source/runtime十份catalog/installer已成对部署，不使用更老12-role/full9准备manifest，不盲替SHA。

- 当前10节点为200/201/210/220/221/230/240/250/260/270；targeting文件SD10 SHA为dc7cf106ebb42021191018c7eda121cf1deb7128308fee7a75beff9a5bf3c9f0。恢复后以fresh十份live SHA、source/candidate实际对比为准；future contract中的pinned值不是断连后永远有效的事实。
- 当前220 health是publish-service/primary30、3基础units/0HTTP；合并后保留这3项，增加dell-nexus.service与**本机alias**`http://192.168.19.31:8081/service/rest/v1/status`，不要整份拷221配置覆盖publisher role/IP。原collector用local_addresses校URL，alias存在后31已属于本机，**不需放宽任意远端HTTP或认证头**。
- exporter继续只bind30:9100，31不再作为独立物理guest出口。installer/ROLES/catalog从10→9须同步source和九个retained runtime，Nexus候选profile并入publish-service；不是把artifact-service虚构为第二VM。
- Nexus合并数据验证通过且root决定221退役后，才删除221 SD条目/物理role；预期**9node+5Ops=14targets，11永久物理角色**。总CPU/RAM预算从原2204/4+2212/4合成2206/8，本次迁移本身不额外释放4GiB。
- 270规则/collector/PVE-QGA目标按各自已审配套窗最小修改，原Lark active/secret/既有应用URLs和其它role保持。不能因221计划下线就预先删它或伪造UP；维护结束后实际14/14和新220Nexus service/HTTP指标读回，再解除准确维护静默。

## 7. 回退触发与最后签收

任何镜像/身份/UUID/原内容差异或持久化/ACL不满足，都先保持可审journal，不强行删除target来凑通过。root负责停target、撤31、唯一盘反向move回221、恢复源网络/监督；应用文件回退不等于数据/网络灾备，也不wholebackup220。源221OS盘与冷备在最终数据/身份/角色/网络/监控通过前不删。

本清单仅作人工恢复参考；当前合并暂停，不宣称221已冷备、220已8G/双IP、管理已恢复或内存错误已修复。完整人工操作入口见[19-manual-operations.md](../../19-manual-operations.md)。
