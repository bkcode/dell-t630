"""Pure retarget of a same-instance Nexus package, preserving endpoints/data/identities."""
import json

DATA_UUID='239dc45a-b1f3-408b-a8ef-7afa77b52204'
IP='192.168.19.31'
SOURCE_HOST='artifact-service'
TARGET_HOST='publish-service'
IMAGES={
 'sonatype/nexus3@sha256:e190be450888ec912b941579bac90767d73debc3307a26326c8a71132b02951f':'sha256:2ae4fee2eed85f42c982aa2fc16746a8453c7f79faf2a7ea236855ca8652e001',
 'nginx@sha256:db4f612f385437d11eb26620a4f1d7efb3ff44e1296a3c21540b30454e6e2bf3':'sha256:4e5db4761e0ff445f7fd29aad680ad28e8abf7d204895557f145d65535abcc1c'}
FILES={
 'package/assignment.json':'/opt/dell/nexus/assignment.json',
 'package/target_guard.py':'/opt/dell/nexus/target_guard.py',
 'package/manage.py':'/opt/dell/nexus/manage.py',
 'package/compose.yaml':'/opt/dell/nexus/compose.yaml',
 'package/compose.mount-gated.yaml':'/opt/dell/nexus/compose.mount-gated.yaml',
 'package/config/nginx.conf':'/opt/dell/nexus/config/nginx.conf',
 'package/application-import.py':'/opt/dell/nexus/application-import.py',
 'package/fresh-instance.json':'/opt/dell/nexus/fresh-instance.json',
 'env/nexus.env':'/etc/nexus.env',
 'unit/dell-nexus.service':'/etc/systemd/system/dell-nexus.service',
 'secret/admin-password':'/root/dell-nexus-secrets/admin-password',
 'secret/reader-password':'/root/dell-nexus-secrets/reader-password',
 'secret/publisher-password':'/root/dell-nexus-secrets/publisher-password'}


def target_json(raw):
 value=json.loads(raw)
 if value.get('expected_guest_ip')!=IP or value.get('expected_hostname')!=SOURCE_HOST:raise ValueError('source identity contract drift')
 uuid=value.get('storage',{}).get('filesystem_uuid',value.get('filesystem_uuid'))
 if uuid!=DATA_UUID:raise ValueError('source dedicated filesystem identity differs')
 value['expected_hostname']=TARGET_HOST
 return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()


def compose_ids(raw):
 result=raw
 for reference,identity in IMAGES.items():
  old=('    image: '+reference+'\n').encode();new=('    image: '+identity+'\n').encode()
  if result.count(old)!=1:raise ValueError('source immutable image selector drift')
  result=result.replace(old,new)
 return result


def transformed(files):
 if set(files)!=set(FILES):raise ValueError('exact same-instance minimal package only')
 result=dict(files)
 for key in ['package/assignment.json','package/fresh-instance.json']:result[key]=target_json(files[key])
 result['package/compose.yaml']=compose_ids(files['package/compose.yaml'])
 return result
