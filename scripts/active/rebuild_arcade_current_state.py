#!/usr/bin/env python3
"""Generate the public arcade state from local canonical data and read-only probes."""
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

AUDIT = Path('/userdata/system/state/arcade_audit')
EXPORT = Path('/userdata/system/state/arcade_audit_git')
CONF = Path('/userdata/system/batocera.conf')
ES_SYSTEMS = Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg')
TOKEN_FILE = Path('/userdata/system/secrets/github_arcade_audit.token')
OWNER, REPO, BRANCH = 'agustinc08', 'arcade-audit', 'main'
EXPECTED_PADS = {
    'P1': ('USB5', 'event17', 'js0'), 'P2': ('USB6', 'event18', 'js1'),
    'P3': ('USB8', 'event20', 'js3'), 'P4': ('USB7', 'event19', 'js2'),
}
EXPECTED_MAME_OVERRIDES = {
    'ffight2b.zip', 'altair.zip', 'apache3.zip', 'blazlaz.zip', 'cubeqst.zip',
    'sia2650.zip', 'evosocc.zip', 'hoops95.zip', 'funcube4.zip', 'lbgrande.zip',
    'sws98.zip', 'tenkomor.zip', 'multigam.zip', 'multigm3.zip', 'nratechu.zip',
    'ertictac.zip', 'kov2p.zip', 'martmast.zip',
}


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def command(*args):
    try:
        return subprocess.run(args, check=False, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True, timeout=8).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ''


def remote_head():
    if not TOKEN_FILE.is_file() or TOKEN_FILE.stat().st_mode & 0o077:
        return 'UNAVAILABLE: token file missing or permissions unsafe'
    auth_value = TOKEN_FILE.read_text(encoding='utf-8').strip()
    if not auth_value:
        return 'UNAVAILABLE: token file empty'
    req = urllib.request.Request(
        f'https://api.github.com/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}',
        headers={'Accept': 'application/vnd.github+json', 'Authorization': 'Bearer ' + auth_value,
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Batocera-Arcade-Audit'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        return data['object']['sha']
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError):
        return 'UNAVAILABLE: GitHub read failed'
    finally:
        auth_value = ''


def parse_conf():
    if not CONF.is_file():
        raise RuntimeError('batocera.conf unavailable')
    lines = CONF.read_text(encoding='utf-8', errors='replace').splitlines()
    values = {}
    overrides = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key == 'mame.core' or key == 'global.mame.core':
            values['global_mame_core'] = value.strip().strip('"')
        match = re.fullmatch(r'mame\["([^"]+\.zip)"\]\.core', key)
        if match:
            overrides.append((match.group(1), value.strip().strip('"')))
        if key in {'global.videomode', 'global.videooutput', 'global.vsync',
                    'audio.device', 'audio.mode', 'audio.volume'}:
            values[key] = value.strip().strip('"')
    values['overrides'] = sorted(overrides)
    return values


def effective_mame_core():
    try:
        root = ET.parse(ES_SYSTEMS).getroot()
        for system in root.findall('.//system'):
            if (system.findtext('name') or '').strip().lower() != 'mame':
                continue
            cores = system.findall('.//core')
            preferred = next((c for c in cores if c.get('default', '').lower() == 'true'), None)
            if preferred is None and cores:
                preferred = cores[0]
            return (preferred.text or '').strip() if preferred is not None else 'UNKNOWN'
    except (OSError, ET.ParseError):
        return 'UNKNOWN'
    return 'UNKNOWN'


def default_audio_sink():
    sink = command('pactl', 'get-default-sink')
    if sink:
        return sink
    sink = command('wpctl', 'inspect', '@DEFAULT_AUDIO_SINK@')
    for line in sink.splitlines():
        match = re.search(r'node\.name\s*=\s*"([^"]+)"', line)
        if match:
            return match.group(1)
    return 'UNAVAILABLE'


def controller_state():
    path = AUDIT / 'controllers_live.json'
    if not path.exists():
        return 'UNAVAILABLE', [], []
    data = load_json(path)
    if data.get('mapping_modified') is True:
        raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: controller mapping modification flag is set')
    entries = data.get('BOTONERA_P1_P4')
    if not isinstance(entries, list):
        raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: controllers_live schema unavailable')
    lines = []
    for player, expected in EXPECTED_PADS.items():
        found = next((item for item in entries if item.get('player') == player), None)
        usb, event, js = expected
        if not found:
            raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: controller player missing')
        if (found.get('usb_port') != usb or found.get('event_path') != '/dev/input/' + event
                or 'js' + str(found.get('sdl_index')) != js):
            raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: P1-P4 mapping differs')
        lines.append(f'- {player}: {usb} / {event} / {js}')
    gamepads = data.get('GAMEPADS_CONNECTED', [])
    external = []
    if isinstance(gamepads, list):
        for pad in gamepads:
            if not isinstance(pad, dict):
                continue
            name = str(pad.get('name') or 'Unknown').replace('`', '')
            transport = str(pad.get('transport') or 'unknown').replace('`', '')
            audio = 'yes' if pad.get('audio_capability') is True else 'no/unknown'
            external.append(f'{name} ({transport}, audio endpoint: {audio})')
    return 'controllers_live.json', lines, external


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        os.chmod(temp, 0o644); os.replace(temp, path)
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def config_report(conf, mame_core):
    tracked = {
        'batocera.conf': CONF,
        'controller_dispatcher': Path('/userdata/system/el_gordo_tools/controller_dispatcher'),
        'selector_controles': Path('/userdata/system/el_gordo_tools/selector_controles'),
        'custom_service': Path('/userdata/system/services/custom_service'),
        'audio_policy_service': Path('/userdata/system/el_gordo_tools/arcade_audio_policy_service.sh'),
        'es_systems_el_gordo.cfg': ES_SYSTEMS,
        'custom.sh': Path('/userdata/system/custom.sh'),
    }
    lines = ['# Configuración actual saneada de Batocera', '',
             'Generado de la configuración activa. No es una copia de `batocera.conf`; sólo enumera parámetros permitidos y hashes de archivos críticos.', '',
             '## Parámetros seleccionados', '']
    safe = {k:v for k,v in conf.items() if k != 'overrides'}
    lines.append(f'- Effective MAME system core in `es_systems_el_gordo.cfg`: `{mame_core}`')
    for key, value in sorted(safe.items()):
        lines.append(f'- `{key}`: `{value}`')
    lines.append(f'- MAME per-game overrides: {len(conf["overrides"])}')
    for rom, core in conf['overrides']:
        lines.append(f'  - `{rom}` → `{core}`')
    lines += ['', '## SHA-256 de configuración y herramientas activas', '']
    for label, path in tracked.items():
        if not path.is_file():
            lines.append(f'- `{label}`: ausente')
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f'- `{label}`: `{digest}`')
    lines += ['', 'No se exportan SSID, contraseñas, tokens, cuentas, archivos completos de configuración ni claves.', '']
    atomic_write(AUDIT / 'reports/CURRENT_BATOCERA_CONFIG.md', '\n'.join(lines))


def main():
    cert = load_json(AUDIT / 'full_game_certification_checkpoint.json')
    master = load_json(AUDIT / 'arcade_master_checkpoint.json')
    rows = read_csv(AUDIT / 'full_game_certification.csv')
    issues_path = AUDIT / 'arcade_issues.csv'
    if not issues_path.exists():
        issues_path = AUDIT / 'data/arcade_issues.csv'
    issues = read_csv(issues_path)
    systems = read_csv(AUDIT / 'data/detected_systems.csv')
    repairs_path = AUDIT / 'game_repair_queue.csv'
    repairs = read_csv(repairs_path) if repairs_path.exists() else []
    conf = parse_conf()
    mame_core = effective_mame_core()
    counts = {
        'total_inventory': len(rows), 'installed': sum(r.get('installed') == 'YES' for r in rows),
        'historical_boot_ok': sum(bool(r.get('boot_core')) for r in rows),
        'auto_certified': sum(r.get('auto_certification') == 'AUTO_CERTIFIED' for r in rows),
        'game_fail': sum(r.get('auto_certification') == 'GAME_FAIL' for r in rows),
        'static_fail': sum(r.get('auto_certification') == 'STATIC_FAIL' for r in rows),
        'flaky': sum(r.get('auto_certification') == 'FLAKY' for r in rows),
        'needs_repair': sum(r.get('lifecycle_state') == 'NEEDS_REPAIR' for r in rows),
        'control_certified': sum(r.get('control_certification') == 'CONTROL_CERTIFIED' for r in rows),
        'guest_ready': sum(r.get('guest_ready') == 'YES' for r in rows),
    }
    attempted_from_table = sum(r.get('auto_certification') in
                               {'AUTO_CERTIFIED', 'GAME_FAIL', 'STATIC_FAIL', 'FLAKY'} for r in rows)
    if attempted_from_table != cert.get('attempted_new'):
        raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: attempted count differs')
    checks = [('AUTO_CERTIFIED', counts['auto_certified'], cert.get('auto_certified')),
              ('CONTROL_CERTIFIED', counts['control_certified'], cert.get('manual_control_certified')),
              ('GUEST_READY', counts['guest_ready'], cert.get('guest_ready'))]
    if any(actual != expected for _, actual, expected in checks):
        raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: certification CSV/checkpoint mismatch')
    actual_override_names = {name for name, _ in conf['overrides']}
    if (mame_core != 'mame078plus'
            or actual_override_names != EXPECTED_MAME_OVERRIDES
            or any(core != 'mame' for _, core in conf['overrides'])):
        raise RuntimeError('CURRENT_STATE_RECONCILIATION_FAIL: MAME core/override baseline mismatch')
    head = remote_head()
    version = command('cat', '/etc/os-release')
    batocera = next((x.split('=',1)[1].strip('"') for x in version.splitlines() if x.startswith('VERSION=')), 'UNKNOWN')
    lscpu = command('lscpu')
    cpu = next((x.split(':',1)[1].strip() for x in lscpu.splitlines()
                if x.startswith(('Model name:', 'Nombre del modelo:'))), '')
    if not cpu:
        cpuinfo = command('cat', '/proc/cpuinfo')
        cpu = next((x.split(':',1)[1].strip() for x in cpuinfo.splitlines()
                    if x.lower().startswith('model name')), 'UNKNOWN')
    memory = command('free', '-h')
    ram = next((x.split()[1] for x in memory.splitlines() if x.startswith('Mem:')), 'UNKNOWN')
    gpu = command('lspci')
    gpu = next((x.split(': ',1)[-1] for x in gpu.splitlines() if 'VGA compatible controller' in x or '3D controller' in x), 'UNKNOWN')
    disks = command('df', '-h', '/userdata', '/media/ROMS', '/media/BATOCERA_ROMS')
    phase = master.get('phases', {}).get('PHASE_14_FULL_GAME_CERTIFICATION', {}).get('status', 'UNKNOWN')
    next_game = cert.get('next_untested') or cert.get('next_game') or 'NONE'
    pads_source, pads, gamepads = controller_state()
    audio_sink = default_audio_sink()
    display_mode = conf.get('global.videomode', 'NOT_CONFIGURED')
    repair_count = sum(1 for r in repairs if r.get('status','').upper() not in {'FIXED','CLOSED','RESOLVED'})
    root_issues = [i for i in issues if i.get('status','').upper() in
                   {'OPEN','ABIERTO','EN INVESTIGACIÓN','BLOCKED','BLOQUEADO'}]
    manual_path = AUDIT / 'manual_physical_test_queue.csv'
    if not manual_path.exists():
        manual_path = AUDIT / 'data/manual_physical_test_queue.csv'
    manual_rows = read_csv(manual_path) if manual_path.exists() else []
    manual_pending = sum(1 for row in manual_rows if row.get('status','').upper() not in
                         {'DONE','COMPLETE','PASS','CONTROL_CERTIFIED','CLOSED'})
    free = '\n'.join('    ' + x for x in disks.splitlines()[1:]) if disks else '    UNKNOWN'
    pad_text = '\n'.join(pads) if pads else '- No disponible'
    last_action = master.get('last_action', 'No registrado')
    if isinstance(last_action, (dict, list)):
        last_action = json.dumps(last_action, ensure_ascii=False, sort_keys=True)
    lines = [
        '# Estado actual del arcade', '',
        f'- UPDATED_AT: {dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}',
        f'- GITHUB_HEAD observado antes de publicar: `{head}`',
        f'- BATOCERA_VERSION: {batocera}', '', '## Sistema y hardware', '',
        f'- CPU: {cpu}', f'- GPU: {gpu}', f'- RAM: {ram}',
        f'- DISPLAY: modo configurado `{display_mode}`; EDID/modo vivo no disponible en la sesión de consulta.',
        '- NETWORK: Ethernet y adaptadores Wi-Fi/Bluetooth detectados históricamente; no se publican SSID, dirección IP ni MAC.', '',
        '## Configuración arcade', '',
        f'- GLOBAL_MAME_CORE: `{mame_core}`',
        f'- MAME_OVERRIDES_COUNT: {len(conf["overrides"])}',
        f'- AUDIO_DEFAULT: `{audio_sink}`',
        f'- HDMI_DEFAULT_STATUS: {"PASS" if "pci-0000_01_00.1.hdmi-stereo" in audio_sink else "NOT_CONFIRMED"}',
        '- AUDIO_POLICY_STATUS: instalada; reconexión física DS4 y persistencia post-reboot pendientes.', '',
        '### P1–P4', '', f'- Fuente de snapshot: `{pads_source}`', pad_text, '',
        f'- GAMEPADS_CONNECTED: {len(gamepads)}',
        *[f'  - {x}' for x in gamepads], '',
        '## Certificación', '', f'- FULL_CERTIFICATION_PHASE: {phase}',
        f'- TOTAL_INVENTORY: {counts["total_inventory"]}', f'- INSTALLED: {counts["installed"]}',
        f'- HISTORICAL_BOOT_OK: {counts["historical_boot_ok"]}',
        f'- AUTO_CERTIFIED: {counts["auto_certified"]}', f'- GAME_FAIL: {counts["game_fail"]}',
        f'- STATIC_FAIL: {counts["static_fail"]}', f'- FLAKY: {counts["flaky"]}',
        f'- NEEDS_REPAIR: {counts["needs_repair"]}', f'- CONTROL_CERTIFIED: {counts["control_certified"]}',
        f'- GUEST_READY: {counts["guest_ready"]}', f'- NEXT_GAME: `{next_game}`',
        f'- ADAPTERS_READY: {sum(s.get("adapter_status") == "READY" for s in systems)}',
        f'- ADAPTERS_PENDING: {sum(s.get("adapter_status") != "READY" for s in systems)}',
        f'- REPAIR_QUEUE_PENDING: {repair_count}', '', '## Espacio', '',
        '- FILESYSTEM_STATUS: lectura de capacidad; no es una prueba SMART.', free, '',
        '## Guest Mode y herramientas', '',
        f'- GUEST_MODE_STATUS: {master.get("phases", {}).get("PHASE_07_GUEST_MODE", {}).get("status", "UNKNOWN")}; no se promueven juegos automáticamente.',
        '- ARCADE_MANAGER_STATUS: script local disponible; servicio/panel persistente no certificado.',
        f'- OPEN_ROOT_ISSUES: {len(root_issues)}',
        f'- MANUAL_TESTS_PENDING: {manual_pending} (detalle en `data/manual_physical_test_queue.csv`).',
        f'- LAST_MAJOR_CHANGES: {last_action}', '',
        'Este documento se deriva de checkpoints, tabla de certificación y consultas locales. Los datos variables deben regenerarse; los reportes históricos no prevalecen sobre estas fuentes.', ''
    ]
    text='\n'.join(lines)
    atomic_write(AUDIT / 'ARCADE_CURRENT_STATE.md', text)
    config_report(conf, mame_core)
    print('CURRENT_STATE_WRITTEN', AUDIT / 'ARCADE_CURRENT_STATE.md')
    print('GITHUB_HEAD', head)
    print('CERTIFICATION_RECONCILIATION_PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Avoid reporting exception context that could contain data values.
        print(type(exc).__name__ + ': ' + str(exc).split(':',1)[0])
        raise SystemExit(2)
