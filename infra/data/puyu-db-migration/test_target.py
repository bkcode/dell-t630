#!/usr/bin/python3
"""Offline contract tests for the VM210 Puyu import worker."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('puyu_target',HERE/'target-worker.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)

RUN='a'*32

def fingerprint():
    return {'version':1,'databases':{db:{'create_database':'CREATE DATABASE `'+db+'`',
            'tables':{f't{i}':{'create_table':'CREATE TABLE `t` ( `id` int ) ENGINE=InnoDB',
                               'insert_columns':['id'],'row_count':0,'row_multiset_sha256':'b'*64}
                      for i in range(count)}} for db,count in w.COUNTS.items()}}

def manifest():
    return {'version':1,'run_id':RUN,'source_sha256':'c'*64,'source_compressed_bytes':10,
            'source_expanded_bytes':20,'gzip_CRC_verified':True,
            'databases':[{'name':db,'table_count':count}for db,count in w.COUNTS.items()],
            'fingerprint':fingerprint(),'extra_source_proof':True}

class Manifest(unittest.TestCase):
    def test_accepts_manifest_with_extra_proof(self): w.validate_manifest(manifest())
    def test_rejects_wrong_db_counts_or_sha(self):
        x=manifest();x['databases'][0]['table_count']=5
        with self.assertRaises(w.Rejected):w.validate_manifest(x)
        x=manifest();x['source_sha256']='bad'
        with self.assertRaises(w.Rejected):w.validate_manifest(x)
    def test_rewrite_removes_only_two_database_if_not_exists(self):
        raw=(b'CREATE DATABASE /*!32312 IF NOT EXISTS*/ `puyu_auth_local`;\n'
             b'CREATE DATABASE IF NOT EXISTS `puyu_erp_local`;\n'
             b'INSERT INTO `x` VALUES (\'CREATE DATABASE IF NOT EXISTS text\');\n')
        out=w.rewrite_database_create(raw)
        self.assertNotIn(b'IF NOT EXISTS*/',out)
        self.assertNotIn(b'CREATE DATABASE IF NOT EXISTS `puyu_erp_local`',out)
        self.assertIn(b'CREATE DATABASE IF NOT EXISTS text',out)
    def test_rewrite_rejects_unexpected_database_shape(self):
        with self.assertRaises(w.Rejected): w.rewrite_database_create(b'CREATE DATABASE IF NOT EXISTS `puyu_auth_local`;')

class FullLifecycle(unittest.TestCase):
    def test_prepare_apply_verify_phase_order_and_no_database_drop(self):
        original={n:getattr(w,n)for n in ['BASE','guard','safe_dir','read_json','gzip_sql','module_fingerprint','collations','db_metadata','target_database_names','atom','create_importer','import_sql','cleanup_importer','root_sql','target_dump_readonly']}
        calls=[]
        class FP:
            def fingerprint(self,*_a,**_k):return fingerprint()
        with tempfile.TemporaryDirectory()as temp:
            base=Path(temp);d=base/RUN;d.mkdir();(d/'source.sql.gz').write_bytes(b'x');(d/'manifest.json').write_text(json.dumps(manifest()))
            metadata=[]
            try:
                w.BASE=base;w.guard=lambda:{'Id':'frame'};w.safe_dir=lambda *_a,**_k:None
                w.read_json=lambda p,*_a,**_k:json.loads(Path(p).read_text())
                dump=(b'CREATE DATABASE /*!32312 IF NOT EXISTS*/ `puyu_auth_local`;\n'
                      b'CREATE DATABASE /*!32312 IF NOT EXISTS*/ `puyu_erp_local`;\n')
                w.gzip_sql=lambda *_a,**_k:dump;w.module_fingerprint=lambda:FP();w.collations=lambda:{}
                w.db_metadata=lambda:list(metadata);w.target_database_names=lambda:[];w.atom=lambda p,v:Path(p).write_text(json.dumps(v))
                w.create_importer=lambda _r:(calls.append('create')or ('owned', True))
                def imported(_r,_sql):calls.append('import');metadata.extend(['puyu_auth_local\tt1','puyu_erp_local\tt1'])
                w.import_sql=imported;w.cleanup_importer=lambda _r,_u,**_kw:calls.append('cleanup')
                w.root_sql=lambda sql:'0' if 'mysql.user' in sql else 'x\tstatus\tOK'
                w.target_dump_readonly=lambda:dump
                self.assertEqual(w.prepare(RUN)['status'],'prepared-no-target-write')
                self.assertEqual(w.apply(RUN)['status'],'target-two-databases-imported-pending-verify')
                self.assertEqual(w.verify(RUN)['status'],'target-puyu-snapshot-verified')
                self.assertEqual(calls,['create','import','cleanup'])
            finally:
                for n,v in original.items():setattr(w,n,v)
    def test_collision_stops_before_import(self):
        original = w.target_database_names
        try:
            w.target_database_names=lambda:['puyu_auth_local']
            self.assertIn('puyu_auth_local', w.target_database_names())
            with self.assertRaises(w.Rejected):
                w.need(not set(w.DATABASES).intersection(w.target_database_names()), 'target-database-collision')
        finally: w.target_database_names=original

if __name__=='__main__':unittest.main()
