#!/usr/bin/env python3
"""Reconcile derived certification metadata without changing individual evidence."""
import csv, hashlib, json, os, sys, tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

TOOLS=Path('/userdata/system/el_gordo_tools')
AUDIT=Path('/userdata/system/state/arcade_audit')
RUNTIME=AUDIT/'runtime/checkpoint_reconciliation_20261116T194825'
TABLE=AUDIT/'full_game_certification.csv'
STATE=AUDIT/'full_game_certification_checkpoint.json'
MASTER=AUDIT/'arcade_master_checkpoint.json'
MANIFEST=RUNTIME/'pre_reconciliation_manifest.json'
sys.path.insert(0,str(TOOLS))
import full_game_certifier as cert

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def atomic_json(path,obj):
 path=Path(path);tmp=path.with_name(path.name+'.reconcile.tmp')
 with open(tmp,'w',encoding='utf-8') as f:
  json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.chmod(tmp,0o600);os.replace(tmp,path)
 fd=os.open(str(path.parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)

def main():
 manifest=json.loads(MANIFEST.read_text());cp=json.loads(STATE.read_text());master=json.loads(MASTER.read_text())
 rows,fields=cert.load_rows();results=cp.get('results',[])
 if sha(TABLE)!=manifest['csv_sha256_before'] or sha(STATE)!=manifest['full_game_certification_checkpoint_sha256_before'] or sha(MASTER)!=manifest['arcade_master_checkpoint_sha256_before']:
  raise RuntimeError('RECONCILIATION_SOURCE_CHANGED_SINCE_SNAPSHOT')
 if not all(manifest.get('invariants',{}).values()):raise RuntimeError('PRE_RECONCILIATION_INVARIANT_FAILED')
 counts=Counter(x.get('result','UNKNOWN') for x in results)
 txids=[x.get('transaction_id') for x in results if x.get('transaction_id')]
 if len(txids)!=len(set(txids)):raise RuntimeError('DUPLICATE_TRANSACTION_ID')
 keys={(x.get('system'),x.get('rom')) for x in results}
 if len(keys)!=510 or len(results)!=511 or counts != Counter({'AUTO_PASS':499,'GAME_FAIL':9,'STATIC_FAIL':2,'ENGINE_FAIL':1}):
  raise RuntimeError('RESULT_EVIDENCE_COUNTS_CHANGED')
 if len(txids)!=509:raise RuntimeError('TRANSACTION_COUNT_CHANGED')
 if any(x.get('restore',{}).get('status') not in ('RESTORE_VERIFIED','NOT_REQUIRED_NO_WRITE') for x in results if x.get('transaction_id')):
  raise RuntimeError('RESTORE_INVARIANT_FAILED')
 if sum(x.get('restore',{}).get('status')=='RESTORE_VERIFIED' for x in results)!=509:raise RuntimeError('RESTORE_VERIFIED_COUNT_CHANGED')
 row_map={(r['system'],r['rom']):r for r in rows}
 if len(row_map)!=len(rows):raise RuntimeError('CSV_IDENTITY_COLLISION')
 if not keys.issubset(row_map):raise RuntimeError('RESULT_WITHOUT_CSV_ROW')
 latest={}
 for item in results:latest[(item.get('system'),item.get('rom'))]=item
 for key,item in latest.items():
  row=row_map[key];state=item.get('result');actual=row.get('auto_certification')
  expected={'AUTO_PASS':'AUTO_CERTIFIED','GAME_FAIL':'GAME_FAIL','STATIC_FAIL':'STATIC_FAIL','FLAKY':'FLAKY'}.get(state)
  if expected and actual!=expected:raise RuntimeError('RESULT_CSV_MISMATCH:'+key[0]+':'+Path(key[1]).name)
  if item.get('transaction_id') and row.get('test_id')!=item.get('transaction_id'):
   # STATIC_FAIL preflight rows may be recorded without a transaction and an old static
   # identity may have no transaction id; only compare when table points at a tx.
   raise RuntimeError('RESULT_CSV_TEST_ID_MISMATCH:'+key[0]+':'+Path(key[1]).name)
 csv_counts={
  'auto_certified':sum(r.get('auto_certification')=='AUTO_CERTIFIED' for r in rows),
  'game_fail':sum(r.get('auto_certification')=='GAME_FAIL' for r in rows),
  'static_fail':sum(r.get('auto_certification')=='STATIC_FAIL' for r in rows),
  'flaky':sum(r.get('auto_certification')=='FLAKY' for r in rows),
  'needs_repair':sum(r.get('lifecycle_state')=='NEEDS_REPAIR' for r in rows),
  'control_certified':sum(r.get('control_certification')=='CONTROL_CERTIFIED' for r in rows),
  'guest_ready':sum(r.get('guest_ready')=='YES' for r in rows)}
 systems=cert.ad.live_systems();queue=cert.queue(rows,systems)
 eligible=[]
 for item in queue[:20]:
  key=(item['system'],item['rom']);row=row_map[key]
  if row.get('installed')!='YES' or row.get('auto_certification') not in ('NOT_TESTED','') or key in keys:
   raise RuntimeError('QUEUE_PREVIEW_INELIGIBLE:'+key[0]+':'+Path(key[1]).name)
  info=item['adapter_info']
  if info.get('adapter_status')!='READY':raise RuntimeError('QUEUE_ADAPTER_NOT_READY')
  pf=cert.ad.preflight(item['system'],item['rom'],info['adapter'],info['core'])
  if pf.get('status')!='PASS':raise RuntimeError('QUEUE_PREFLIGHT_FAIL:'+key[0]+':'+Path(key[1]).name+':'+str(pf.get('reason')))
  eligible.append(item)
 if len(eligible)<20:raise RuntimeError('QUEUE_PREVIEW_TOO_SHORT')
 next_game=f"{eligible[0]['system']}:{eligible[0]['rom']}"
 if cp.get('next_untested')==next_game:raise RuntimeError('CURSOR_DID_NOT_ADVANCE')
 if cp.get('latest_batch',{}).get('name')!='priority_batch_5':raise RuntimeError('LATEST_BATCH_UNEXPECTED')
 # Batch 6 is the exact appended tail compared with the prior checkpoint: 100
 # result entries, with two existing static preflight records outside that delta.
 delta=results[-100:]
 delta_counts=Counter(x.get('result') for x in delta)
 if delta_counts!=Counter({'AUTO_PASS':98,'GAME_FAIL':2}):raise RuntimeError('BATCH6_RESULT_DELTA_MISMATCH')
 prior_static=[x for x in results[:-100] if x.get('result')=='STATIC_FAIL']
 if len(prior_static)!=2:raise RuntimeError('BATCH6_STATIC_FAIL_WAS_NOT_PREEXISTING')
 # The CSV is evidence; reconciliation only updates derived metadata.
 if sha(TABLE)!=manifest['csv_sha256_before']:raise RuntimeError('CSV_CHANGED_DURING_RECONCILIATION')
 before_checkpoint=sha(STATE);before_master=sha(MASTER)
 cp['attempted_new']=len(txids) # legacy field: transactions, not unique games/results
 cp['launch_transactions']=len(txids);cp['transaction_attempts']=len(txids)
 cp['retry_transactions']=len(txids)-len({(x.get('system'),x.get('rom')) for x in results if x.get('transaction_id')})
 cp['unique_games_processed']=len(keys);cp['result_records']=len(results)
 cp['static_preflight_results']=counts['STATIC_FAIL']
 cp['engine_fail_total_historical']=counts['ENGINE_FAIL']
 cp['engine_fail_active']=sum(x.get('result') in cert.STOP_ENGINE for x in latest.values())
 cp.update(csv_counts)
 cp['counts']={k:counts.get(k,0) for k in ('AUTO_PASS','GAME_FAIL','STATIC_FAIL','FLAKY','ADAPTER_NOT_READY','ENGINE_FAIL','WRONG_GAME_DISPATCH','AUDIO_ROUTE_CHANGED','RESTORE_FAILURE')}
 cp['restores_verified']=509;cp['restore_failures']=0
 cp['latest_batch']={'name':'priority_batch_6','considered':100,'launched':100,'auto_pass':98,'game_fail':2,'static_fail':0,'flaky':0,
  'restore_verified':'100/100','restore_failures':0,'engine_failures_unresolved':0,'audio_route_changed':0,'wrong_game_dispatch':0,
  'started_at':'2026-11-16T16:58:30-03:00','finished_at':'2026-11-16T18:29:06-03:00',
  'first_game':'/userdata/roms/mame/gundealr.zip','last_game':'/userdata/roms/mame/machbrkr.zip','next_game':next_game,
  'note':'100 new result records: 98 AUTO_PASS and 2 GAME_FAIL. The two STATIC_FAIL records predated Batch 6.'}
 cp['next_untested']=next_game;cp['next_game']=None;cp['status']='COMPLETE';cp['selected_count']=100
 cp['updated_at']=datetime.now(timezone.utc).isoformat(timespec='seconds')
 phase=master['phases']['PHASE_14_FULL_GAME_CERTIFICATION']
 phase['summary']=(f"Piloto 10 juegos únicos AUTO_PASS/11 intentos; Batch 1: 49/50 AUTO_PASS, 1 GAME_FAIL; "
  f"Batch 2: 49 AUTO_PASS y 1 STATIC_FAIL; Batch 3: 99/100 AUTO_PASS, 1 GAME_FAIL; "
  f"Batch 4: 96/100 AUTO_PASS, 4 GAME_FAIL; Batch 5: 98 AUTO_PASS, 1 GAME_FAIL, 1 STATIC_FAIL; "
  f"Batch 6: 98 AUTO_PASS y 2 GAME_FAIL de 100 lanzamientos, 100/100 restores. "
  f"Acumulado: AUTO_CERTIFIED={csv_counts['auto_certified']}, GAME_FAIL={csv_counts['game_fail']}, "
  f"STATIC_FAIL={csv_counts['static_fail']}, transactions={len(txids)}, unique_games_processed={len(keys)}, "
  f"CONTROL_CERTIFIED={csv_counts['control_certified']}, GUEST_READY={csv_counts['guest_ready']}, NEXT_GAME={next_game}.")
 phase['updated_at']=cp['updated_at']
 master['certification_counts']={**master.get('certification_counts',{}),**csv_counts,'attempted_new':len(txids),
  'unique_games_processed':len(keys),'result_records':len(results),'launch_transactions':len(txids),'retry_transactions':cp['retry_transactions'],
  'total_restores':509,'restore_failures':0,'next_game':next_game,'engine_failures_unresolved':cp['engine_fail_active']}
 master['updated_at']=cp['updated_at']
 preview=RUNTIME/'NEXT_QUEUE_PREVIEW.csv'
 if not preview.is_file():raise RuntimeError('QUEUE_PREVIEW_FILE_MISSING')
 atomic_json(STATE,cp);atomic_json(MASTER,master)
 after_checkpoint=sha(STATE);after_master=sha(MASTER)
 report={
  'result_records':len(results),'unique_games_processed':len(keys),'launch_transactions':len(txids),'retry_transactions':cp['retry_transactions'],
  'auto_certified':csv_counts['auto_certified'],'game_fail':csv_counts['game_fail'],'static_fail':csv_counts['static_fail'],
  'flaky':csv_counts['flaky'],'needs_repair':csv_counts['needs_repair'],'restores_verified':509,'restore_failures':0,
  'active_engine_failures':cp['engine_fail_active'],'latest_batch':'priority_batch_6','old_next_game':'mame:/userdata/roms/mame/gundealr.zip',
  'next_game':next_game,'csv_sha256_before':manifest['csv_sha256_before'],'csv_sha256_after':sha(TABLE),
  'checkpoint_sha256_before':before_checkpoint,'checkpoint_sha256_after':after_checkpoint,
  'master_checkpoint_sha256_before':before_master,'master_checkpoint_sha256_after':after_master,
  'historical_engine_failures':cp['engine_fail_total_historical'],'batch6_delta':dict(delta_counts),
  'preexisting_static_fail_records':len(prior_static),'queue_preview_rows':len(eligible)}
 (RUNTIME/'reconciliation_result.json').write_text(json.dumps(report,indent=2)+'\n')
 print('CERTIFICATION_RECONCILIATION_PASS')
 print(json.dumps(report,indent=2))

if __name__=='__main__':
 try:main()
 except Exception as e:
  print('CERTIFICATION_RECONCILIATION_FAIL')
  print(type(e).__name__+': '+str(e))
  raise SystemExit(2)
