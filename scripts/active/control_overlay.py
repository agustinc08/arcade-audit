#!/usr/bin/env python3
"""Render truthful pre-launch control metadata; never invent action labels."""
import argparse,csv,json
from pathlib import Path
TABLE=Path('/userdata/system/state/arcade_audit/game_certification.csv')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('system');p.add_argument('rom');a=p.parse_args()
 with TABLE.open(encoding='utf-8-sig',newline='') as f:
  row=next((x for x in csv.DictReader(f) if x.get('system')==a.system and Path(x.get('rom','')).name.lower()==Path(a.rom).name.lower()),None)
 if not row:print(json.dumps({'found':False,'message':'Control data not certified'}));return 1
 result={'found':True,'name':row.get('name',''),'system':a.system,'players_metadata':row.get('players_metadata','UNKNOWN'),
         'control_mode':row.get('control_mode','UNKNOWN'),'recommended_control':row.get('control_mode','UNKNOWN'),
         'control_certification':row.get('control_certification','NOT_TESTED'),
         'buttons':{},'note':'Button labels shown only when a human-certified mapping exists.'}
 if row.get('control_certification')=='CONTROL_CERTIFIED':
  for key in ('button1','button2','button3','button4','button5','button6'):
   if row.get(key) and row[key] not in ('NOT_TESTED',''):result['buttons'][key.upper()]=row[key]
 print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
