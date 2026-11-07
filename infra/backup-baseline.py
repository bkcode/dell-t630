from pathlib import Path
import subprocess,json,datetime,hashlib
root=Path('/root/dell-bootstrap')
assert not Path('/etc/pve/qemu-server/9020.conf').exists(),'Restore test VMID already exists'
assert subprocess.check_output(['qm','status','9002'],text=True).strip()=='status: stopped'
# Free reserved memory before booting an extra disposable restore target.
p=subprocess.run(['qm','shutdown','232','--timeout','30'],capture_output=True,text=True)
if p.returncode:raise SystemExit('Could not safely stop idle staging Java232; restore not started')
folder=Path('/mnt/pve/store/dell-artifacts/baseline-backup');folder.mkdir(mode=0o700,exist_ok=True)
before=set(folder.glob('*.vma.zst'))
p=subprocess.run(['vzdump','9002','--dumpdir',str(folder),'--mode','stop','--compress','zstd'],capture_output=True,text=True)
if p.returncode:print(p.stdout[-800:],p.stderr[-800:]);raise SystemExit(p.returncode)
new=set(folder.glob('*.vma.zst'))-before
assert len(new)==1
archive=new.pop();archive.chmod(0o600)
p=subprocess.run(['qmrestore',str(archive),'9020','--storage','store','--unique','1'],capture_output=True,text=True)
if p.returncode:print(p.stdout[-800:],p.stderr[-800:]);raise SystemExit(p.returncode)
base=Path('/mnt/pve/store/snippets/dell-linux-default-user.yaml').read_text()
base=base.replace('preserve_hostname: false','preserve_hostname: false\nhostname: dell-restore-baseline')
snippet=Path('/mnt/pve/store/snippets/dell-restore-baseline-user.yaml');snippet.write_text(base);snippet.chmod(0o600)
for a in [['qm','set','9020','--name','dell-restore-baseline','--memory','2048','--cores','2','--net0','virtio,bridge=vmbr0','--ipconfig0','ip=dhcp','--cicustom','user=store:snippets/'+snippet.name,'--onboot','0'],['qm','start','9020']]:
 p=subprocess.run(a,capture_output=True,text=True)
 if p.returncode:print(p.stdout[-500:],p.stderr[-500:]);raise SystemExit(p.returncode)
h=hashlib.sha256()
with archive.open('rb') as f:
 for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
receipt={'at':datetime.datetime.now().isoformat(),'source_vmid':9002,'source_was_stopped':True,'restore_vmid':9020,'archive':str(archive),'bytes':archive.stat().st_size,'sha256':h.hexdigest(),'scope':'disposable OS baseline backup/restore only; no production/application data','limitations':['Guest boot and independent off-host copy validation pending','Not a MySQL/Penpot/Nexus restore acceptance','Idle staging VM232 stopped to retain host memory reserve']}
(root/'baseline-backup-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
