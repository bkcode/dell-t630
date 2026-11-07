#!/opt/homebrew/opt/python@3.14/bin/python3.14 -I
"""One fixed corrective notice for the observed launchd execution mismatch, no arbitrary text/target."""
import importlib.util,json,hashlib
from pathlib import Path
p=Path(__file__).with_name('probe.py');s=importlib.util.spec_from_file_location('probe',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
body=json.dumps({'msg_type':'text','content':{'text':'【验收更正】【Dell T630 外部探测】\n刚才的主机不可达告警来自Mac后台探针运行环境异常，独立复核七个服务器入口全部正常，未观察到服务器实际掉线。\n该定时探针已暂停，保留真实诊断记录排查；没有停止测试网关或正式业务。服务器内部监控正常，Lark内部通知接入继续。'}},ensure_ascii=False,separators=(',',':')).encode()
ok=m.send_lark(body)
record={'at':m.now(),'status':'corrective-notice-acknowledged' if ok else 'corrective-notice-not-acknowledged','upstream_code':0 if ok else None,'payload_sha256':hashlib.sha256(body).hexdigest(),'webhook_value_emitted':False,'production_probe_state_rewritten':False}
root=Path(__file__).resolve().parents[3];(root/'evidence/implementation/mac-external-probe-corrective-notice.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));raise SystemExit(0 if ok else 1)
