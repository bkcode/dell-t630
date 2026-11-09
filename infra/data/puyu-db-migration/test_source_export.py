import gzip,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
s=importlib.util.spec_from_file_location('exporter',Path(__file__).with_name('source-export.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class SourceExportTests(unittest.TestCase):
 def fixture(self):
  return {'schemas':[[db,'utf8mb4','utf8mb4_0900_ai_ci'] for db in m.DATABASES],'tables':[[db,'t','BASE TABLE','InnoDB','utf8mb4_0900_ai_ci'] for db in m.DATABASES],'columns':[],'indexes':[[db,'t','PRIMARY'] for db in m.DATABASES],'object_counts':{'routines':0,'triggers':0,'events':0}}
 def test_fixed_flags_no_incompatible_connect_timeout_no_skip_charset(self):
  self.assertEqual(m.DUMP_FLAGS,['--single-transaction','--order-by-primary','--skip-extended-insert','--complete-insert','--hex-blob','--skip-comments','--skip-dump-date','--no-tablespaces','--set-gtid-purged=OFF','--default-character-set=utf8mb4','--tz-utc','--databases','puyu_auth_local','puyu_erp_local'])
  self.assertNotIn('--skip-set-charset',m.DUMP_FLAGS)
 def test_schema_PK_engine_and_objects_gates(self):
  m.validate_metadata(self.fixture())
  for field,value in [('schemas',[]),('indexes',[]),('object_counts',{'events':1})]:
   item=self.fixture();item[field]=value
   with self.assertRaises(m.Rejected):m.validate_metadata(item)
  for typ,eng in [('VIEW',''),('BASE TABLE','MyISAM')]:
   item=self.fixture();item['tables'][0][2:4]=[typ,eng]
   with self.assertRaises(m.Rejected):m.validate_metadata(item)
 def test_compressed_cap_rejects_before_overwrite(self):
  raw=io.BytesIO();limited=m.CompressedBound(raw)
  with patch.object(m,'MAX_COMPRESSED',4):
   limited.write(b'1234')
   with self.assertRaises(m.Rejected):limited.write(b'5')
  self.assertEqual(raw.getvalue(),b'1234')
 def test_gzip_integrity_uses_private_hash_only_and_detects_bad_CRC(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'source.sql.gz';p.write_bytes(gzip.compress(b'-- synthetic nonbusiness SQL\n'))
   digest,count=m.verify_gzip(p);self.assertEqual(count,29);self.assertEqual(len(digest),64)
   raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
   with self.assertRaises((OSError,EOFError)):m.verify_gzip(p)
 def test_release_normal_needs_marker_and_independent_session_count_zero(self):
  lock=m.BackupLock();lock.connection_id=123;lock.process=Mock();lock.process.poll.return_value=None;lock.process.stdin.closed=False
  with patch.object(lock,'_send') as send,patch.object(lock,'_expect',return_value='release'),patch.object(m,'independent_release_counts',return_value={'owned_lock_connection_count':0,'owned_backup_lock_count':0}):
   proof=lock.release()
  self.assertTrue(proof['UNLOCK_marker_acknowledged']);self.assertFalse(proof['owned_connection_KILL_fallback_used']);self.assertIn('UNLOCK INSTANCE',send.call_args.args[0])
 def test_only_owned_session_killed_when_unlock_not_acknowledged(self):
  lock=m.BackupLock();lock.connection_id=123;lock.process=Mock();lock.process.poll.return_value=None;lock.process.stdin.closed=False
  counts=[{'owned_lock_connection_count':1,'owned_backup_lock_count':1},{'owned_lock_connection_count':0,'owned_backup_lock_count':0}]
  with patch.object(lock,'_send',side_effect=BrokenPipeError),patch.object(m,'independent_release_counts',side_effect=counts),patch.object(m,'query',return_value=(0,'')) as query:
   proof=lock.release()
  self.assertTrue(proof['owned_connection_KILL_fallback_used']);self.assertEqual(query.call_args.args[0],'KILL CONNECTION 123;')
 def test_proof_query_failure_still_disposes_CLI(self):
  lock=m.BackupLock();lock.connection_id=123;lock.process=Mock();lock.process.poll.return_value=None;lock.process.stdin.closed=False
  with patch.object(lock,'_send',side_effect=BrokenPipeError),patch.object(m,'independent_release_counts',side_effect=m.Rejected('query-failed')):
   with self.assertRaises(m.Rejected):lock.release()
  lock.process.terminate.assert_called_once()
 def test_no_handshake_never_sent_lock_no_unowned_KILL(self):
  lock=m.BackupLock();lock.process=Mock();lock.process.poll.return_value=1
  with patch.object(m,'query') as query:proof=lock.release()
  query.assert_not_called();self.assertTrue(proof['no_LOCK_command_sent'])
 def test_owned_dump_probe_cannot_kill_reused_PID(self):
  with patch.object(m.subprocess,'run',return_value=Mock(returncode=91)) as run:
   with self.assertRaises(m.Rejected):m.dispose_dump_process(100,200)
  self.assertEqual(run.call_count,1)
 def test_shellsyntax_and_no_reconnect_lock(self):
  self.assertEqual(subprocess.run(['sh','-n','-c',m.DUMP],capture_output=True).returncode,0)
  self.assertIn('DUMP_PID:',m.DUMP);self.assertIn('exec mysqldump',m.DUMP)

if __name__=='__main__':unittest.main()
