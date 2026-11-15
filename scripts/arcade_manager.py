#!/usr/bin/env python3
"""Read-only, request-driven local Arcade Manager (no action routes or background poller)."""
import argparse,csv,json,subprocess,urllib.request
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
ROOT=Path('/userdata/system/state/arcade_audit')
HTML='''<!doctype html><meta charset="utf-8"><title>Arcade Manager</title><style>body{font:18px system-ui;background:#101722;color:#edf2f7;margin:3rem}input{font:inherit;padding:.6rem;width:24rem}pre{white-space:pre-wrap}a{color:#8fd3ff}</style><h1>ARCADE MANAGER</h1><p>Panel read-only. No hay acciones remotas.</p><div id="status">Cargando…</div><input id="q" placeholder="Buscar juego"><button onclick="search()">Buscar</button><pre id="games"></pre><script>async function load(){let r=await fetch('/api/status');document.querySelector('#status').textContent=JSON.stringify(await r.json(),null,2)}async function search(){let q=document.querySelector('#q').value;let r=await fetch('/api/games?q='+encodeURIComponent(q));document.querySelector('#games').textContent=JSON.stringify(await r.json(),null,2)}load()</script>'''
def safe_status():
    x={'online':True,'sampled_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'read_only':True}
    try:
        with urllib.request.urlopen('http://127.0.0.1:1234/isIdle',timeout=1) as r:x['es_idle']=json.load(r)
        with urllib.request.urlopen('http://127.0.0.1:1234/runningGame',timeout=1) as r:x['running_game']=json.load(r)
    except Exception:x['es_api']='OFFLINE_OR_UNAVAILABLE'
    cp=ROOT/'arcade_master_checkpoint.json'
    if cp.is_file():
        d=json.loads(cp.read_text());x['master_phases']={k:v.get('status') for k,v in d.get('phases',{}).items()}
        x['global_mame_core']=d.get('baseline',{}).get('global_mame_core')
    ctrl=ROOT/'controllers_live.json'
    if ctrl.is_file():x['controllers']=json.loads(ctrl.read_text())
    issues=ROOT/'arcade_issues.csv'
    if issues.is_file():
        with issues.open(encoding='utf-8-sig',newline='') as f:x['open_issues']=[{'id':r['id'],'severity':r['severity'],'status':r['status'],'category':r['category']} for r in csv.DictReader(f) if r.get('status') in ('OPEN','BLOCKED','MANUAL_REQUIRED')]
    return x
def games(q,limit=50):
    p=ROOT/'full_game_certification.csv';needle=q.casefold();out=[]
    if not p.is_file():return out
    with p.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if needle and needle not in (r['name']+' '+r['system']+' '+r['rom']).casefold():continue
            out.append({k:r.get(k,'') for k in ('system','rom','name','installed','boot_status','boot_core','auto_certification','control_mode','recommended_control','control_certification','players_metadata','guest_ready','issue')})
            if len(out)>=limit:break
    return out
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=='/':body=HTML.encode();typ='text/html; charset=utf-8'
        elif u.path=='/api/status':body=json.dumps(safe_status(),ensure_ascii=False).encode();typ='application/json; charset=utf-8'
        elif u.path=='/api/games':body=json.dumps(games(parse_qs(u.query).get('q',[''])[0]),ensure_ascii=False).encode();typ='application/json; charset=utf-8'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def do_POST(self):self.send_error(405)
    def log_message(self,fmt,*args):pass
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765);a=p.parse_args()
    if not 1024<=a.port<=65535:raise SystemExit('PORT_OUT_OF_RANGE')
    print(json.dumps({'bind':a.host,'port':a.port,'read_only':True,'actions':'none','autostart':'none'}))
    ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
if __name__=='__main__':main()
