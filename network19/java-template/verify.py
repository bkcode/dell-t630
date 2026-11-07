#!/usr/bin/env python3
"""Generic Java21 acceptance only. No role IP, application, config or credential."""
import argparse,hashlib,json,os,pwd,re,shutil,socket,subprocess,tempfile
from pathlib import Path
FORBIDDEN_DIRS=['/opt/finger','/etc/nacos','/var/lib/mysql','/opt/dell/ops','/etc/penpot','/etc/nexus.env','/var/lib/dell-gateway19']
def command(args,cwd=None):
 env=dict(os.environ);env.pop('JAVA_TOOL_OPTIONS',None);env.pop('JDK_JAVA_OPTIONS',None)
 r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=30,env=env)
 if r.returncode:raise RuntimeError('fixed acceptance command failed; output withheld')
 return (r.stdout+r.stderr).strip()
def main():
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');args=p.parse_args();java=pwd.getpwnam('java')
 if java.pw_uid==0 or os.geteuid()!=java.pw_uid:raise RuntimeError('run the acceptance script as the dedicated nonroot java account')
 versions={'java':command(['/usr/bin/java','-Xms16m','-Xmx64m','-version']),'javac':command(['/usr/bin/javac','-version'])}
 if not re.search(r'\bversion "21[.\"]',versions['java']) or not re.match(r'javac 21\b',versions['javac']):raise RuntimeError('JDK21 java and javac required')
 bad=[x for x in FORBIDDEN_DIRS if Path(x).exists()]
 if bad:raise RuntimeError('business or role state present; this is not a clean acceptance clone')
 ports=command(['ss','-H','-lntup']);forbidden={3306,6379,5672,15672,8848,9848,9849,9999,10000,10104,10202,10210,8081,8096,9001,9090,9093,9100,19093};unexpected=[]
 for line in ports.splitlines():
  fields=line.split()
  if len(fields)>4:
   try:port=int(fields[4].rsplit(':',1)[1])
   except ValueError:continue
   if port in forbidden:unexpected.append(port)
 if unexpected:raise RuntimeError('business/exporter listeners must be absent on a generic parked template')
 if subprocess.run(['pgrep','-x','java'],capture_output=True).returncode==0:raise RuntimeError('persistent Java process already present')
 exporter=subprocess.run(['systemctl','is-enabled','prometheus-node-exporter.service'],capture_output=True,text=True);active=subprocess.run(['systemctl','is-active','--quiet','prometheus-node-exporter.service'],capture_output=True)
 if exporter.stdout.strip()!='masked' or active.returncode==0:raise RuntimeError('generic exporter must remain parked/masked until instance IP/role authorization')
 report={'status':'java21-clean-nonroot-acceptance-passed','uid':os.geteuid(),'user':'java','versions':versions,'business_artifacts_present':False,'business_or_exporter_listeners':[],'exporter_parked':True,'CPU_count':os.cpu_count(),'loadavg':list(os.getloadavg()),'filesystem_free_bytes':shutil.disk_usage('/').free,'MemTotal_kib':int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:'))),'machine_id_sha256':hashlib.sha256(Path('/etc/machine-id').read_bytes()).hexdigest(),'boot_id_sha256':hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes()).hexdigest(),'network_or_external_messages_sent':False}
 if args.smoke:
  with tempfile.TemporaryDirectory(prefix='java-acceptance-') as tmp:
   file=Path(tmp)/'Acceptance.java';file.write_text('public class Acceptance { public static void main(String[] a) { if(Runtime.version().feature()!=21) throw new RuntimeException("major"); System.out.print("JAVA21_ACCEPTANCE_ONLY:"+System.getProperty("user.name")); }}\n');command(['/usr/bin/javac','--release','21',str(file)],tmp);result=command(['/usr/bin/java','-Xms16m','-Xmx64m','-XX:ActiveProcessorCount=1','-cp',tmp,'Acceptance'],tmp)
   if result!='JAVA21_ACCEPTANCE_ONLY:java':raise RuntimeError('temporary nonroot compiler/runtime smoke failed')
  report['temporary_compile_and_run']='passed; source/class automatically removed'
 print(json.dumps(report))
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'status':'failed','message':'generic acceptance failed; no secrets/business output emitted'}));raise
