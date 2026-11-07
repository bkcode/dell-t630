#!/usr/bin/env python3
"""Focused actual-class regression in the credential-free offline build sandbox."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,subprocess,time,xml.etree.ElementTree as ET
BASE=Path(__file__).resolve().parents[3];WORK=BASE/'private/java-build';GATEWAY=WORK/'repos/finger-gateway-mobile'
p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args();assert re.fullmatch('[a-z0-9-]{1,50}',a.run_id)
logs=WORK/'logs';log=logs/('gateway-redis-'+a.run_id+'.log');assert not log.exists(),'Preserve prior result'
gradles=list((WORK/'gradle-home/wrapper/dists/gradle-8.14.3-bin').glob('*/gradle-8.14.3/bin/gradle'));assert len(gradles)==1
java=Path.home()/'.local/share/mise/installs/java/temurin-21';assert (java/'bin/java').is_file()
command=['/usr/bin/sandbox-exec','-f',str(WORK/'loopback-only.sb'),str(gradles[0]),'--offline','--no-daemon','--max-workers=2','--console=plain','-Dorg.gradle.jvmargs=-Xmx1g -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8','-Dorg.gradle.parallel=false','-Dorg.gradle.java.installations.auto-download=false','-Pkotlin.compiler.execution.strategy=in-process','--init-script',str(WORK/'offline-guard.init.gradle'),'test','--tests','com.sargia.finger.gateway.mobile.config.GatewayRedisConfigurationTest']
env={'PATH':str(java/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin','JAVA_HOME':str(java),'GRADLE_USER_HOME':str(WORK/'gradle-home'),'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','NEXUS_USERNAME':'','NEXUS_PASSWORD':''}
started=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
with log.open('w') as output:
 log.chmod(0o600);process=subprocess.run(command,cwd=GATEWAY,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=600)
raw=log.read_text(errors='replace');xml=GATEWAY/'build/test-results/test/TEST-com.sargia.finger.gateway.mobile.config.GatewayRedisConfigurationTest.xml';cases=[]
if xml.exists():
 tree=ET.parse(xml).getroot()
 for c in tree.findall('testcase'):
  failures=[]
  for f in list(c.findall('failure'))+list(c.findall('error')):
   text=(f.text or '')+' '+f.attrib.get('message','');classes=sorted(set(re.findall(r'\b(?:[A-Za-z_$][\w$]*\.)*[A-Z][\w$]*(?:Exception|Error)\b',text)));failures.append({'type':f.attrib.get('type'),'exception_classes':classes})
  cases.append({'name':c.attrib.get('name'),'failed':bool(failures),'failures':failures})
summary={'run_id':a.run_id,'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'exit_code':process.returncode,'offline':True,'external_network_denied':True,'source_credentials_read':False,'private_log':str(log),'test_cases':cases,'compile_failure':bool(re.search('compileTestKotlin FAILED|Compilation error',raw)),'missing_coordinates':sorted(set(re.findall(r'\b(?:com|org|net|io)[A-Za-z0-9_.-]*:[A-Za-z0-9_.-]+:[A-Za-z0-9_.+~-]+',raw))),'global_bean_overriding_enabled':False}
path=log.with_suffix('.json');path.write_text(json.dumps(summary,indent=2)+'\n');path.chmod(0o600);print(json.dumps(summary));raise SystemExit(process.returncode)
