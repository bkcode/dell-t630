import unittest,json
from unittest.mock import patch
from types import SimpleNamespace
import worker
class VhostNormalizationTests(unittest.TestCase):
 def test_only_redundant_fields_and_empty_limits_normalized(self):
  source={'name':'fixture','description':'reviewed','tags':['acceptance'],'metadata':{'description':'reviewed','tags':['acceptance']}}
  restored={'name':'fixture','limits':[],'metadata':{'description':'reviewed','tags':['acceptance']}}
  self.assertEqual(worker.normalize_vhost(source),worker.normalize_vhost(restored))
 def test_changed_or_inconsistent_metadata_not_ignored(self):
  with self.assertRaises(worker.Rejected):worker.normalize_vhost({'name':'fixture','description':'changed','metadata':{'description':'original'}})
  self.assertNotEqual(worker.normalize_vhost({'name':'fixture','metadata':{},'limits':{'max-queues':1}}),worker.normalize_vhost({'name':'fixture','metadata':{},'limits':[]}))
 def test_unknown_field_rejected(self):
  with self.assertRaises(worker.Rejected):worker.normalize_vhost({'name':'fixture','future-security-field':'unknown'})
class InternalParameterTests(unittest.TestCase):
 def query(self,expected_value,actual_value):
  expected={'global_parameters':[{'name':'internal_cluster_id','value':expected_value}]}
  responses=[SimpleNamespace(stdout=b''),SimpleNamespace(stdout=b'{"global_parameters":[]}'),SimpleNamespace(stdout=json.dumps([{'name':'internal_cluster_id','value':json.dumps(actual_value)}]).encode())]
  with patch.object(worker,'docker',side_effect=responses):return worker.rabbit_export('isolated-fixture',expected)
 def test_filtered_identity_privately_compared(self):
  self.assertEqual(self.query('synthetic-identity','synthetic-identity')['global_parameters'],[{'name':'internal_cluster_id','value':'synthetic-identity'}])
 def test_actual_identity_mismatch_rejected(self):
  with self.assertRaises(worker.Rejected):self.query('synthetic-original','synthetic-different')
if __name__=='__main__':unittest.main()
