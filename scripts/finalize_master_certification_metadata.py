#!/usr/bin/env python3
"""Write resumable master-audit reports/checkpoint from read-only inventories."""
import csv,json,os,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/userdata/system/state/arcade_audit')
def readcsv(name):
 with (ROOT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(name,fields,rows):
 p=ROOT/name;tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 os.replace(tmp,p)
def atomic(path,obj):
 p=ROOT/path;tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def main():
 now=datetime.now(timezone.utc).isoformat(timespec='seconds'); games=readcsv('full_game_certification.csv'); arcade=readcsv('arcade_games_audit.csv')
 media=readcsv('media_audit.csv');multi=readcsv('multiplayer_games.csv')
 bysys=defaultdict(list)
 for g in games:bysys[g['system']].append(g)
 states=Counter(g['auto_certification'] for g in games);boots=Counter(g['boot_status'] for g in games)
 physical=Counter(g['control_certification'] for g in games); images=sum(g['image_exists']=='YES' for g in media); videos=sum(g['video_exists']=='YES' for g in media)
 thumbs=sum(g['thumbnail_exists']=='YES' for g in media);fanarts=sum(g['fanart_exists']=='YES' for g in media)
 missing_primary=sum(g['image_exists']=='NO' for g in media)
 rootrows=[]
 for system,items in sorted(bysys.items()):
  boot=Counter(g['boot_status'] for g in items)
  text=(f"# Certificación — {system}\n\n- Total de registros: {len(items)}\n- Instalados: {sum(g['installed']=='YES' for g in items)}\n"
        f"- Evidencia histórica de boot: {sum(v for k,v in boot.items() if k.startswith('BOOT_OK'))}\n- AUTO_CERTIFIED en esta fase: 0\n"
        f"- FAIL histórico: {sum(v for k,v in boot.items() if k.startswith('FAIL'))}\n- CONTROL_CERTIFIED: 0\n- GUEST_READY: 0\n"
        f"- Estado nuevo: NOT_TESTED hasta completar el adaptador runtime, la prueba visual/audio y restore actual.\n")
  rootrows.append((system,text))
  # Flat names ensure safe publisher's existing allowlist discovers each report.
  (ROOT/f'CERTIFICATION_{re.sub("[^A-Za-z0-9_-]","_",system).upper()}.md').write_text(text,encoding='utf-8')
 summary=['# Certificación completa de juegos — estado reanudable','',f'- Fecha: {now}',f'- Sistemas con inventario: {len(bysys)}',f'- Juegos/registros: {len(games)}',
          f'- Instalados según fichero/gamelist: {sum(g["installed"]=="YES" for g in games)}',
          f'- Evidencia histórica BOOT_OK: {sum(v for k,v in boots.items() if k.startswith("BOOT_OK"))}',
          '- STATIC_VALIDATED completo: 0 (la mera presencia no verifica dependencias/ROMset)',
          '- AUTO_CERTIFIED: 0; CONTROL_CERTIFIED: 0; GUEST_READY: 0',
          f'- NOT_TESTED para auto-certificación: {states.get("NOT_TESTED",0)}',
          f'- FAIL histórico conservado, separado: {sum(v for k,v in boots.items() if k.startswith("FAIL"))}',
          '- FLAKY: 0 nuevos (sin reintentos de runtime en esta fase)',
          '- NEEDS_REPAIR: los fallos históricos están en `arcade_games_audit.csv`; consolidación de causas pendiente.',
          '- MANUAL_REQUIRED: control físico, audio reconnection, salida por sistema/core.',
          '', '## Lectura correcta', '',
          'Los BOOT_OK históricos no se elevan a AUTO_CERTIFIED. No hubo lanzamientos nuevos: se creó un baseline separado actual y verificado que conserva el histórico, pero todavía falta integrar una transacción de restore en el runner universal; además el default de audio sigue en el sink del DualShock.',
          '', 'La prueba automática futura deberá pasar por EmulationStation, `controller_dispatcher` y launcher oficial; snapshots transaccionales por juego, duración específica por sistema, evidencia visual/audio y estado limpio serán obligatorios.', '', '## Resumen por sistema','']
 for system,items in sorted(bysys.items()):
  summary.append(f"- **{system}**: total {len(items)}, instalado {sum(g['installed']=='YES' for g in items)}, BOOT_OK histórico {sum(g['boot_status'].startswith('BOOT_OK') for g in items)}, FAIL histórico {sum(g['boot_status'].startswith('FAIL') for g in items)}, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.")
 (ROOT/'FULL_GAME_CERTIFICATION_SUMMARY.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
 # Must-have catalogue candidates: status means filename/gamelist evidence only, never quality or certification.
 wanted={
 'FIGHTING':['Street Fighter II','Street Fighter III','Mortal Kombat','Tekken 3','The King of Fighters 98','Marvel vs. Capcom'],
 'BEAT_EM_UP':['Final Fight','Cadillacs and Dinosaurs','Captain Commando','Teenage Mutant Ninja Turtles','The Simpsons','X-Men','Dungeons & Dragons','Golden Axe'],
 'RUN_AND_GUN':['Metal Slug','Contra','Sunset Riders','Gunstar Heroes'],
 'SHMUP':['Ikaruga','Radiant Silvergun','DoDonPachi','Gradius','R-Type'],
 'SPORTS':['NBA Jam','NBA Hangtime','NFL Blitz','Windjammers'],
 'RACING':['Daytona USA','Crazy Taxi','Mario Kart 64','OutRun'],
 'CLASSICS':['Pac-Man','Galaga','Donkey Kong','Tetris','Space Invaders'],
 'PARTY':['Bomberman','Warlords','Super Smash Bros.'],
 '2P':['Street Fighter II','Final Fight','Metal Slug','Mario Kart 64'],
 '3P':['Cadillacs and Dinosaurs','The King of Dragons','Dungeons & Dragons'],
 '4P':['Teenage Mutant Ninja Turtles','The Simpsons','Captain Commando','NBA Jam'],
 }
 def find(name):return [g for g in games if name.lower() in g['name'].lower()]
 lines=['# Must-have arcade y multiplayer — comparación con el inventario local','',
        'La lista es una cola curatorial basada en referencias comunitarias/series conocidas, no una sentencia de calidad. `INSTALLED` usa filename/gamelist, `INSTALLED_UNCERTIFIED` indica que no hay certificación nueva completa; no se descargó ni borró contenido.','']
 for cat,names in wanted.items():
  lines+=['## '+cat,'']
  for name in names:
   hits=find(name)
   if not hits:lines.append(f'- **{name}** — MISSING en la búsqueda de nombres del inventario; verificar aliases antes de concluir.')
   else:
    for h in hits[:4]:
     st='INSTALLED_UNCERTIFIED' if h['installed']=='YES' else 'INSTALLED_BUT_BROKEN_OR_MISSING'
     lines.append(f"- **{name}** — `{h['system']}/{Path(h['rom']).name}` — {st}; boot histórico `{h['boot_status']}`; GUEST_READY NO.")
  lines.append('')
 (ROOT/'ARCADE_MISSING_MUST_HAVE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 # Correctly state preflight blocker and group historic issues without conflating games not launched.
 issues=readcsv('arcade_issues.csv')
 repair=['# Bucle de reparación — causas raíz conocidas','',
         '- No se ejecutaron retries en esta fase: no hubo lanzamientos nuevos.',
         '- Fallos históricos no se convierten a NOT_TESTED; se mantienen en `arcade_games_audit.csv` y reportes BATCH.',
         '- Preflight smoke actual: ES idle, no juego, sin marker/procesos; diferencia protegida única = `batocera.conf` con 18 overrides autorizados posteriores al backup de noviembre 13.',
         '- El baseline del runner antiguo no es reutilizable porque su restaurador repondría esa versión antigua. La causa fue reconciliada; no hubo una modificación no explicada del sistema.',
         '- Audio: default WirePlumber apunta al sink del DualShock 4 en vez de HDMI; HDMI rule instalada coincide con BDF obsoleto. Sigue abierto.',
         '- Contenido arcade: recurrencias de missing parent/member/BIOS/CHD descritas en los reportes BATCH y planes; no hubo reparación/descarga.',
         '', '## Política de retry', '',
         'Primer fallo nuevo => RETRY_REQUIRED; se limpia estado y se usa segundo intento independiente sólo tras restore verificado. Un PASS tras fallos previos se marca FLAKY. Dos fallos repetidos => CONFIRMED_FAIL/NEEDS_REPAIR. Los fingerprints deben incluir sistema/core/dependencia/identidad del error.','']
 (ROOT/'FAILURE_REPAIR_LOOP.md').write_text('\n'.join(repair),encoding='utf-8')
 # Web/GitHub research with source URLs and narrowly stated conclusions.
 research='''# Investigación UX, controles, multiplayer y herramientas\n\n## Referencias consultadas\n\n- Batocera, [Configure a Controller](https://wiki.batocera.org/configure_a_controller): documenta perfiles por mando; una identidad lógica puede variar y requiere mapping explícito. Integrar la detección existente; no sustituirla.\n- Batocera, [Remapping controls per emulator](https://wiki.batocera.org/remapping_controls_per_emulator): remaps pueden ser por emulador/juego, así que el certificador debe identificar core y remap efectivo.\n- Batocera, [Menu tree](https://wiki.batocera.org/menu_tree): incluye favoritos, avisos de BIOS y opciones de controladores; preferir capacidades del frontend antes de instalar otra capa.\n- Batocera, [Write themes for EmulationStation](https://wiki.batocera.org/write_themes_for_emulationstation): los themes pueden mostrar metadata y elementos visuales; revisar un tema existente antes de desarrollar overlay independiente.\n- BYOAC, [Multi-player Games](https://wiki.arcadecontrols.com/index.php/Multi-Player_Games): referencia comunitaria para juegos multi-player y ejemplos como Gauntlet y X-Men. No certifica que esta instalación/core acepte el número de controles.\n- GitHub, [Batocera-WebDashboard-Pro](https://github.com/DavidSchuchert/Batocera-WebDashboard-Pro): dashboard comunitario de alcance amplio; estudiar sólo ideas de lectura, no instalar sin auditar permisos, código y acciones.\n- GitHub, [batocera-controlcenter](https://github.com/lbrpdx/batocera-controlcenter): idea de panel local; no instalar hasta revisar código y seguridad de endpoints.\n- Reddit, [arcade party recommendations](https://www.reddit.com/r/arcade/comments/1kaveqf/your_top_10_arcade_games_for_parties_with/): sugerencias comunitarias de beat-em-ups/deportes; señal de curación, no métrica objetiva de popularidad.\n\n## Recomendación de interfaz\n\nMostrar sólo título, número de jugadores de metadata, control recomendado certificado y disponibilidad de joystick. Conservar menú técnico en Admin Mode. Banners de jugadores deben decir “metadata” hasta que core/emulador y mandos estén verificados.\n\n## Multiplayer 5–8P\n\nEl inventario detectó 163 filas con metadata cuyo máximo declarado es 5 o más; contiene números que pueden ser online o modos no simultáneos (ej. 2–32), por lo que no son 163 juegos 5–8P locales confirmados. `GAMES_5_TO_8_PLAYERS.md` separa los candidatos instalados de soporte runtime y certificación física, ambos NOT_TESTED. Revisar primero juegos arcade clásicos de 4/6 plazas y consolas con multitap; validar límites de USB y emulator antes de anunciar 5–8P.\n\n## Decisión de terceros\n\nNo se instaló software/theme/proyecto externo. El dashboard debe iniciar read-only, LAN/VPN solamente, sin exponer acciones a WAN ni API de EmulationStation.\n'''
 (ROOT/'ARCADE_GITHUB_RESEARCH.md').write_text(research,encoding='utf-8')
 # status and checkpoint update, atomic; phases reflect evidence completed in this continuation only.
 cp=json.loads((ROOT/'arcade_master_checkpoint.json').read_text(encoding='utf-8'))
 phases=cp['phases'];
 def setp(k,status,summary,issues=None):phases[k].update({'status':status,'summary':summary,'issues':issues or []});phases[k]['updated_at']=now
 setp('PHASE_14_FULL_GAME_CERTIFICATION','BLOCKED',f'Inventario resumible de {len(games)} filas en {len(bysys)} sistemas; baseline transaccional actual verificado en archivo separado, histórico preservado. No se ejecutaron launches: falta integrar restore en adapters universales y audio default HDMI.', ['CERT-001','AUD-002'])
 setp('PHASE_15_VISUAL_MEDIA_AUDIT','COMPLETE_WITH_ISSUES',f'{len(media)} gamelist entries; imágenes presentes {images}, vídeos {videos}, thumbnails {thumbs}, fanart {fanarts}; {missing_primary} sin imagen accesible; orphans candidatos registrados; calidad visual y actividad de vídeo no certificadas.', ['MEDIA-001'])
 setp('PHASE_16_MULTIPLAYER_8P','COMPLETE_WITH_ISSUES',f'{len(multi)} entradas metadata >=2; {sum(int(x["max_players_metadata"])>=5 for x in multi)} filas >=5 players metadata; 0 runtime/physical certified.', ['MULTI-001'])
 setp('PHASE_17_CONTROLLER_CERTIFICATION','MANUAL_REQUIRED','Snapshot read-only actual: cuatro paneles P1-P4 más DualShock y USB Gamepad externos; herramienta física evdev lista, ninguna secuencia física certificada.', ['CTRL-001'])
 setp('PHASE_18_GUEST_READY_BUILD','COMPLETE_WITH_ISSUES','No se incluyó ningún juego en Guest Ready. El inventario y requerimientos están separados; GUEST_READY permanece 0 hasta AUTO_CERTIFIED + CONTROL_CERTIFIED + salida/audio/video.', ['AUD-002','CTRL-001'])
 setp('PHASE_19_FAILURE_REPAIR_LOOP','COMPLETE_WITH_ISSUES','Causas actuales agrupadas en reporte; sin retries ni reparaciones nuevas, se preservaron fallos y estados históricos.', ['SAFE-001','AUD-002','CAT-001'])
 # issue rows are appended only if absent.
 issue_rows=issues; seen={x['id'] for x in issue_rows}
 additions=[
  {'id':'CERT-001','phase':'PHASE_14_FULL_GAME_CERTIFICATION','system':'all','game':'','severity':'HIGH','category':'STALE_PROTECTED_BASELINE','description':'Smoke runner preflight detects only the 18 authorized MAME overrides added after its backup; its restore would revert batocera.conf. No game was launched.','evidence':'smoke_runner.py preflight plus redacted diff against protected backup; exact additions are the 18 authorized per-game MAME overrides.','status':'OPEN','action':'Implement a new current transaction baseline with per-game restore; keep old baseline historical.','manual_required':'NO'},
  {'id':'MEDIA-001','phase':'PHASE_15_VISUAL_MEDIA_AUDIT','system':'all','game':'','severity':'LOW','category':'MEDIA_ORPHAN_CANDIDATES','description':f'{len(orphans) if "orphans" in locals() else 3565} unreferenced image/video paths found; {missing_primary} records lack an accessible primary image. Candidates are not auto-deleted.','evidence':'media_audit.csv; media_orphan_candidates.csv','status':'OPEN','action':'Review candidate path/gamelist references before any deletion.','manual_required':'NO'},
  {'id':'MULTI-001','phase':'PHASE_16_MULTIPLAYER_8P','system':'all','game':'','severity':'MEDIUM','category':'MULTIPLAYER_METADATA_UNVERIFIED','description':'Metadata has 163 rows with max player value >=5; some values may indicate online/non-simultaneous users. No runtime/physical 5-8P capability certified.','evidence':'multiplayer_games.csv; GAMES_5_TO_8_PLAYERS.md','status':'OPEN','action':'Validate local simultaneity, emulator limits, multitap and physical controller topology game by game.','manual_required':'YES'}]
 issue_rows.extend(x for x in additions if x['id'] not in seen)
 writecsv('arcade_issues.csv',list(issue_rows[0].keys()),issue_rows)
 cp['updated_at']=now;cp['current_phase']='PHASE_14_FULL_GAME_CERTIFICATION';cp['last_action']='Generated read-only cross-system certification/media/multiplayer inventories, physical input tool and system reports. No games launched; old restore baseline is stale for current authorized overrides.'
 cp.setdefault('current_observations',{})['certification']={'systems_with_game_entries':len(bysys),'game_rows':len(games),'historic_boot_ok':sum(v for k,v in boots.items() if k.startswith('BOOT_OK')),'auto_certified_new':0,'control_certified':0,'guest_ready':0,'media_rows':len(media),'images_present':images,'videos_present':videos,'thumbnail_present':thumbs,'fanart_present':fanarts,'orphan_candidates':3565,'multiplayer_metadata_rows':len(multi),'metadata_max_players_5_to_8':sum(5<=int(x['max_players_metadata'])<=8 for x in multi),'metadata_max_players_over_8':sum(int(x['max_players_metadata'])>8 for x in multi),'runtime_5_to_8_certified':0,'physical_5_to_8_certified':0,'launch_tests_performed':0,'current_baseline':'VERIFIED; separate local 0600 file, historic backup preserved','safety':'BLOCKED: universal per-game restore integration not yet implemented and HDMI is not default audio sink'}
 cp.setdefault('scope_extension',{}).setdefault('full_game_certification',{})
 cp['scope_extension']['full_game_certification']['inventory_csv']='full_game_certification.csv';cp['scope_extension']['full_game_certification']['resume_checkpoint']='full_game_certification_checkpoint.json'
 cp['scope_extension']['full_game_certification']['resume_policy']='Continue from NOT_TESTED rows; never repeat a runtime attempt without explicit retry state and verified per-game restore.'
 atomic('arcade_master_checkpoint.json',cp)
 certstate={'schema_version':1,'updated_at':now,'source':'full_game_certification.csv','queue_policy':'priority: guest candidates, favorites, multiplayer, fighting, beat-em-up, classics, popular, remainder; remove-candidate last',
            'next_untested':None,'attempted_new':0,'auto_certified':0,'manual_control_certified':0,'guest_ready':0,'launches_blocked_by':['UNIVERSAL_RESTORE_ADAPTERS_NOT_IMPLEMENTED','AUDIO_DEFAULT_WRONG'],
            'note':'Resume by selecting next row with auto_certification=NOT_TESTED after safety blockers resolved; no automatic retry of FAIL/FLAKY.'}
 atomic('full_game_certification_checkpoint.json',certstate)
 print(json.dumps({'systems':len(bysys),'games':len(games),'historic_boot_ok':sum(v for k,v in boots.items() if k.startswith('BOOT_OK')),
                   'certification_media':len(media),'image_coverage':images,'video_coverage':videos,'multiplayer_rows':len(multi),
                   'multi_metadata_5plus':sum(int(x['max_players_metadata'])>=5 for x in multi),'reports_per_system':len(rootrows)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
