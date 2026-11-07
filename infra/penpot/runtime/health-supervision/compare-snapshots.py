#!/usr/bin/env python3
"""Local metadata-only comparison; no credentials or target calls."""
import argparse,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--expect-new-boot',action='store_true');a=p.parse_args()
before=json.loads((HERE/'evidence/before-install.json').read_text())['result'];after=json.loads((HERE/'evidence'/(a.phase+'.json')).read_text())['result'];media=json.loads((HERE/'evidence/media-extra-attribution.json').read_text())['result']
checks={'worker_import_idle':after['worker_idle'],'original_three_file_stats_revn_and_full_data_hash_unchanged':before['original_files']==after['original_files'],'all_973_current_media_paths_and_bytes_unchanged':before['media_path_to_sha256']==after['media_path_to_sha256'],'all_original_971_media_SHA_present':set(media['expected_media_sha256'])<=set(after['media_path_to_sha256'].values()),'new_identity_and_assignment_file_hashes_unchanged':before['identity_hashes']==after['identity_hashes'],'Git_same_clean_ff1783e':before['Git_HEAD']==after['Git_HEAD']=='ff1783e7865af7aae571c985f03e057631b7af63' and after['Git_dirty']=='','old_base_unit_bytes_unchanged':before['unit_sha256']==after['unit_sha256'],'all_11_running_healthy':len(after['containers'])==11 and all(c['running'] and c['health']=='healthy' for c in after['containers'].values())}
checks['boot_id_changed' if a.expect_new_boot else 'boot_id_unchanged']=before['boot_id']!=after['boot_id'] if a.expect_new_boot else before['boot_id']==after['boot_id']
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'source_original_media':971,'current_media_baseline':973,'media_files_after':after['media_files'],'original_designs':3,'design_writes':0,'secret_values_emitted':False}
(HERE/'evidence'/(a.phase+'-comparison.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(0 if report['status']=='passed' else 1)
