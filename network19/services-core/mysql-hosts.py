#!/usr/bin/env python3
"""Prepared guest210 helper; default plan is SELECT/SHOW only. Auth stays in guest RAM."""
import argparse,hashlib,json,os,socket,subprocess,sys
from pathlib import Path
CONTRACT=json.loads(Path(__file__).with_name('sql-host-contract.json').read_text())
USERS={'finger_auth_test':3,'finger_system_test':5,'finger_coms_test':10};OLD='10.63.20.20';NEW='192.168.19.45';CONTAINER='dell-data-test-data-mysql-1'
class Refused(RuntimeError):pass

def sql(text):
 shell='export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"; exec mysql --user=root --protocol=socket --batch --raw --skip-column-names'
 p=subprocess.run(['docker','--host','unix:///var/run/docker.sock','exec','-i',CONTAINER,'sh','-c',shell],input=text.encode(),capture_output=True,timeout=30)
 if p.returncode:raise Refused('metadata-or-account-operation-failed; SQL/auth details withheld')
 return p.stdout.decode().strip()
def account(user,host,q='`'):return q+user+q+'@'+q+host+q

def grants(user,host):return sql('SHOW GRANTS FOR '+account(user,host)+';').splitlines()
def checked_grants(user,host):
 rows=grants(user,host)
 if sorted(g.split(' TO ',1)[0] for g in rows)!=CONTRACT['accounts'][user]['grant_prefixes']:raise Refused('exact-source-table-grant-list-changed')
 plugin=sql("SELECT plugin FROM mysql.user WHERE user='"+user+"' AND host='"+host+"';")
 if plugin!=CONTRACT['accounts'][user]['plugin']:raise Refused('authentication-plugin-changed')
 dml=[x for x in rows if x.startswith('GRANT SELECT, INSERT, UPDATE, DELETE ON `'+user+'`.`')]
 if len(dml)!=USERS[user] or len(rows)!=len(dml)+1 or not any(x.startswith('GRANT USAGE ON *.* TO ') for x in rows):raise Refused('expected-exact18-table-DML-contract-differs')
 if any('WITH GRANT OPTION' in x or 'IDENTIFIED' in x for x in rows):raise Refused('grant-option-or-sensitive-contract-rejected')
 return rows

def parse_create_rest(raw,user,host):
 def complete(statement):
  for quote in ['`',"'"]:
   prefix='CREATE USER '+account(user,host,quote)+' '
   if statement.startswith(prefix):return statement[len(prefix):]
  return None
 body=complete(raw)
 if body is not None:return body  # Opaque auth body may contain literal TAB; do not split it.
 if '\t' in raw:
  first,statement=raw.split('\t',1)
  if first in [user+'@'+host,account(user,host),account(user,host,"'")]:
   body=complete(statement)
   if body is not None:return body
 raise Refused('unsupported-canonical-CREATE-USER-format')

def create_rest(user,host):
 return parse_create_rest(sql('SHOW CREATE USER '+account(user,host)+';'),user,host)

def exists(user,host):return sql("SELECT COUNT(*) FROM mysql.user WHERE user='"+user+"' AND host='"+host+"';")=='1'
def migrate_grants(rows,user,source,target):
 old=' TO '+account(user,source);new=' TO '+account(user,target)
 result=[]
 for row in rows:
  if row.count(old)!=1 or not row.endswith(old):raise Refused('noncanonical-targeted-GRANT-suffix')
  result.append(row[:-len(old)]+new)
 return result

def clone(user,source,target):
 source_grants=checked_grants(user,source);body=create_rest(user,source)  # Includes auth hash; never stored/output.
 target_grants=migrate_grants(source_grants,user,source,target)
 if exists(user,target):
  if create_rest(user,target)!=body or set(grants(user,target))!=set(target_grants):raise Refused('existing-newHost-auth-or-grants-conflict')
  return False
 sql('CREATE USER '+account(user,target)+' '+body+';')
 try:
  for statement in target_grants:sql(statement+';')
  if create_rest(user,target)!=body or set(grants(user,target))!=set(target_grants):raise Refused('newHost-private-auth-or-grants-comparison-failed')
 except Exception:
  sql('DROP USER '+account(user,target)+';');raise
 return True

def root_receipt(path,phase):
 if path is None or path.resolve()!=path or path.stat().st_uid!=0 or path.stat().st_mode&0o077:raise Refused('explicit-root600-window-receipt-required')
 r=json.loads(path.read_text())
 if r.get('migration')!='network19' or r.get('target_vmid')!=210 or r.get('allowed_phase')!=phase or r.get('parent_window_open') is not True:raise Refused('receipt-phase-not-authorized')
 if phase=='retire-old' and not all(r.get(k) is True for k in ['Java19_45_current_user_exact_host_verified','all18_DML_grants_verified','new_network_rollback_release_ready','no_old_client_connections']):raise Refused('retire-old-extra-gates-not-met')
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['plan','add-new','retire-old','restore-old'],default='plan');p.add_argument('--apply',action='store_true');p.add_argument('--root-receipt',type=Path);p.add_argument('--ledger',type=Path,default=Path('/root/dell-network19/mysql-host-ledger.json'));a=p.parse_args()
 if os.geteuid()!=0 or socket.gethostname().split('.')[0]!='data-test' or Path('/etc/pve').exists():raise Refused('only-assigned210-guest-root')
 rows=[]
 for user,count in USERS.items():
  source=NEW if a.phase=='restore-old' else OLD
  if a.phase=='retire-old' and not exists(user,OLD):source=NEW
  original=checked_grants(user,source);rows.append({'user':user,'old_host':OLD,'new_host':NEW,'DML_table_count':count,'plugin_expected':'caching_sha2_password','source_grants_sha256':hashlib.sha256('\n'.join(original).encode()).hexdigest()})
 if not a.apply:
  print(json.dumps({'status':'read-only-plan','phase':a.phase,'accounts':rows,'Nacos_percent_accounts_untouched':True,'auth_hashes_or_passwords_read':False,'writes':0}));return
 if a.phase=='plan':raise Refused('plan-never-writes')
 root_receipt(a.root_receipt,a.phase);created=[];completed=[]
 if a.phase in ['add-new','restore-old']:
  source,target=(OLD,NEW) if a.phase=='add-new' else (NEW,OLD)
  try:
   for user in USERS:
    if clone(user,source,target):created.append(user)
    completed.append(user)
  except Exception:
   for user in created:sql('DROP USER '+account(user,target)+';')
   raise
 else:
  for user in USERS:
   checked_grants(user,NEW)
   if exists(user,OLD):
    if create_rest(user,OLD)!=create_rest(user,NEW):raise Refused('retire-private-auth-hash-differs')
    if set(migrate_grants(checked_grants(user,OLD),user,OLD,NEW))!=set(grants(user,NEW)):raise Refused('retire-exact-grants-differ')
  for user in USERS:
   if exists(user,OLD):sql('DROP USER '+account(user,OLD)+';')
   completed.append(user)
 # DDL is autocommit: ledger is not a pretend SQL transaction and never includes CREATE USER/auth body.
 a.ledger.parent.mkdir(mode=0o700,parents=True,exist_ok=True);a.ledger.write_text(json.dumps({'migration':'network19','phase':a.phase,'completed_users':completed,'created_users_this_phase':created,'Nacos_percent_accounts_untouched':True,'auth_or_password_values_stored':False},indent=2)+'\n');a.ledger.chmod(0o600)
 print(json.dumps({'status':'applied-under-explicit-receipt','phase':a.phase,'accounts_completed':len(completed),'auth_unchanged_private_comparison':True,'Nacos_accounts_unchanged':True,'secret_values_emitted':False}))
if __name__=='__main__':
 try:main()
 except Exception as error:
  print(json.dumps({'status':'refused-or-failed','error_category':type(error).__name__,'message':str(error) if isinstance(error,Refused) else 'details-withheld'}));sys.exit(1)
