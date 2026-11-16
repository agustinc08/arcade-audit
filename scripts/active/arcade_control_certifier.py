#!/usr/bin/env python3
"""Human-guided physical input capture using read-only evdev events."""
import argparse,json,os,select,sys,time
from datetime import datetime,timezone
from pathlib import Path

OUT=Path('/userdata/system/state/arcade_audit/physical_control_sessions')
EXPECTED={'P1':{'usb_port':'5','event':'/dev/input/event17','js':'/dev/input/js0'},
          'P2':{'usb_port':'6','event':'/dev/input/event18','js':'/dev/input/js1'},
          'P3':{'usb_port':'8','event':'/dev/input/event20','js':'/dev/input/js3'},
          'P4':{'usb_port':'7','event':'/dev/input/event19','js':'/dev/input/js2'}}
STEPS=['ARRIBA','ABAJO','IZQUIERDA','DERECHA','B1','B2','B3','B4','B5','B6','COIN','START']
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--player',choices=EXPECTED);p.add_argument('--device',required=True)
    p.add_argument('--game',default='');p.add_argument('--system',default='');a=p.parse_args()
    try:
        from evdev import InputDevice,ecodes
    except ImportError:print('EVDEV_UNAVAILABLE');return 2
    devpath=Path(a.device)
    if not devpath.is_absolute() or not devpath.name.startswith('event') or not devpath.exists():print('INVALID_EVENT_DEVICE');return 2
    dev=InputDevice(str(devpath)); real=str(Path('/sys/class/input')/devpath.name/'device')
    try:sys_path=os.path.realpath(real)
    except OSError:sys_path='UNKNOWN'
    phys=dev.phys or ''
    expected=EXPECTED.get(a.player) if a.player else None
    verified=bool(expected and str(devpath)==expected['event'] and ('-'+expected['usb_port']+'/' in sys_path or sys_path.endswith('-'+expected['usb_port'])))
    print(json.dumps({'device':str(devpath),'name':dev.name,'vendor':dev.info.vendor,'product':dev.info.product,
                      'sysfs_path':sys_path,'player_requested':a.player,'expected_identity_match':verified,
                      'guid':'NOT_AVAILABLE_FROM_EVDEV'},ensure_ascii=False,indent=2))
    if not a.player or not verified:
        print('IDENTITY_NOT_CERTIFIED: choose the exact cabinet P1-P4 event device; no events recorded');return 3
    print('Las señales sólo registran eventos físicos observados. Confirmá que la acción pedida corresponde al control presionado.')
    recorded=[]
    try:
        for step in STEPS:
            input(f'Presioná/mové {a.player} {step}; luego Enter para empezar a escuchar... ')
            print(f'Esperando evento real para {step} (15 s)...')
            deadline=time.monotonic()+15; event=None
            while time.monotonic()<deadline:
                ready,_,_=select.select([dev.fd],[],[],min(.25,deadline-time.monotonic()))
                if not ready:continue
                for e in dev.read():
                    if e.type in (ecodes.EV_ABS,ecodes.EV_KEY) and (e.type!=ecodes.EV_KEY or e.value==1):
                        event={'type':ecodes.EV.get(e.type,str(e.type)),'code':e.code,
                               'code_name':ecodes.bytype.get(e.type,{}).get(e.code,str(e.code)),'value':e.value,
                               'observed_at':datetime.now(timezone.utc).isoformat(timespec='milliseconds')};break
                if event:break
            if not event:recorded.append({'requested_action':step,'observed':False});print('SIN EVENTO');continue
            human=input(f"Evento {event['type']} {event['code_name']} value={event['value']}. ¿Fue la acción {step}? [s/N] ").strip().lower()=='s'
            event.update({'requested_action':step,'human_confirmed':human,'observed':True});recorded.append(event)
    finally:dev.close()
    OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
    report={'system':a.system,'game':a.game,'player':a.player,'device':str(devpath),'name':dev.name,
            'sysfs_path':sys_path,'physical_event_capture':True,'human_confirmed_count':sum(x.get('human_confirmed',False) for x in recorded),
            'total_steps':len(STEPS),'result':'CONTROL_CERTIFIED_CANDIDATE' if len(recorded)==len(STEPS) and all(x.get('human_confirmed') for x in recorded) else 'MANUAL_REQUIRED',
            'control_certified':False,'note':'Candidate evidence only; owner review and in-game action confirmation required before CONTROL_CERTIFIED.',
            'recorded':recorded,'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    dest=OUT/(datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+(a.system or 'system')+'_'+(a.game or 'game')+'_'+a.player+'.json')
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.chmod(dest,0o600)
    print(json.dumps({'saved':str(dest),'result':report['result'],'control_certified':False},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
