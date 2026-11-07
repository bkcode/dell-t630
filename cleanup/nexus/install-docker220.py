#!/usr/bin/env python3
"""Explicit220 preparation only. Install pinned Docker with classic storage BEFORE first startup."""
import json,os,re,shutil,socket,stat,subprocess,time
from pathlib import Path
ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C','LC_ALL':'C','DEBIAN_FRONTEND':'noninteractive','NEEDRESTART_MODE':'l'}
VERSIONS={'docker-ce':'5:29.9.3-1~debian.13~trixie','docker-ce-cli':'5:29.9.3-1~debian.13~trixie','containerd.io':'2.4.2-3~debian.13~trixie','docker-compose-plugin':'5.7.0-1~debian.13~trixie'}
DAEMON={'features':{'containerd-snapshotter':False},'storage-driver':'overlay2','live-restore':False,'log-driver':'local','log-opts':{'max-size':'10m','max-file':'3'}}
BACKUP=Path('/root/dell-nexus-consolidation/docker-prepare')


def run(args,timeout=60,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,env=ENV)
    if check and p.returncode:raise RuntimeError('fixed package/runtime command failed; raw output withheld')
    return p


def meta(path):
    p=Path(path);s=p.stat();return {'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'size':s.st_size,'inode':s.st_ino,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}


def backup(path):
    p=Path(path)
    if p.is_symlink():raise RuntimeError('unexpected config symlink')
    name=path.strip('/').replace('/','__')
    if p.exists():
        raw=p.read_bytes();(BACKUP/name).write_bytes(raw);(BACKUP/name).chmod(0o600)
        return {'existed':True,'mode':stat.S_IMODE(p.stat().st_mode),'backup':name}
    return {'existed':False}


def main():
    os.umask(0o077)
    if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='publish-service' or Path('/etc/pve').exists():raise RuntimeError('assigned220 only')
    release=Path('/etc/os-release').read_text();assert 'ID=debian' in release and 'VERSION_ID="13"' in release
    addrs=json.loads(run(['/usr/sbin/ip','-j','addr']).stdout);nics=[x for x in addrs if x.get('address','').lower()=='bc:24:11:2a:01:ad'];assert len(nics)==1
    ips={x.get('local') for x in nics[0].get('addr_info',[]) if x.get('family')=='inet'};assert ips=={'192.168.19.30'},'prepare must not pre-bind source221 alias'
    assert shutil.which('docker') is None and not Path('/opt/dell/nexus').exists(),'refuse existing stack/runtime'
    assert not Path('/var/lib/docker/containers').exists() or not any(Path('/var/lib/docker/containers').iterdir())
    key='/var/lib/dell-publisher/.ssh/test240_ed25519';keybefore=meta(key)
    groups_before=run(['/usr/bin/id','publisher']).stdout.strip();assert 'docker' not in groups_before
    if BACKUP.exists():raise RuntimeError('prior Docker preparation exists; inspect before retry')
    BACKUP.mkdir(parents=True,mode=0o700);BACKUP.chmod(0o700)
    configs={p:backup(p) for p in ['/etc/docker/daemon.json','/etc/apt/sources.list.d/docker.sources','/etc/apt/keyrings/docker.asc','/usr/sbin/policy-rc.d']}
    Path('/etc/docker').mkdir(mode=0o755,exist_ok=True)
    Path('/etc/docker/daemon.json').write_text(json.dumps(DAEMON,indent=2)+'\n');Path('/etc/docker/daemon.json').chmod(0o644)
    Path('/etc/apt/keyrings').mkdir(mode=0o755,exist_ok=True)
    # Public Docker signing key via TLS only; no registry/client credentials.
    p=run(['/usr/bin/curl','-q','--noproxy','*','--proto','=https','--max-redirs','0','--fail','--silent','--connect-timeout','10','--max-time','45','https://download.docker.com/linux/debian/gpg'],timeout=50)
    assert p.stdout.startswith('-----BEGIN PGP PUBLIC KEY BLOCK-----')
    Path('/etc/apt/keyrings/docker.asc').write_text(p.stdout);Path('/etc/apt/keyrings/docker.asc').chmod(0o644)
    Path('/etc/apt/sources.list.d/docker.sources').write_text('Types: deb\nURIs: https://download.docker.com/linux/debian\nSuites: trixie\nComponents: stable\nArchitectures: amd64\nSigned-By: /etc/apt/keyrings/docker.asc\n');Path('/etc/apt/sources.list.d/docker.sources').chmod(0o644)
    run(['/usr/bin/apt-get','update','-qq'],timeout=180)
    packages=[k+'='+v for k,v in VERSIONS.items()]
    simulation=run(['/usr/bin/apt-get','-s','--no-install-recommends','install',*packages],timeout=120).stdout
    upgrades=[line for line in simulation.splitlines() if re.match(r'^Inst \S+ \[',line)]
    removals=[line for line in simulation.splitlines() if line.startswith('Remv ')]
    if upgrades or removals:raise RuntimeError('existing package upgrade/removal in plan; installation not run')
    # Service-autostart suppression is temporary and restored byte-for-byte; no other service restarts.
    original=configs['/usr/sbin/policy-rc.d'];policy=Path('/usr/sbin/policy-rc.d')
    body='#!/bin/sh\n# Dell bounded Docker prepare: do not autostart services during this apt transaction.\nexit 101\n'
    policy.write_text(body);policy.chmod(0o755)
    try:
        run(['/usr/bin/apt-get','-y','--no-install-recommends','-o','Dpkg::Lock::Timeout=120','install',*packages],timeout=600)
    finally:
        if policy.read_text()!=body:raise RuntimeError('policy changed by third party; do not overwrite')
        if original['existed']:
            policy.write_bytes((BACKUP/original['backup']).read_bytes());policy.chmod(original['mode'])
        else:policy.unlink()
    run(['/usr/bin/dockerd','--validate','--config-file','/etc/docker/daemon.json'])
    run(['/usr/bin/systemctl','enable','--now','docker.service'],timeout=120)
    info=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','info','--format','{"name":{{json .Name}},"driver":{{json .Driver}},"root":{{json .DockerRootDir}},"containers":{{json .Containers}},"live_restore":{{json .LiveRestoreEnabled}},"version":{{json .ServerVersion}},"arch":{{json .Architecture}}}']).stdout)
    assert info['name']=='publish-service' and info['driver']=='overlay2' and info['root']=='/var/lib/docker' and info['containers']==0 and not info['live_restore'] and info['arch']=='x86_64'
    assert meta(key)==keybefore and run(['/usr/bin/id','publisher']).stdout.strip()==groups_before
    denied=run(['/usr/sbin/runuser','-u','publisher','--','/usr/bin/test','-w','/var/run/docker.sock'],check=False);assert denied.returncode!=0
    record={'role':220,'status':'Docker-classic-ready-no-Nexus-stack','versions':VERSIONS,'daemon':info,'daemon_config':DAEMON,'publisher_group_unchanged_not_docker':True,'publisher_socket_write_denied':True,'publisher_key_metadata_unchanged_contents_not_read':True,'existing_packages_upgraded_or_removed':False,'Nexus_started_or_alias31_bound':False,'config_backups':configs}
    (BACKUP/'result.json').write_text(json.dumps(record,indent=2)+'\n');(BACKUP/'result.json').chmod(0o600)
    print(json.dumps(record))

if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'role':220,'status':'Docker-preparation-unconfirmed','private_backup_retained':True,'raw_details_withheld':True}));raise SystemExit(1)
