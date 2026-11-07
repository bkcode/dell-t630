#!/usr/bin/env python3
"""Only260, exact nonce loop fixture. Never mutates real NAS unit/data or other guests."""
import argparse,datetime,hashlib,json,os,re,shlex,shutil,socket,stat,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
sys.dont_write_bytecode=True
REAL=Path('/srv/dev-disk-by-uuid-5b19837c-128c-498a-b79d-563db810c34a');REAL_UUID='5b19837c-128c-498a-b79d-563db810c34a'
GUARD=Path('/usr/local/libexec/dell-nas-check-data');PROD_UNIT=Path('/etc/systemd/system/dell-nas-jellyfin.service');PROD_COMPOSE=Path('/opt/dell/nas/compose.yaml')
EXPECTED={'guard':'5ba9fd7cfc37d1e7398a454dff0151c516b15a15b93b3c37061f0486d01120fc','unit':'847a04928bf0d5d831e4cc8c7afe5490b61c7a5cc2d7ad7e570ca1fc7ed017ff','compose':'f57289cc286a4b2991f0c0709f3ef41336931a2041c8d8a051a87e9a434d86a7'}
IMAGE='jellyfin/jellyfin@sha256:fea863d0cd9ec445985d9c75fc6ed64e38a1d2766cf0c250a33d553f4fc1b771';D=['docker','--host','unix:///var/run/docker.sock'];SIZE=4*1024**3;PORT=8096
PROFILE_OVERRIDE='services:\n  jellyfin:\n    cpus: 0.25\n    mem_limit: 512m\n    memswap_limit: 512m\n    pids_limit: 128\n    ports: !override []\nnetworks:\n  default:\n    internal: true\n'
class Failure(RuntimeError):pass

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args,timeout=30,check=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:raise Failure('fixed-operation-failed:'+args[0])
 return p
def docker(*args,**kw):return run(D+list(args),**kw)
def paths(nonce):
 if not re.fullmatch('[a-f0-9]{32}',nonce):raise Failure('invalid-QA-nonce')
 work=Path('/var/lib/dell-nas-sys001')/nonce;mount=Path('/srv/dell-nas-sys001')/nonce/'mount';project='dell-nas-sys001-'+nonce
 return {'nonce':nonce,'work':str(work),'mount':str(mount),'file':str(work/'scratch.ext4'),'unit':project+'.service','project':project,'container':project+'-jellyfin-1','network':project+'_default','unit_file':'/run/systemd/system/'+project+'.service','manifest':str(work/'manifest.json')}
def private(path,data):
 if path.is_symlink():raise Failure('private-path-symlink')
 temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2);f.write('\n')
 os.replace(temp,path)
def load(nonce):
 p=paths(nonce);file=Path(p['manifest'])
 if file.resolve()!=file or file.stat().st_uid!=0 or file.stat().st_mode&0o077:raise Failure('manifest-owner-or-permissions')
 m=json.loads(file.read_text())
 if any(m.get(k)!=v for k,v in p.items()) or m['uuid']==REAL_UUID:raise Failure('manifest-QA-scope-mismatch')
 return m
def save(m):private(Path(m['manifest']),m)
def mount_unit(m):return run(['systemd-escape','--path','--suffix=mount',m['mount']]).stdout.strip()
def mem_available():return int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024

def guest():
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='nas-media' or Path('/etc/pve').exists():raise Failure('assigned260-root-only')
 x=json.loads(run(['ip','-j','addr']).stdout)
 if not any(a.get('local')=='10.63.40.10' for n in x for a in n.get('addr_info',[])):raise Failure('wrong-NAS-address')

def baseline():
 files={'guard':GUARD,'unit':PROD_UNIT,'compose':PROD_COMPOSE,'env':Path('/opt/dell/nas/.env'),'OMVconfig':Path('/etc/openmediavault/config.xml')}
 hashes={k:sha(p) for k,p in files.items()}
 if any(hashes[k]!=v for k,v in EXPECTED.items()):raise Failure('production-template-or-guard-changed')
 unit_meta={}
 for name in ['openmediavault-engined.service','smbd.service','dell-nas-jellyfin.service']:
  p=run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState']);x=dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
  if x.get('ActiveState')!='active':raise Failure('real-NAS-not-active')
  unit_meta[name]=x
 c=json.loads(docker('inspect','--format','{"id":{{json .Id}},"pid":{{json .State.Pid}},"started_at":{{json .State.StartedAt}},"health":{{json .State.Health.Status}},"image":{{json .Image}}}','dell-nas-jellyfin-1').stdout)
 if c['health']!='healthy':raise Failure('real-Jellyfin-unhealthy')
 real_fs=json.loads(run(['findmnt','--json','--mountpoint',str(REAL),'--output','TARGET,SOURCE,FSTYPE,UUID']).stdout)['filesystems'][0]
 if real_fs['uuid']!=REAL_UUID:raise Failure('real-media-UUID-changed')
 name='dell-permission-5193233d83fe453eb9aa1290e404b1bc.bin';samples={s:sha(REAL/s/name) for s in ['media','games','incoming']}
 if set(samples.values())!={'8f106c67b7b0f9ba8fc55ca569989fd955237e2c480ab3d36b63db7229dae35d'}:raise Failure('real-sample-integrity-not-ready')
 return {'files':hashes,'units':unit_meta,'container':c,'real_mount':real_fs,'samples':samples}
def continuity(m,minimum=1024**3):
 if mem_available()<minimum:raise Failure('MemAvailable-below-protected-headroom')
 current=baseline()
 if current!=m['baseline']:raise Failure('real-NAS-continuity-difference')
 return True

def loop_mapping(device):
 if not re.fullmatch('/dev/loop[0-9]+',device):raise Failure('only-loop-device-allowed')
 p=run(['losetup','--json','--output','NAME,BACK-FILE',device]);rows=json.loads(p.stdout)['loopdevices']
 if len(rows)!=1:raise Failure('loop-mapping-ambiguous')
 return rows[0]
def validate_loop(device,backing,expected):
 if not re.fullmatch('/dev/loop[0-9]+',device) or backing!=expected:raise Failure('loop-BACK-FILE-scope-mismatch')
def checked_loop(m):
 device=m['loop'];row=loop_mapping(device);validate_loop(device,row['back-file'],m['file'])
 if row['name']!=device or run(['lsblk','-dnro','TYPE',device]).stdout.strip()!='loop':raise Failure('not-a-loop-block-device')
 f=Path(m['file']);s=f.stat()
 if f.resolve()!=f or not stat.S_ISREG(s.st_mode) or s.st_size!=SIZE or s.st_uid!=0 or s.st_nlink!=1 or os.stat(f.parent).st_dev!=os.stat('/').st_dev:raise Failure('new-rootfs-loopfile-contract')
 return device

def guard(m):
 p=run([str(GUARD),'--mountpoint',m['mount'],'--uuid',m['uuid'],'--minimum-gib','1'],check=False)
 try:x=json.loads(p.stdout)
 except Exception:raise Failure('production-guard-result-not-JSON') from None
 return p.returncode,x

def compose(m,args):return D+['compose','--project-name',m['project'],'--env-file',str(Path(m['work'])/'qa.env'),'-f',str(PROD_COMPOSE),'-f',str(Path(m['work'])/'override.yaml'),*args]
def qa_inspect(m):
 p=docker('inspect','--format','{"id":{{json .Id}},"name":{{json .Name}},"running":{{json .State.Running}},"health":{{if (index .State "Health")}}{{json .State.Health.Status}}{{else}}null{{end}},"pid":{{json .State.Pid}},"started_at":{{json .State.StartedAt}},"status":{{json .State.Status}},"OOM":{{json .State.OOMKilled}},"memory":{{json .HostConfig.Memory}},"memory_swap":{{json .HostConfig.MemorySwap}},"pids":{{json .HostConfig.PidsLimit}},"cpu":{{json .HostConfig.NanoCpus}},"image":{{json .Image}},"ports":{{json .HostConfig.PortBindings}},"ports_effective":{{json .NetworkSettings.Ports}},"mounts":[{{range $i,$v:=.Mounts}}{{if $i}},{{end}}{"source":{{json $v.Source}},"destination":{{json $v.Destination}},"rw":{{json $v.RW}}}{{end}}]}',m['container'],check=False)
 return json.loads(p.stdout) if p.returncode==0 else None

def root_tree(m):
 point=Path(m['mount'])
 if os.path.ismount(point):raise Failure('root-directory-tree-requested-while-mounted')
 return {str(p.relative_to(point)):sha(p) if p.is_file() else 'directory' for p in point.rglob('*')}
def qamount(m):
 device=checked_loop(m)
 if os.path.ismount(m['mount']):raise Failure('QA-mount-already-active')
 if run(['blkid','-s','UUID','-o','value',device]).stdout.strip()!=m['uuid']:raise Failure('QA-filesystem-UUID-differs')
 run(['mount','-t','ext4',device,m['mount']]);code,x=guard(m)
 if code or x.get('status')!='passed':raise Failure('actual-production-guard-positive-failed')
 return {'exit_code':code,'result':x}

def stop_qa(m):
 run(['systemctl','stop',m['unit']],timeout=80,check=False)
 c=qa_inspect(m)
 if c and c['running']:raise Failure('QA-container-still-running-no-force')
def runtime_sample(c):
 sample={'running':c['running'],'status':c['status'],'health':c['health'],'OOM':c['OOM'],'ports_requested':c['ports'],'ports_effective':c['ports_effective'],'memory_limit':c['memory'],'cpu_limit':c['cpu'],'pids_limit':c['pids'],'at':now()}
 if c['pid']>0:
  try:
   line=next(l for l in Path('/proc',str(c['pid']),'cgroup').read_text().splitlines() if l.startswith('0::'))
   group=Path('/sys/fs/cgroup')/line[3:].lstrip('/')
   for name in ['memory.current','memory.peak','pids.current','pids.peak','cpu.stat']:
    file=group/name;sample[name]=file.read_text().strip() if file.exists() else None
  except (OSError,StopIteration):sample['cgroup_sample_unavailable']=True
 return sample

def waiting_old_exited(c,initial,elapsed):
 if c['OOM']:raise Failure('QA-OOM-hard-failure')
 if c['status'] in ['exited','dead']:
  if c['status']=='exited' and initial and initial['status']=='exited' and c['id']==initial['id'] and c['started_at']==initial['started_at'] and elapsed<=15:return True
  raise Failure('QA-new-exit-or-old-state-over15s')
 return False

def ready(m):
 continuity(m);initial=qa_inspect(m);m['C_pre_start_container']={k:initial[k] for k in ['id','started_at','status','OOM']} if initial else None;save(m);run(['systemctl','reset-failed',m['unit']],check=False)
 run(['systemctl','daemon-reload']);loaded=run(['systemctl','show',m['unit'],'--property=LoadState','--value']).stdout.strip()
 if loaded!='loaded':raise Failure('QA-unit-native-load-failed')
 start_clock=time.monotonic();run(['systemctl','start',m['unit']],timeout=30)
 deadline=time.monotonic()+180;streak=0;samples=[]
 while time.monotonic()<deadline:
  continuity(m);c=qa_inspect(m)
  if c and waiting_old_exited(c,initial,time.monotonic()-start_clock):
   state=run(['systemctl','is-active',m['unit']],check=False).stdout.strip()
   if state not in ['active','activating']:raise Failure('QA-unit-not-starting-during-grace')
   m.setdefault('old_exited_transition_samples',[]).append({'id':c['id'],'started_at':c['started_at'],'elapsed_seconds':round(time.monotonic()-start_clock,3)});save(m);time.sleep(.5);continue
  if c and c['running']:
   if c['name']!='/'+m['container'] or c['memory']!=512*1024**2 or c['memory_swap']!=512*1024**2 or c['pids']!=128 or c['cpu']!=250000000:raise Failure('QA-resource-contract-changed')
   if c['image']!=m['image_id'] or c['ports'] not in ({},None) or any((c['ports_effective'] or {}).values()):raise Failure('QA-image-or-zero-publish-contract-difference')
   if any(not x['source'].startswith(m['mount']+'/') for x in c['mounts']):raise Failure('QA-mount-outside-dedicated-volume')
   sample=runtime_sample(c)
   p=docker('exec',c['id'],'curl','-q','--noproxy','*','--fail','--silent','--max-time','3','--output','/dev/null','--write-out','%{http_code}','http://127.0.0.1:8096/health',check=False,timeout=7)
   sample.update(native_HTTP_exit_code=p.returncode,HTTP_status=p.stdout.strip(),HTTP_body_or_credentials_emitted=False)
   samples.append(sample);m['ready_samples']=samples[-60:];save(m)
   streak=streak+1 if p.returncode==0 and p.stdout.strip()=='200' and c['health']=='healthy' else 0
   if streak>=3:return {'native_container_HTTP_status':200,'consecutive_successes':streak,'Docker_health':'healthy','zero_PortBindings':True,'resource_contract':True,'only_QA_volume_mounted':True,'container_id':c['id'],'resource_net_health_samples':samples}
  else:streak=0
  time.sleep(3)
 raise Failure('QA-internal-ready-deadline-no-more-retries')

def render_unit(source,m):
 real_mount=str(REAL);old_unit=run(['systemd-escape','--path','--suffix=mount',real_mount]).stdout.strip();new_unit=mount_unit(m)
 text=source.split('[Install]')[0]
 text=text.replace('Description=Dell NAS Jellyfin (requires verified data filesystem)','Description=Dedicated SYS001 NAS QA '+m['nonce'])
 text=text.replace(real_mount,m['mount']).replace(old_unit,new_unit)
 text=text.replace('WorkingDirectory=/opt/dell/nas','WorkingDirectory='+m['work'])
 old='--env-file /opt/dell/nas/.env -f /opt/dell/nas/compose.yaml'
 new=shlex.join(['--project-name',m['project'],'--env-file',str(Path(m['work'])/'qa.env'),'-f',str(PROD_COMPOSE),'-f',str(Path(m['work'])/'override.yaml')])
 text=text.replace(old,new).replace('up --no-build --abort-on-container-exit','up --no-build --pull never --abort-on-container-exit')
 text=text.replace('--uuid '+REAL_UUID,'--uuid '+m['uuid']+' --minimum-gib 1').replace('Restart=on-failure','Restart=no')
 text=text.replace('[Unit]\n','[Unit]\nJobTimeoutSec=20s\nJobRunningTimeoutSec=20s\n',1)
 if REAL_UUID in text or real_mount in text or '/opt/dell/nas/.env' in text or '--minimum-gib 1' not in text:raise Failure('QA-unit-render-scope-failed')
 return text

def prepare(nonce):
 guest();p=paths(nonce)
 if Path(p['work']).exists() or Path(p['unit_file']).exists() or Path(p['mount']).exists():raise Failure('new-exclusive-QA-objects-required')
 for field in ['work','mount','file']:
  point=Path(p[field])
  if point.resolve(strict=False)!=point:raise Failure('QA-path-symlink-rejected')
 before=baseline()
 if mem_available()<1536*1024**2 or shutil.disk_usage('/').free<8*1024**3:raise Failure('QA-resource-headroom-not-ready')
 for path in [Path('/var/lib/dell-nas-sys001'),Path('/srv/dell-nas-sys001')]:
  if path.resolve(strict=False)!=path:raise Failure('QA-parent-symlink')
  path.mkdir(mode=0o700,exist_ok=True)
  if path.stat().st_uid!=0 or path.stat().st_mode&0o022:raise Failure('QA-parent-not-root-private')
 Path(p['work']).mkdir(mode=0o700);Path(p['mount']).mkdir(mode=0o700,parents=True)
 qa_uuid=str(uuid.uuid4());root_uuid=json.loads(run(['findmnt','--json','--target','/','--output','UUID']).stdout)['filesystems'][0]['uuid']
 if qa_uuid in [REAL_UUID,root_uuid]:raise Failure('QA-UUID-must-be-new')
 m={**p,'uuid':qa_uuid,'phase':'created','created_at':now(),'baseline':before,'loop':None,'image_id':None,'events':[]};save(m)
 canary=Path(m['mount'])/'rootfs-canary';canary.write_bytes(('SYS001-rootfs:'+nonce).encode());canary.chmod(0o600);m['root_tree']=root_tree(m);save(m)
 fd=os.open(m['file'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd);run(['fallocate','--length',str(SIZE),m['file']])
 m['loop']=run(['losetup','--find','--show',m['file']]).stdout.strip();save(m);device=checked_loop(m)
 if run(['findmnt','--source',device],check=False).returncode==0 or run(['wipefs','--no-act','--noheadings','--output','TYPE',device]).stdout.strip():raise Failure('QA-loop-not-empty-or-mounted')
 run(['mkfs.ext4','-q','-U',m['uuid'],device],timeout=60);m['guard_A']=qamount(m)
 for name in ['appdata/jellyfin/config','appdata/jellyfin/cache','media']:
  point=Path(m['mount'])/name;point.mkdir(mode=0o700,parents=True,exist_ok=True);os.chown(point,2000,2000)
 marker=Path(m['mount'])/'QA-volume-canary';marker.write_text('SYS001-volume:'+nonce);m['volume_canary_sha256']=sha(marker)
 image=json.loads(docker('image','inspect','--format','{"id":{{json .Id}},"architecture":{{json .Architecture}}}',IMAGE).stdout)
 if image['architecture']!='amd64':raise Failure('cached-AMD64-image-required')
 m['image_id']=image['id'];env=Path(m['work'])/'qa.env';env.write_text('NAS_MOUNT='+m['mount']+'\nNAS_DATA_UUID='+m['uuid']+'\nNAS_BIND_IP=127.0.0.1\nJELLYFIN_IMAGE='+IMAGE+'\nJELLYFIN_UID=2000\nJELLYFIN_GID=2000\nJELLYFIN_PUBLIC_URL=http://127.0.0.1:'+str(PORT)+'\n');env.chmod(0o600)
 override=PROFILE_OVERRIDE
 (Path(m['work'])/'override.yaml').write_text(override)
 config=json.loads(run(compose(m,['config','--format','json'])).stdout);service=config['services']['jellyfin']
 if set(config['services'])!={'jellyfin'} or config['name']!=m['project'] or service.get('ports') or not config['networks']['default']['internal']:raise Failure('merged-QA-compose-not-isolated')
 fd=os.open(m['unit_file'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 with os.fdopen(fd,'w') as out:out.write(render_unit(PROD_UNIT.read_text(),m))
 save(m)
 proof=ready(m);m.update(phase='A-ready',A=proof);save(m);continuity(m)
 return m,{'A':proof,'guard_A':m['guard_A'],'status':'passed','same_installed_guard_used':True,'test_profile':'v2-internal-only-zero-publish'}

def b1(m):
 continuity(m);stop_qa(m);checked_loop(m)
 run(['umount',m['mount']]);code,x=guard(m)
 if code!=1 or x.get('reason')!='data filesystem is not mounted' or root_tree(m)!=m['root_tree']:raise Failure('B1-negative-guard-or-root-directory-failed')
 continuity(m);m.update(phase='B1-passed',B1={'guard_exit_code':code,'guard_reason':x['reason'],'only_QA_unmounted':True,'root_directory_tree_unchanged':True,'loop_still_attached':True});save(m)
 return {'status':'passed','B1':m['B1']}

def cancel_jobs(m):
 run(['systemctl','stop',m['unit']],check=False,timeout=40)
 lines=run(['systemctl','list-jobs','--no-legend','--no-pager']).stdout.splitlines();names={m['unit'],mount_unit(m)}
 for line in lines:
  parts=line.split()
  if len(parts)>1 and parts[1] in names:run(['systemctl','cancel',parts[0]],check=False)
 pending=[line for line in run(['systemctl','list-jobs','--no-legend','--no-pager']).stdout.splitlines() if any(name in line.split() for name in names)]
 if pending:raise Failure('QA-pending-job-not-cleared')

def failure_metadata(m):
 p=run(['systemctl','show',m['unit'],'--property=LoadState,ActiveState,SubState,Result,ExecMainCode,ExecMainStatus'],check=False)
 unit=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
 fields={'__REALTIME_TIMESTAMP','_SYSTEMD_UNIT','_PID','PRIORITY','MESSAGE_ID','UNIT','JOB_TYPE','JOB_RESULT','RESULT','EXIT_CODE','EXIT_STATUS'}
 p=run(['journalctl','--unit',m['unit'],'--no-pager','-n','20','--output=json','--output-fields='+','.join(sorted(fields))],check=False)
 logs=[]
 if p.returncode==0:
  for line in p.stdout.splitlines():
   try:row=json.loads(line);logs.append({k:v for k,v in row.items() if k in fields})
   except json.JSONDecodeError:pass
 return {'systemd':unit,'journal_metadata':logs,'log_MESSAGE_Env_Cmd_or_credentials_not_returned':True}

def b2(m):
 continuity(m)
 if os.path.ismount(m['mount']) or m['phase']!='B1-passed':raise Failure('B2-requires-unmounted-B1')
 device=checked_loop(m);run(['losetup','--detach',device]);m['loop']=None;save(m)
 if run(['losetup','--associated',m['file']]).stdout.strip():raise Failure('QA-loop-detach-not-complete')
 started=time.monotonic();timedout=False
 try:p=run(['systemctl','start',m['unit']],timeout=25,check=False);code=p.returncode
 except subprocess.TimeoutExpired:timedout=True;code=None
 failure=failure_metadata(m);cancel_jobs(m);c=qa_inspect(m)
 if timedout or code==0 or (c and c['running']) or root_tree(m)!=m['root_tree']:raise Failure('B2-start-not-explicitly-failed-or-root-write')
 unit_state=failure_metadata(m)['systemd']
 if unit_state.get('ActiveState')=='active':raise Failure('QA-unit-active-after-missing-volume')
 continuity(m);m.update(phase='B2-passed',B2={'QA_start_exit_code':code,'client_timeout':False,'elapsed_seconds':round(time.monotonic()-started,3),'job_management_timeout_seconds':20,'only_QA_loop_detached':True,'no_QA_running':True,'root_directory_tree_unchanged':True,'QA_jobs_cleared':True,'failure_metadata':failure,'local_failure_signal_observed':True,'notification_delivery_tested':False,'production_monitoring_changed':False});save(m)
 return {'status':'passed','B2':m['B2']}

def restore(m):
 continuity(m)
 if m['phase']!='B2-passed' or run(['losetup','--associated',m['file']]).stdout.strip():raise Failure('restore-state-or-loop-not-exclusive')
 m['loop']=run(['losetup','--find','--show',m['file']]).stdout.strip();save(m);m['guard_C']=qamount(m)
 if sha(Path(m['mount'])/'QA-volume-canary')!=m['volume_canary_sha256']:raise Failure('same-UUID-volume-canary-changed')
 proof=ready(m);continuity(m);m.update(phase='C-ready',C={**proof,'same_UUID':True,'volume_canary_unchanged':True});save(m)
 return {'status':'passed','C':m['C'],'guard_C':m['guard_C']}

def resume_c(m):
 continuity(m)
 if m.get('C_race_retry_issued') or m['phase']!='B2-passed' or not m.get('loop') or not os.path.ismount(m['mount']):raise Failure('conditional-C-resume-not-eligible')
 checked_loop(m);code,g=guard(m)
 if code or g.get('status')!='passed' or sha(Path(m['mount'])/'QA-volume-canary')!=m['volume_canary_sha256']:raise Failure('conditional-C-volume-identity-failed')
 c=qa_inspect(m)
 if not c or c['running'] or c['OOM'] or c['id']!=m['A']['container_id']:raise Failure('conditional-C-old-instance-not-matching')
 m['C_race_retry_issued']=True;m['guard_C']={'exit_code':code,'result':g};save(m)
 proof=ready(m);continuity(m);m.update(phase='C-ready',C={**proof,'same_UUID':True,'volume_canary_unchanged':True});save(m)
 return {'status':'passed','C':m['C'],'guard_C':m['guard_C'],'conditional_C_correction_used_once':True,'pre_start_container':m['C_pre_start_container'],'old_exited_transition_samples':m.get('old_exited_transition_samples',[]),'old_failure_retained':True}

def cleanup(m):
 guest();failures=[]
 try:cancel_jobs(m);stop_qa(m)
 except Exception as e:failures.append(type(e).__name__+':QA-stop')
 c=qa_inspect(m)
 if c:
  if c['name']!='/'+m['container'] or c['running']:failures.append('QA-container-not-stopped')
  elif docker('rm',c['id'],check=False).returncode:failures.append('QA-container-remove')
 network=docker('network','inspect','--format','{"name":{{json .Name}},"containers":{{json .Containers}}}',m['network'],check=False)
 if network.returncode==0:
  n=json.loads(network.stdout)
  if n['name']!=m['network'] or n['containers']:failures.append('QA-network-not-exclusive-empty')
  elif docker('network','rm',m['network'],check=False).returncode:failures.append('QA-network-remove')
 if os.path.ismount(m['mount']):
  try:
   checked_loop(m);code,_=guard(m)
   if code:raise Failure('cleanup-QA-mount-identity')
   run(['umount',m['mount']])
  except Exception:failures.append('QA-unmount-busy-no-force')
 if m.get('loop'):
  try:device=checked_loop(m);run(['losetup','--detach',device]);m['loop']=None
  except Exception:failures.append('QA-loop-detach')
 if run(['losetup','--associated',m['file']]).stdout.strip():failures.append('QA-loop-still-associated')
 unit=Path(m['unit_file'])
 if unit.exists():unit.unlink();run(['systemctl','daemon-reload']);run(['systemctl','reset-failed',m['unit'],mount_unit(m)],check=False)
 continuity_ok=False
 try:continuity_ok=baseline()==m['baseline']
 except Exception:pass
 result={'status':'passed' if not failures and continuity_ok else 'cleanup-pending','failures':failures,'real_NAS_continuity_unchanged':continuity_ok,'own_container_removed':qa_inspect(m) is None,'own_mount_absent':not os.path.ismount(m['mount']),'own_loop_absent':not run(['losetup','--associated',m['file']]).stdout.strip(),'own_unit_file_absent':not unit.exists()}
 if not failures:
  if root_tree(m)!=m['root_tree']:result['status']='failed-root-directory-changed';failures.append('root-directory-changed')
  else:
   file=Path(m['file'])
   if file.exists():file.unlink()
   shutil.rmtree(Path(m['mount']).parent)
   # Metadata returned to manager before only own nonce control directory is removed.
   shutil.rmtree(Path(m['work']));result['own_loopfile_and_nonce_directories_removed']=True
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','b1','b2','restore','resume-c','cleanup']);p.add_argument('--nonce',required=True);a=p.parse_args();guest();m=None
 try:
  if a.phase=='prepare':m,result=prepare(a.nonce)
  else:
   m=load(a.nonce);result={'b1':b1,'b2':b2,'restore':restore,'resume-c':resume_c,'cleanup':cleanup}[a.phase](m)
  result.update(nonce=a.nonce,phase=a.phase,at=now(),real_media_disk_touched=False)
  result['real_NAS_snapshot']=baseline()
  result['real_NAS_continuity_unchanged']=m is not None and result['real_NAS_snapshot']==m['baseline']
  if m:result['QA_UUID']=m['uuid']
  print(json.dumps(result));return 0 if result['status']=='passed' else 1
 except Exception as error:
  # Stop only QA on any failure; keep its manifest for exact bounded cleanup.
  try:
   m=m or load(a.nonce);stop_qa(m)
  except Exception:pass
  print(json.dumps({'status':'failed','phase':a.phase,'nonce':a.nonce,'error_category':type(error).__name__,'safe_reason':str(error) if isinstance(error,Failure) else 'details-withheld','cleanup_may_be_required':True,'real_services_not_restarted':True}));return 1
if __name__=='__main__':raise SystemExit(main())
