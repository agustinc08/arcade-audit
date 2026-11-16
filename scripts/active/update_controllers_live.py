#!/usr/bin/env python3
"""Read-only snapshot of arcade panel identities and currently connected SDL pads."""
import json,subprocess,sys,os
from datetime import datetime,timezone
from pathlib import Path
OUT=Path('/userdata/system/state/arcade_audit/controllers_live.json')
DISPATCHER=Path('/userdata/system/el_gordo_tools/controller_dispatcher')
def main():
    try:
        raw=subprocess.run([str(DISPATCHER),'--diagnose'],capture_output=True,text=True,timeout=12,check=True).stdout
        d=json.loads(raw)
    except Exception as e:
        print('CONTROLLER_DIAGNOSE_FAILED',type(e).__name__);return 2
    try:
        pactl=subprocess.run(['pactl','list','short','sinks'],capture_output=True,text=True,timeout=5).stdout
    except Exception:pactl=''
    audio_names=[line.split('\t')[1] for line in pactl.splitlines() if len(line.split('\t'))>1]
    arcade=d.get('profiles',{}).get('arcade',{}).get('players',[])
    assigned={x.get('path'):x for x in arcade if x.get('arcade_player')}
    pads=[]; panels=[]
    for x in d.get('natural',[]):
        path=x.get('path',''); assignment=assigned.get(path)
        sysfs=os.path.realpath('/sys/class/input/'+Path(path).name+'/device') if path else ''
        if assignment: transport='USB'
        elif '/usb' in sysfs: transport='USB'
        elif '/bluetooth' in sysfs or x.get('guid','').startswith('030000004c05'): transport='Bluetooth'
        else: transport='UNKNOWN'
        item={'name':x.get('name','').strip(),'guid':x.get('guid'),'event_path':path,
              'sdl_index':x.get('index'),'transport':transport,
              'battery':'UNKNOWN','audio_capability':any(z in ' '.join(audio_names).lower() for z in ('wireless_controller','dualshock','dualsense')) and ('sony' in x.get('name','').lower()),
              'connected':True}
        if assignment:
            item.update({'player':assignment.get('arcade_player'),'usb_port':assignment.get('usb_port')});panels.append(item)
        else:pads.append(item)
    payload={'updated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'source':'controller_dispatcher --diagnose; SDL runtime; pactl sink names',
             'BOTONERA_P1_P4':sorted(panels,key=lambda x:x.get('player','')),
             'GAMEPADS_CONNECTED':pads,
             'audio_default_sink_identity':'see current WirePlumber/pactl state; device capability only, not certification',
             'mapping_modified':False}
    OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,OUT)
    print(json.dumps({'panels':len(panels),'external_gamepads':len(pads),'saved':str(OUT)},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
