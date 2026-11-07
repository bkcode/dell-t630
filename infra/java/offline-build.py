#!/usr/bin/env python3
"""Prepare isolated source/cache snapshots and run serialized offline Gradle probes."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[2]
WORK = BASE / 'private/java-build'
SOURCE = Path('/Users/yangzhaohui/work/www/finger/finger-master/projects')
SERVICES = ['finger-gateway-mobile', 'finger-auth', 'finger-service-system', 'finger-service-coms', 'finger-bff-system']
EXCLUDE_DIRS = {'.git', '.gradle', 'build', 'out', 'target', 'node_modules', '.idea', '.pnpm-store', 'docs', 'logs', 'tmp', 'test-results'}
EXCLUDE_NAMES = {'gradle.properties', 'local.properties', '.DS_Store', 'AGENTS.md', 'AGENTS.local.md', 'CLAUDE.md'}
ROOT_FILES = {'build.gradle.kts', 'settings.gradle.kts', 'build.gradle', 'settings.gradle', 'gradlew', 'gradlew.bat', 'gradle.lockfile'}


def now():
    return dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def git_state(path):
    env = {'PATH': '/usr/bin:/bin', 'GIT_OPTIONAL_LOCKS': '0'}
    def git(*args):
        result = subprocess.run(['/usr/bin/git', '-C', str(path), *args], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    return {'head': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
            'status_porcelain': git('status', '--porcelain', '--untracked-files=normal')}


def excluded(path, relative):
    if any(part in EXCLUDE_DIRS for part in relative.parts):
        return True
    name = path.name.lower()
    if path.is_symlink() or name in EXCLUDE_NAMES or name.startswith('.env'):
        return True
    if not path.is_dir() and path.suffix.lower() not in {'.kt', '.java', '.kts', '.gradle'} and any(word in name for word in ['credential', 'password', 'secret', 'private-key']):
        return True
    if path.suffix.lower() in {'.key', '.pem', '.p12', '.pfx', '.jks', '.keystore'}:
        return True
    if re.match(r'application.*\.ya?ml$', name) or name.endswith('.properties') and name != 'gradle-wrapper.properties':
        return True
    return False


def prepare():
    if WORK.exists():
        raise RuntimeError('Workspace already exists; refusing to replace snapshots or logs')
    WORK.mkdir(mode=0o700)
    states = []
    for service in SERVICES:
        origin = SOURCE / service
        before = git_state(origin)
        target = WORK / 'repos' / service
        target.mkdir(parents=True, mode=0o700)
        records = []
        omitted = []
        for current, dirs, files in os.walk(origin):
            current = Path(current)
            rel_dir = current.relative_to(origin)
            dirs[:] = [name for name in dirs if not excluded(current/name, rel_dir/name)]
            for name in files:
                source = current/name
                relative = source.relative_to(origin)
                # Root source docs/configs are not needed for this build probe.
                if len(relative.parts) == 1 and name not in ROOT_FILES:
                    continue
                if excluded(source, relative):
                    omitted.append(str(relative))
                    continue
                if not (relative.parts[0] in {'src', 'gradle'} or len(relative.parts)>1 and relative.parts[1] in {'src', 'gradle'} or name in ROOT_FILES):
                    continue
                output = target/relative
                output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copyfile(source, output)
                output.chmod(0o700 if name == 'gradlew' else 0o600)
                records.append({'path': str(relative), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'bytes': output.stat().st_size})
        after = git_state(origin)
        if before != after:
            raise RuntimeError('Source Git state changed during snapshot: '+service)
        states.append({'service': service, 'source': str(origin), 'git': before,
                       'source_state_unchanged': True, 'files': records, 'omitted_paths': omitted})
    home = WORK/'gradle-home'
    cache_sources = ['caches/modules-2', 'caches/8.14.3', 'caches/jars-9', 'wrapper/dists/gradle-8.14.3-bin']
    for relative in cache_sources:
        origin = Path.home()/'.gradle'/relative
        if not origin.is_dir():
            raise RuntimeError('Required cached directory missing: '+relative)
        target = home/relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # macOS APFS clone-on-write copy; fallback copies into the same private workspace only.
        proc = subprocess.run(['/bin/cp', '-cR', str(origin), str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode:
            if target.exists():
                raise RuntimeError('Cache clone failed with partial target; inspect before retry')
            shutil.copytree(origin, target, symlinks=False)
    # Never copy user gradle.properties, init scripts, daemon logs, or registry credentials.
    (home/'gradle.properties').write_text('org.gradle.daemon=false\norg.gradle.workers.max=2\norg.gradle.parallel=false\norg.gradle.jvmargs=-Xmx1g -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8\nkotlin.compiler.execution.strategy=in-process\norg.gradle.java.installations.auto-download=false\n')
    (home/'gradle.properties').chmod(0o600)
    guard = WORK/'offline-guard.init.gradle'
    guard.write_text('''if (!gradle.startParameter.offline) { throw new GradleException("Offline mode is mandatory") }
allprojects {
  tasks.configureEach { task ->
    if (task.name.toLowerCase().contains("publish") || task.name.toLowerCase().contains("deploy")) {
      task.onlyIf { throw new GradleException("Publishing and deployment prohibited in offline probe") }
    }
  }
}
''')
    guard.chmod(0o600)
    dump(WORK/'snapshot.json', {'schema_version': 1, 'prepared_at': now(), 'source_snapshots': states,
                              'cache_sources': cache_sources, 'credential_files_copied': False,
                              'runtime_profiles_copied': False, 'status': 'prepared-not-built'})
    print(json.dumps({'status': 'prepared', 'workspace': str(WORK), 'services': SERVICES,
                      'credential_files_copied': False, 'runtime_profiles_copied': False}))


def safe_summary(raw):
    # Only preserve coordinates and known build-failure categories, never arbitrary log lines.
    coords = sorted(set(x.rstrip('.') for x in re.findall(r'\b(?:com\.sargia\.finger|com\.sargia\.finger\.gradle-conventions|org\.jetbrains\.kotlin|org\.springframework\.boot|com\.google\.devtools\.ksp)[A-Za-z0-9_.-]*:[A-Za-z0-9_.-]+:[A-Za-z0-9_.+~-]+', raw)))
    markers = {'offline_cache_miss': ['available for offline mode', 'offline mode'],
               'plugin_not_found': ['Plugin [id:', 'was not found'],
               'compile_failure': ['Compilation error', 'Compilation failed', 'compileKotlin FAILED'],
               'toolchain_missing': ['Cannot find a Java installation', 'No matching toolchains'],
               'test_failure': ['There were failing tests'],
               'daemon_failure': ['daemon disappeared', 'Could not connect to the Gradle daemon', 'Could not start the daemon process'],
               'lock_permission_failure': ['Operation not permitted', 'Permission denied'],
               'build_success': ['BUILD SUCCESSFUL']}
    return {'coordinates': coords, 'markers': [key for key, patterns in markers.items() if any(p in raw for p in patterns)]}


def probe(service, action, timeout, run_id):
    manifest = WORK/'snapshot.json'
    if not manifest.is_file():
        raise RuntimeError('Run prepare first')
    logs = WORK/'logs'
    logs.mkdir(mode=0o700, exist_ok=True)
    gradle_bins = list((WORK/'gradle-home/wrapper/dists/gradle-8.14.3-bin').glob('*/gradle-8.14.3/bin/gradle'))
    if len(gradle_bins) != 1:
        raise RuntimeError('Exactly one cached Gradle 8.14.3 binary is required')
    java_home = Path.home()/'.local/share/mise/installs/java/temurin-21'
    if not (java_home/'bin/java').is_file():
        raise RuntimeError('Existing Java 21 installation missing')
    api_modules = {'finger-service-system':'system-api','finger-service-coms':'coms-api',
        'finger-common-lib-sms-contract':'common-sms','finger-service-msgs-api-contract':'msgs-api',
        'finger-service-fds-api-contract':'fds-api','finger-service-auds-api-contract':'auds-api',
        'finger-service-exs-api-contract':'exs-api'}
    if action == 'auth-config-test' and service != 'finger-auth':
        raise ValueError('Focused config test is Auth-only')
    if action == 'metadata' and service not in api_modules:
        raise ValueError('metadata applies only to approved source contract modules')
    if service.endswith('-contract') and action == 'bootjar':
        raise ValueError('Contract-only snapshot cannot boot')
    compile_target = ':system-boot:compileKotlin' if service=='finger-service-system' else ':coms-boot:compileKotlin' if service=='finger-service-coms' else ':'+api_modules[service]+':compileKotlin' if service.endswith('-contract') else 'compileKotlin'
    tasks = {'tasks':['tasks','--all'], 'compile':[compile_target], 'auth-config-test':['test','--tests','com.sargia.finger.gateway.auth.config.AuthBootstrapPropertiesTest'],
        'bootjar':[':system-boot:bootJar'] if service=='finger-service-system' else [':coms-boot:bootJar'] if service=='finger-service-coms' else ['bootJar'],
        'metadata':[':'+api_modules.get(service,'')+':'+task for task in ['jar','generatePomFileForMavenJavaPublication','generateMetadataFileForMavenJavaPublication']]}[action]
    command = [str(gradle_bins[0]), '--offline', '--no-daemon', '--max-workers=2', '--console=plain',
               '-Dorg.gradle.jvmargs=-Xmx1g -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8',
               '-Dorg.gradle.parallel=false', '-Dorg.gradle.java.installations.auto-download=false',
               '-Pkotlin.compiler.execution.strategy=in-process', '--init-script', str(WORK/'offline-guard.init.gradle'), *tasks]
    # Whitelist only non-secret process variables; no NEXUS/AWS/proxy credentials or parent JAVA options.
    env = {'PATH': str(java_home/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin', 'JAVA_HOME': str(java_home),
           'GRADLE_USER_HOME': str(WORK/'gradle-home'), 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
           'NEXUS_USERNAME': '', 'NEXUS_PASSWORD': ''}
    if not re.fullmatch(r'[a-z0-9-]{1,40}', run_id):
        raise ValueError('run-id must contain lowercase letters, digits and hyphens')
    profile = WORK/'loopback-only.sb'
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
                       '(allow network-bind)\n'
                       '(allow network-inbound (local ip "localhost:*"))\n'
                       '(allow network-outbound (remote ip "localhost:*"))\n'
                       '(deny file-read* (literal "/Users/yangzhaohui/.gradle/gradle.properties"))\n'
                       '(deny file-read* (literal "/Users/yangzhaohui/.m2/settings.xml"))\n'
                       '(deny file-read* (subpath "/Users/yangzhaohui/.ssh"))\n')
    profile.chmod(0o600)
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), *command]
    log = logs/(service+'-'+action+'-'+run_id+'.log')
    if log.exists():
        raise RuntimeError('Probe log already exists; preserve failure and do not blindly retry')
    started = now()
    timed_out = False
    with log.open('w') as out:
        log.chmod(0o600)
        try:
            process = subprocess.Popen(command, cwd=WORK/'repos'/service, env=env,
                                       stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            code=124;timed_out=True
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
    raw=log.read_text(errors='replace')
    source_same = all(git_state(Path(r['source'])) == r['git'] for r in json.loads(manifest.read_text())['source_snapshots'])
    result={'schema_version':1,'service':service,'action':action,'started_at':started,'finished_at':now(),
            'status':'passed' if code==0 else 'failed','exit_code':code,'timed_out':timed_out,
            'offline':True,'publish_executed':False,'tests_skipped_by_flag':False,
            'gradle_max_heap_mib':1024,'max_workers':2,'source_git_state_unchanged':source_same,
            'network_policy':'sandbox-exec external network denied; loopback only','run_id':run_id,
            'private_log':str(log),'summary':safe_summary(raw),
            'limitations':['No runtime profile copied; artifacts need target external configuration.',
                           'tasks/compile/bootJar do not imply tests have passed.',
                           'Existing Gradle cache was cloned; no user credential files or init scripts copied.']}
    dump(log.with_suffix('.json'),result)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if code==0 and source_same else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('prepare')
    test=sub.add_parser('probe')
    test.add_argument('--service',required=True,choices=SERVICES+['finger-common-lib-sms-contract','finger-service-msgs-api-contract','finger-service-fds-api-contract','finger-service-auds-api-contract','finger-service-exs-api-contract'])
    test.add_argument('--action',choices=['tasks','compile','bootjar','metadata','auth-config-test'],default='tasks')
    test.add_argument('--timeout',type=int,default=180)
    test.add_argument('--run-id',required=True,help='Unique evidence suffix; existing logs are never overwritten')
    a=p.parse_args()
    try:
        if a.command=='prepare':prepare();return 0
        if not 30<=a.timeout<=600:raise ValueError('timeout must be 30..600 seconds')
        return probe(a.service,a.action,a.timeout,a.run_id)
    except Exception as e:
        print(json.dumps({'status':'failed','error_category':type(e).__name__,'message':str(e)}))
        return 2

if __name__=='__main__':sys.exit(main())
