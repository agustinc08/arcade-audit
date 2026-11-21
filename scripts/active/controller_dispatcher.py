#!/usr/bin/python3
from __future__ import annotations

import argparse
import contextlib
import ctypes
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from marker_ownership import marker_lock, read_marker
from marker_ownership import remove_if_owned as remove_owned_marker
import automatic_selector_context as automatic_context


ROOT = Path("/userdata/system")
TOOLS = ROOT / "el_gordo_tools"
TECHNICAL = ROOT / "configs/el_gordo_controller_profiles/controller_technical.json"
MULTIPLAYER = ROOT / "configs/el_gordo_controller_profiles/multiplayer.json"
BATOCERA_CONF = ROOT / "batocera.conf"
HEALTH_DB = ROOT / "state/game_health.sqlite"
BOOT_AUDIT_ONCE = ROOT / "state/boot_audit_once.json"
LAUNCH_STDERR = ROOT / "logs/es_launch_stderr.log"
EMULATOR_LOG = ROOT / "logs/emulog.txt"
LOCK_PATH = Path("/var/run/el_gordo_controller_dispatcher.lock")
PLAYER_OPTION = re.compile(r"^-p([1-8])(index|guid|name|devicepath|nbbuttons|nbhats|nbaxes)$")
MS_BIND = 4096
MS_REC = 16384
MS_PRIVATE = 1 << 18


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} no contiene un objeto JSON")
    return value


def technical_config() -> dict[str, Any]:
    cfg = load_json(TECHNICAL)
    ports = cfg.get("arcade_controllers")
    if not isinstance(ports, list) or len(ports) != 4:
        raise ValueError("la configuración técnica no define exactamente cuatro botoneras")
    if cfg.get("max_players") != 8:
        raise ValueError("max_players debe ser 8 para el launcher Batocera instalado")
    return cfg


def rotate_log(cfg: dict[str, Any]) -> Path:
    logging_cfg = cfg["logging"]
    path = Path(logging_cfg["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    maximum = int(logging_cfg.get("max_bytes", 262144))
    if path.exists() and path.stat().st_size >= maximum:
        backup = path.with_name(path.name + ".1")
        if backup.exists():
            backup.unlink()
        path.replace(backup)
    return path


def log_line(log_path: Path, event: str, **fields: Any) -> None:
    record = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event": event,
        **fields,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def show_error(message: str) -> None:
    if not os.environ.get("DISPLAY"):
        return
    try:
        subprocess.run(
            [
                "/usr/bin/yad",
                "--error",
                "--title=Selector de controles",
                f"--text={message}",
                "--button=OK:0",
                "--timeout=8",
                "--center",
                "--on-top",
            ],
            check=False,
            timeout=10,
        )
    except Exception:
        pass


def tail_text(path: Path, maximum_lines: int = 80, maximum_chars: int = 12000) -> str:
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-maximum_lines:])[-maximum_chars:]


def useful_error(*logs: str) -> str:
    pattern = re.compile(
        r"(error|failed|fatal|missing|not found|unable|exception|invalid|no such file|bios|chd|cue)",
        re.IGNORECASE,
    )
    matches = [line.strip() for text in logs for line in text.splitlines() if pattern.search(line)]
    return "\n".join(matches[-12:])[-4000:]


def ensure_health_database() -> None:
    HEALTH_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(HEALTH_DB, timeout=5) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS launch_events (
                id INTEGER PRIMARY KEY,
                launched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                system TEXT NOT NULL,
                rom TEXT NOT NULL,
                control_order TEXT NOT NULL
                    CHECK (control_order IN ('arcade','external','unknown')),
                emulator TEXT,
                core TEXT,
                command TEXT NOT NULL CHECK (json_valid(command)),
                pid INTEGER,
                duration_seconds REAL NOT NULL,
                exit_code INTEGER,
                signal INTEGER,
                relevant_error TEXT,
                launcher_log TEXT,
                emulator_log TEXT,
                effective_config TEXT NOT NULL CHECK (json_valid(effective_config)),
                status TEXT NOT NULL,
                requested_exit INTEGER NOT NULL CHECK (requested_exit IN (0,1)),
                diagnosis TEXT,
                solution TEXT,
                missing_file TEXT
            );
            CREATE INDEX IF NOT EXISTS launch_events_status_time
                ON launch_events(status, id DESC);
            CREATE INDEX IF NOT EXISTS launch_events_game_time
                ON launch_events(system, rom, id DESC);
            CREATE TABLE IF NOT EXISTS game_diagnoses (
                id INTEGER PRIMARY KEY,
                diagnosed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
                system TEXT NOT NULL,
                rom TEXT NOT NULL,
                emulator TEXT,
                core TEXT,
                category TEXT NOT NULL,
                evidence TEXT NOT NULL,
                missing_file TEXT,
                solution TEXT NOT NULL,
                current_state TEXT NOT NULL,
                quarantine_path TEXT,
                source TEXT,
                UNIQUE(system, rom)
            );
            """
        )


def command_identity(command_array: list[str], entry: dict[str, Any] | None) -> tuple[str, str]:
    emulator = str(entry.get("emulator", "")) if entry else ""
    core = str(entry.get("core", "")) if entry else ""
    executable = Path(command_array[0]).name.lower() if command_array else ""
    if not emulator:
        if "retroarch" in executable:
            emulator = "libretro"
        elif "duckstation" in executable:
            emulator = "duckstation"
        elif "pcsx2" in executable:
            emulator = "pcsx2"
        elif "dolphin" in executable:
            emulator = "dolphin"
        else:
            emulator = executable
    if not core and "-L" in command_array:
        try:
            core = Path(command_array[command_array.index("-L") + 1]).stem.removesuffix("_libretro")
        except (ValueError, IndexError):
            pass
    if not core:
        core = emulator
    return emulator, core


def record_launch(
    system: str,
    rom: Path,
    choice: str,
    entry: dict[str, Any] | None,
    ordered: list[dict[str, Any]],
    maximum: int,
    trace: dict[str, Any],
    requested_exit: bool,
) -> str:
    ensure_health_database()
    started_wall = float(trace.get("started_wall", 0.0))
    launcher_log = (
        tail_text(LAUNCH_STDERR)
        if LAUNCH_STDERR.is_file() and LAUNCH_STDERR.stat().st_mtime >= started_wall - 2.0
        else ""
    )
    emulator_log = (
        tail_text(EMULATOR_LOG)
        if EMULATOR_LOG.is_file() and EMULATOR_LOG.stat().st_mtime >= started_wall - 2.0
        else ""
    )
    duration = float(trace.get("duration_seconds", 0.0))
    exit_code = trace.get("exit_code")
    threshold = 15.0
    if requested_exit:
        status = "CIERRE_SOLICITADO"
    elif not trace.get("command") or (exit_code is not None and int(exit_code) != 0) or duration < threshold:
        status = "SALIDA_INMEDIATA_PENDIENTE"
    else:
        status = "INICIO_SOSTENIDO"
    signal_number = -int(exit_code) if exit_code is not None and int(exit_code) < 0 else None
    command = [str(item) for item in trace.get("command", [])]
    emulator, core = command_identity(command, entry)
    effective = {
        "multiplayer_entry": entry or {},
        "assigned": [
            {
                "player": index + 1,
                "name": controller["name"],
                "guid": controller["guid"],
                "source": controller["source_path"],
                "arcade_player": controller.get("arcade_player"),
                "usb_port": controller.get("usb_port"),
            }
            for index, controller in enumerate(ordered[:maximum])
        ],
    }
    with sqlite3.connect(HEALTH_DB, timeout=5) as connection:
        connection.execute(
            """
            INSERT INTO launch_events (
                system, rom, control_order, emulator, core, command, pid,
                duration_seconds, exit_code, signal, relevant_error,
                launcher_log, emulator_log, effective_config, status, requested_exit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                system,
                str(rom),
                choice if choice in ("arcade", "external") else "unknown",
                emulator,
                core,
                json.dumps(command, ensure_ascii=False),
                trace.get("pid"),
                duration,
                exit_code,
                signal_number,
                useful_error(launcher_log, emulator_log),
                launcher_log,
                emulator_log,
                json.dumps(effective, ensure_ascii=False, sort_keys=True),
                status,
                int(requested_exit),
            ),
        )
    return status


def last_launch_failed(rom: str) -> bool:
    if not HEALTH_DB.is_file():
        return False
    try:
        with sqlite3.connect(HEALTH_DB, timeout=5) as connection:
            row = connection.execute(
                "SELECT status FROM launch_events WHERE rom=? ORDER BY id DESC LIMIT 1",
                (rom,),
            ).fetchone()
        return bool(row and row[0] == "SALIDA_INMEDIATA_PENDIENTE")
    except sqlite3.Error:
        return False


def extract_launch_identity(argv: list[str]) -> tuple[str, str]:
    def value_after(flag: str) -> str:
        try:
            return argv[argv.index(flag) + 1]
        except (ValueError, IndexError) as exc:
            raise ValueError(f"falta {flag} en el lanzamiento") from exc

    return value_after("-system"), value_after("-rom")


# BOOT AUDIT — AUTO BOTONERA
def consume_boot_audit_once(
    system: str,
    rom: str,
    one_shot_path: Path = BOOT_AUDIT_ONCE,
    now: float | None = None,
) -> str | None:
    """Consume a matching, short-lived BOOT AUDIT choice without changing normal launches."""
    with marker_lock():
        return _consume_boot_audit_once_locked(system, rom, one_shot_path, now)


def _consume_boot_audit_once_locked(
    system: str,
    rom: str,
    one_shot_path: Path = BOOT_AUDIT_ONCE,
    now: float | None = None,
) -> str | None:
    marker = read_marker(one_shot_path)
    if marker is None:
        return None
    if (
        marker.get("enabled") is not True
        or marker.get("system") != system
        or marker.get("rom") != rom
        or not Path(rom).is_absolute()
        or marker.get("choice") not in ("BOTONERA", "JOYSTICKS")
    ):
        return None
    try:
        issued_at = float(marker["created_at"])
        expires_at = float(marker["expires_at"])
    except (KeyError, TypeError, ValueError):
        return None
    current_time = time.time() if now is None else now
    if (
        issued_at > current_time
        or current_time - issued_at > 60
        or expires_at <= current_time
        or expires_at < issued_at
        or expires_at - issued_at > 60
    ):
        return None
    try:
        if one_shot_path.is_symlink() or not one_shot_path.is_file():
            return None
        one_shot_path.unlink()
    except OSError:
        return None
    return "arcade" if marker.get("choice") == "BOTONERA" else "external"


def sdl_text(value: bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if value else ""


def scan_sdl() -> list[dict[str, Any]]:
    import sdl2

    if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
        raise RuntimeError(f"SDL_Init: {sdl_text(sdl2.SDL_GetError())}")
    found: list[dict[str, Any]] = []
    try:
        for index in range(sdl2.SDL_NumJoysticks()):
            path_bytes = sdl2.SDL_JoystickPathForIndex(index)
            path = sdl_text(path_bytes)
            if not path:
                continue
            guid_struct = sdl2.SDL_JoystickGetDeviceGUID(index)
            guid_buffer = ctypes.create_string_buffer(33)
            sdl2.SDL_JoystickGetGUIDString(guid_struct, guid_buffer, 33)
            handle = sdl2.SDL_JoystickOpen(index)
            if not handle:
                raise RuntimeError(f"no se pudo abrir SDL joystick {index}")
            try:
                found.append(
                    {
                        "index": index,
                        "guid": guid_buffer.value.decode("ascii"),
                        "name": sdl_text(sdl2.SDL_JoystickName(handle)),
                        "path": str(Path(path).resolve()),
                        "nbbuttons": int(sdl2.SDL_JoystickNumButtons(handle)),
                        "nbhats": int(sdl2.SDL_JoystickNumHats(handle)),
                        "nbaxes": int(sdl2.SDL_JoystickNumAxes(handle)),
                    }
                )
            finally:
                sdl2.SDL_JoystickClose(handle)
    finally:
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER | sdl2.SDL_INIT_JOYSTICK)
    unique: dict[str, dict[str, Any]] = {}
    for controller in found:
        if controller["path"] in unique:
            raise RuntimeError(f"SDL enumeró dos veces {controller['path']}")
        unique[controller["path"]] = controller
    return found


def input_roots() -> list[ET.Element]:
    paths = (
        ROOT / "configs/emulationstation/es_input.cfg",
        Path("/usr/share/emulationstation/es_input.cfg"),
    )
    return [ET.parse(path).getroot() for path in paths if path.exists()]


def find_input_config(controller: dict[str, Any]) -> ET.Element:
    roots = input_roots()
    queries = (
        f'./inputConfig[@deviceGUID="{controller["guid"]}"][@deviceName="{controller["name"]}"]',
        f'./inputConfig[@deviceGUID="{controller["guid"]}"]',
        f'./inputConfig[@deviceName="{controller["name"]}"]',
    )
    for query in queries:
        for root in roots:
            if (element := root.find(query)) is not None:
                return element
    raise RuntimeError(f"mando sin autoconfiguración Batocera: {controller['name']} {controller['guid']}")


def input_button_codes(controller: dict[str, Any]) -> tuple[int, int]:
    element = find_input_config(controller)
    result: dict[str, int] = {}
    for name in ("select", "start"):
        item = element.find(f'./input[@name="{name}"]')
        if item is None or item.get("type") != "button":
            raise RuntimeError(f"{controller['name']} no tiene {name} como botón")
        code = item.get("code")
        if code is None:
            raise RuntimeError(f"{controller['name']} no registra el código evdev de {name}")
        result[name] = int(code)
    return result["select"], result["start"]


def classify_and_order(
    cfg: dict[str, Any], controllers: list[dict[str, Any]], choice: str
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    by_real_path = {controller["path"]: controller for controller in controllers}
    arcade: list[dict[str, Any]] = []
    identities: dict[str, str] = {}
    for item in cfg["arcade_controllers"]:
        by_path = Path(item["by_path"])
        if not by_path.exists():
            raise RuntimeError(f"{item['player']} no está conectado en {by_path}")
        real_path = str(by_path.resolve())
        controller = by_real_path.get(real_path)
        if controller is None:
            raise RuntimeError(f"{item['player']} no fue enumerado por SDL: {real_path}")
        if "dragonrise" not in controller["name"].lower():
            raise RuntimeError(f"{item['player']} no es DragonRise: {controller['name']}")
        if controller in arcade:
            raise RuntimeError("una botonera fue asignada a dos puertos")
        copy = dict(controller)
        copy["arcade_player"] = item["player"]
        copy["usb_port"] = item["usb_port"]
        arcade.append(copy)
        identities[item["player"]] = real_path

    arcade_paths = {controller["path"] for controller in arcade}
    external = [controller for controller in controllers if controller["path"] not in arcade_paths]
    if choice == "arcade":
        ordered = arcade + external
    elif choice == "external":
        ordered = external + arcade if external else arcade
    else:
        raise ValueError(f"elección desconocida: {choice}")
    if len({controller["path"] for controller in ordered}) != len(ordered):
        raise RuntimeError("el orden temporal contiene dispositivos repetidos")
    return ordered, identities


def strip_player_arguments(argv: list[str]) -> list[str]:
    cleaned: list[str] = []
    index = 0
    while index < len(argv):
        if PLAYER_OPTION.match(argv[index]):
            if index + 1 >= len(argv):
                raise ValueError(f"{argv[index]} no tiene valor")
            index += 2
            continue
        cleaned.append(argv[index])
        index += 1
    return cleaned


def controller_arguments(ordered: list[dict[str, Any]], maximum: int) -> list[str]:
    result: list[str] = []
    for player, controller in enumerate(ordered[:maximum], start=1):
        fields = {
            "index": controller["index"],
            "guid": controller["guid"],
            "name": controller["name"],
            "devicepath": controller["path"],
            "nbbuttons": controller["nbbuttons"],
            "nbhats": controller["nbhats"],
            "nbaxes": controller["nbaxes"],
        }
        for suffix, value in fields.items():
            result.extend((f"-p{player}{suffix}", str(value)))
    return result


def mount_call(
    source: str | None,
    target: str,
    flags: int,
    filesystem: str | None = None,
    data: str | None = None,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = source.encode() if source is not None else None
    filesystem_bytes = filesystem.encode() if filesystem is not None else None
    data_bytes = data.encode() if data is not None else None
    result = libc.mount(source_bytes, target.encode(), filesystem_bytes, flags, data_bytes)
    if result != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), target)


def enter_ordered_device_namespace(
    session: Path, natural: list[dict[str, Any]], ordered: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if len(ordered) > len(natural):
        raise RuntimeError(
            f"no se pueden asignar {len(ordered)} controles sobre {len(natural)} dispositivos"
        )
    os.unshare(os.CLONE_NEWNS)
    mount_call(None, "/", MS_REC | MS_PRIVATE)
    stage = session / "devnodes"
    stage.mkdir(mode=0o700)

    targets = [controller["path"] for controller in natural]
    staged: list[Path] = []
    for index, controller in enumerate(ordered):
        node = stage / str(index)
        node.touch(mode=0o600)
        mount_call(controller["path"], str(node), MS_BIND)
        staged.append(node)
    for node, target in zip(staged, targets[: len(staged)], strict=True):
        mount_call(str(node), target, MS_BIND)
    for index, target in enumerate(targets[len(staged) :], start=len(staged)):
        mask = stage / f"unassigned-{index}"
        mask.touch(mode=0o000)
        mount_call(str(mask), target, MS_BIND)

    remapped = scan_sdl()
    if len(remapped) != len(ordered):
        raise RuntimeError(f"verificación SDL: esperados {len(ordered)}, obtenidos {len(remapped)}")
    assigned_targets = targets[: len(ordered)]
    for index, (actual, wanted, target) in enumerate(
        zip(remapped, ordered, assigned_targets, strict=True)
    ):
        if actual["path"] != target:
            raise RuntimeError(f"verificación SDL P{index + 1}: ruta {actual['path']} != {target}")
        if actual["guid"] != wanted["guid"] or actual["name"] != wanted["name"]:
            raise RuntimeError(f"verificación SDL P{index + 1}: el dispositivo no coincide")
        actual.update(
            {
                "arcade_player": wanted.get("arcade_player"),
                "usb_port": wanted.get("usb_port"),
                "source_path": wanted["path"],
            }
        )
    return remapped


def enter_ephemeral_config_overlay(session: Path) -> None:
    target = ROOT / "configs"
    upper = session / "configs-upper"
    work = session / "configs-work"
    upper.mkdir(mode=0o700)
    work.mkdir(mode=0o700)
    options = f"lowerdir={target},upperdir={upper},workdir={work}"
    mount_call("overlay", str(target), 0, "overlay", options)


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def multiplayer_entry(
    system: str, rom: Path, verify_hash: bool = False
) -> dict[str, Any] | None:
    if not MULTIPLAYER.exists():
        return None
    data = load_json(MULTIPLAYER)
    games = data.get("games", [])
    if not isinstance(games, list):
        raise ValueError("multiplayer.json: games debe ser una lista")
    normalized = str(rom.resolve()) if rom.exists() else str(rom)
    for entry in games:
        if not isinstance(entry, dict) or entry.get("system") != system:
            continue
        configured_rom = str(entry.get("rom", ""))
        if configured_rom in (normalized, rom.name):
            expected = entry.get("hash")
            if verify_hash and expected and rom.is_file():
                expected_text = str(expected).lower()
                if expected_text.startswith("sha1:"):
                    expected_text = expected_text.removeprefix("sha1:")
                if expected_text != file_sha1(rom).lower():
                    continue
            return entry
    return None


def temporary_batocera_config(session: Path, entry: dict[str, Any] | None) -> Path:
    target = session / "batocera.conf"
    shutil.copy2(BATOCERA_CONF, target)
    settings = entry.get("settings", {}) if entry else {}
    if not isinstance(settings, dict):
        raise ValueError("multiplayer.json: settings debe ser un objeto")
    if settings:
        with target.open("a", encoding="utf-8") as handle:
            handle.write("\n# EL_GORDO_SESSION_MULTIPLAYER\n")
            for key, value in sorted(settings.items()):
                if "\n" in str(key) or "\n" in str(value) or "=" in str(key):
                    raise ValueError(f"ajuste Multitap inválido: {key!r}")
                handle.write(f"{key}={value}\n")
    return target


def is_neogeo_content(system: str, rom: Path) -> bool:
    if system == "neogeo":
        return True
    if system != "fbneo":
        return False
    dat_path = ROOT.parent / "bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Neogeo only).dat"
    if not dat_path.is_file():
        return False
    shortname = rom.stem.casefold()
    try:
        for _, element in ET.iterparse(dat_path, events=("start",)):
            if element.tag in ("game", "machine") and str(element.get("name", "")).casefold() == shortname:
                return True
    except (ET.ParseError, OSError):
        return False
    return False


def apply_per_game_ephemeral_cleanup(entry: dict[str, Any] | None, log_path: Path) -> None:
    relative = entry.get("clear_mame_cfg") if entry else None
    if not relative:
        return
    relative_path = Path(str(relative))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"ruta MAME temporal inválida: {relative}")
    target = ROOT / "configs" / relative_path
    if target.is_file():
        target.unlink()
        log_line(log_path, "ephemeral_game_cfg_cleared", path=str(target))


def selected_p1_exit_watcher(
    launcher_module: Any,
    device_path: str,
    select_code: int,
    start_code: int,
    stop_event: threading.Event,
    requested_exit_event: threading.Event,
    log_path: Path,
) -> None:
    import evdev

    held_select = False
    try:
        device = evdev.InputDevice(device_path)
        while not stop_event.is_set():
            ready, _, _ = __import__("select").select([device.fd], [], [], 0.25)
            if not ready:
                continue
            for event in device.read():
                if event.type != evdev.ecodes.EV_KEY:
                    continue
                if event.code == select_code:
                    held_select = event.value != 0
                elif event.code == start_code and event.value == 1 and held_select:
                    process = getattr(launcher_module, "proc", None)
                    if process is not None and process.poll() is None:
                        requested_exit_event.set()
                        log_line(log_path, "p1_exit_combo", device=device_path)
                        process.terminate()
                    return
    except Exception as exc:
        log_line(log_path, "p1_exit_watcher_error", error=str(exc), device=device_path)


def patch_runtime(
    p1: dict[str, Any],
    log_path: Path,
    stop_event: threading.Event,
    entry: dict[str, Any] | None,
    system: str,
    rom: Path,
    choice: str,
    maximum: int,
    requested_exit_event: threading.Event,
    launch_trace: dict[str, Any],
) -> tuple[Any, threading.Thread]:
    import configgen.Emulator as emulator_module
    import configgen.emulatorlauncher as launcher_module
    from configgen.generators.duckstation.duckstationGenerator import DuckstationGenerator
    from configgen.generators.libretro.libretroGenerator import LibretroGenerator
    from configgen.generators.pcsx2.pcsx2Generator import Pcsx2Generator
    from configgen.generators.xenia.xeniaGenerator import XeniaGenerator
    from configgen.settings.unixSettings import UnixSettings
    from configgen.utils.configparser import CaseSensitiveConfigParser

    @contextlib.contextmanager
    def p1_only_hotkey_context(generator: Any, system: Any):
        context = dict(generator.getHotkeysContext())
        keys = dict(context.get("keys", {}))
        keys.pop("exit", None)
        subprocess.call(
            [
                "hotkeygen",
                "--new-context",
                "el_gordo_p1_only",
                json.dumps(keys),
            ]
        )
        try:
            yield
        finally:
            subprocess.call(["hotkeygen", "--default-context"])

    launcher_module.set_hotkeygen_context = p1_only_hotkey_context

    original_run_command = launcher_module.runCommand

    def tracked_run_command(command: Any) -> int:
        launch_trace["command"] = [str(item) for item in command.array]
        launch_trace["started_wall"] = time.time()
        started = time.monotonic()
        try:
            result = original_run_command(command)
            launch_trace["exit_code"] = result
            return result
        finally:
            launch_trace["duration_seconds"] = time.monotonic() - started
            process = getattr(launcher_module, "proc", None)
            if process is not None:
                launch_trace["pid"] = process.pid
                launch_trace["exit_code"] = process.returncode

    launcher_module.runCommand = tracked_run_command

    original_xenia_generate = XeniaGenerator.generate

    def xenia_generate_without_fixed_filter(self: Any, *args: Any, **kwargs: Any):
        command = original_xenia_generate(self, *args, **kwargs)
        command.env.pop("SDL_GAMECONTROLLER_IGNORE_DEVICES", None)
        return command

    XeniaGenerator.generate = xenia_generate_without_fixed_filter

    original_libretro_generate = LibretroGenerator.generate

    def libretro_generate_with_session_settings(self: Any, *args: Any, **kwargs: Any):
        command = original_libretro_generate(self, *args, **kwargs)
        runtime_settings = entry.get("retroarch_settings", {}) if entry else {}
        if not isinstance(runtime_settings, dict):
            raise ValueError("multiplayer.json: retroarch_settings debe ser un objeto")
        settings_path = ROOT / "configs/retroarch/retroarchcustom.cfg"
        settings = UnixSettings(settings_path, separator=" ")
        for key in (
            "input_enable_hotkey_btn",
            "input_enable_hotkey_axis",
            "input_exit_emulator_btn",
            "input_exit_emulator_axis",
        ):
            settings.save(key, "nul")
        if is_neogeo_content(system, rom):
            for player in range(1, maximum + 1):
                settings.save(f"input_player{player}_l_btn", "nul")
                settings.save(f"input_player{player}_r_btn", "nul")
        if runtime_settings:
            for key, value in runtime_settings.items():
                settings.save(str(key), str(value))
        settings.write()
        return command

    LibretroGenerator.generate = libretro_generate_with_session_settings

    original_duckstation_generate = DuckstationGenerator.generate

    def duckstation_generate_with_session_multitap(self: Any, *args: Any, **kwargs: Any):
        command = original_duckstation_generate(self, *args, **kwargs)
        mode = entry.get("duckstation_multitap_mode") if entry else None
        if mode:
            if mode not in ("Port1Only", "Port2Only", "BothPorts"):
                raise ValueError(f"modo DuckStation Multitap inválido: {mode}")
            settings_path = ROOT / "configs/duckstation/settings.ini"
            settings = CaseSensitiveConfigParser(interpolation=None)
            settings.read(settings_path)
            if not settings.has_section("ControllerPorts"):
                settings.add_section("ControllerPorts")
            settings.set("ControllerPorts", "MultitapMode", str(mode))
            slots = entry.get("duckstation_arcade_pad_slots") if entry else None
            if slots:
                if slots != [1, 3, 4, 5]:
                    raise ValueError(f"slots DuckStation inválidos: {slots}")
                generated = []
                for source in range(1, maximum + 1):
                    section = f"Pad{source}"
                    generated.append(dict(settings.items(section)) if settings.has_section(section) else {})
                for pad in range(1, 9):
                    section = f"Pad{pad}"
                    if settings.has_section(section):
                        settings.remove_section(section)
                    settings.add_section(section)
                    settings.set(section, "Type", "None")
                for values, destination in zip(generated, slots, strict=True):
                    section = f"Pad{destination}"
                    for key, value in values.items():
                        settings.set(section, key, value)
            with settings_path.open("w", encoding="utf-8") as handle:
                settings.write(handle, space_around_delimiters=False)
        return command

    DuckstationGenerator.generate = duckstation_generate_with_session_multitap

    original_pcsx2_generate = Pcsx2Generator.generate

    def pcsx2_generate_with_arcade_guitar(self: Any, *args: Any, **kwargs: Any):
        command = original_pcsx2_generate(self, *args, **kwargs)
        if system == "ps2" and entry and entry.get("preserve_player_order"):
            controllers = args[2] if len(args) > 2 else kwargs.get("playersControllers")
            if not isinstance(controllers, (list, tuple)) or len(controllers) != 4:
                raise RuntimeError("FIFA Street 2 requiere exactamente cuatro mandos seleccionados")
            selected_indices = [int(controller.index) for controller in controllers]
            if len(set(selected_indices)) != 4:
                raise RuntimeError("FIFA Street 2 recibió mandos SDL repetidos")

            settings_path = ROOT / "configs/PCSX2/inis/PCSX2.ini"
            settings = CaseSensitiveConfigParser(interpolation=None)
            settings.read(settings_path)
            if not settings.has_section("Pad") or not settings.getboolean("Pad", "MultitapPort1", fallback=False):
                raise RuntimeError("PCSX2 no activó Multitap en el Controller Port 1")
            if settings.getboolean("Pad", "MultitapPort2", fallback=False):
                raise RuntimeError("PCSX2 activó Multitap innecesario en el Controller Port 2")

            slots = ("Pad1", "Pad3", "Pad4", "Pad5")
            source_by_index: dict[int, tuple[str, dict[str, str]]] = {}
            for pad_number in range(1, 9):
                section = f"Pad{pad_number}"
                if not settings.has_section(section):
                    continue
                up_binding = settings.get(section, "Up", fallback="")
                match = re.match(r"^SDL-(\d+)/", up_binding)
                if match:
                    index = int(match.group(1))
                    if index in source_by_index:
                        raise RuntimeError(f"PCSX2 duplicó el mando SDL-{index}")
                    source_by_index[index] = (section, dict(settings.items(section)))

            if any(index not in source_by_index for index in selected_indices):
                raise RuntimeError("PCSX2 no generó una ranura para cada mando elegido")

            generated_sections = {
                section: dict(settings.items(section))
                for section in (f"Pad{number}" for number in range(1, 9))
                if settings.has_section(section)
            }
            for section in generated_sections:
                settings.remove_section(section)
            for destination, index in zip(slots, selected_indices, strict=True):
                settings.add_section(destination)
                values = source_by_index[index][1]
                for key, value in values.items():
                    settings.set(destination, key, re.sub(r"SDL-\d+", f"SDL-{index}", value))
            with settings_path.open("w", encoding="utf-8") as handle:
                settings.write(handle, space_around_delimiters=False)
            log_line(
                log_path,
                "pcsx2_multitap_order",
                rom=str(rom),
                profile=choice,
                players=[
                    {"player": number, "sdl_index": index, "pad_slot": slot}
                    for number, (index, slot) in enumerate(zip(selected_indices, slots, strict=True), start=1)
                ],
            )

        if choice != "arcade" or not entry or not entry.get("pcsx2_arcade_guitar"):
            return command
        settings_path = ROOT / "configs/PCSX2/inis/PCSX2.ini"
        settings = CaseSensitiveConfigParser(interpolation=None)
        settings.read(settings_path)
        for player in range(1, min(maximum, 2) + 1):
            section = f"Pad{player}"
            if settings.has_section(section):
                settings.remove_section(section)
            settings.add_section(section)
            sdl = f"SDL-{player - 1}"
            guitar_bindings = {
                "Type": "Guitar",
                "Deadzone": "0",
                "AxisScale": "1",
                "Up": f"{sdl}/DPadUp",
                "Down": f"{sdl}/DPadDown",
                "Select": f"{sdl}/Back",
                "Start": f"{sdl}/Start",
                "Green": f"{sdl}/FaceSouth",
                "Red": f"{sdl}/FaceEast",
                "Yellow": f"{sdl}/FaceWest",
                "Blue": f"{sdl}/FaceNorth",
                "Orange": f"{sdl}/LeftShoulder",
                "Tilt": f"{sdl}/RightShoulder",
            }
            for key, value in guitar_bindings.items():
                settings.set(section, key, value)
        with settings_path.open("w", encoding="utf-8") as handle:
            settings.write(handle, space_around_delimiters=False)
        return command

    Pcsx2Generator.generate = pcsx2_generate_with_arcade_guitar

    select_code, start_code = input_button_codes(p1)
    watcher = threading.Thread(
        target=selected_p1_exit_watcher,
        args=(
            launcher_module,
            p1["path"],
            select_code,
            start_code,
            stop_event,
            requested_exit_event,
            log_path,
        ),
        daemon=True,
    )
    watcher.start()
    return launcher_module, watcher


def selected_profile_controllers(
    ordered: list[dict[str, Any]], choice: str, entry: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not entry or not entry.get("exclusive_profile"):
        return ordered
    if choice not in ("arcade", "external"):
        raise ValueError(f"perfil exclusivo desconocido: {choice}")
    use_arcade = choice == "arcade"
    selected = [
        controller
        for controller in ordered
        if (controller.get("arcade_player") is not None) == use_arcade
    ]
    required = int(entry.get("max_players", 2))
    if len(selected) < required:
        label = "BOTONERA" if use_arcade else "JOYSTICK"
        raise RuntimeError(
            f"FIFA Street 2 + {label}: se requieren {required} controles del perfil elegido; "
            f"detectados {len(selected)}. No se mezclarán perfiles."
        )
    return selected


def run_official_launcher(
    session: Path,
    argv: list[str],
    system: str,
    rom_text: str,
    ordered: list[dict[str, Any]],
    cfg: dict[str, Any],
    log_path: Path,
) -> int:
    natural = scan_sdl()
    rom = Path(rom_text)
    entry = multiplayer_entry(
        system,
        rom,
        bool(cfg.get("verify_multiplayer_hash_on_launch", False)),
    )
    ordered = selected_profile_controllers(ordered, cfg["selected_profile"], entry)
    maximum = int(entry.get("max_players", 2)) if entry else 2
    maximum = max(1, min(maximum, int(cfg["max_players"]), len(ordered)))
    restrict_psx_multitap = bool(
        system == "psx" and entry and entry.get("adapter_type") == "PSX_MULTITAP"
    )
    restrict_assigned_devices = restrict_psx_multitap or bool(entry and entry.get("exclusive_profile"))
    assigned_order = ordered[:maximum] if restrict_assigned_devices else ordered
    remapped = enter_ordered_device_namespace(session, natural, assigned_order)
    enter_ephemeral_config_overlay(session)
    apply_per_game_ephemeral_cleanup(entry, log_path)
    launcher_args = strip_player_arguments(argv) + controller_arguments(remapped, maximum)
    temp_conf = temporary_batocera_config(session, entry)
    mount_call(str(temp_conf), str(BATOCERA_CONF), MS_BIND)

    import configgen.Emulator as emulator_module

    emulator_module.BATOCERA_CONF = temp_conf
    stop_event = threading.Event()
    requested_exit_event = threading.Event()
    launch_trace: dict[str, Any] = {}
    launcher_module, watcher = patch_runtime(
        remapped[0],
        log_path,
        stop_event,
        entry,
        system,
        rom,
        cfg["selected_profile"],
        maximum,
        requested_exit_event,
        launch_trace,
    )
    log_line(
        log_path,
        "launch",
        system=system,
        rom=rom_text,
        order=[
            {
                "player": index + 1,
                "name": controller["name"],
                "source": controller["source_path"],
                "arcade_player": controller.get("arcade_player"),
            }
            for index, controller in enumerate(remapped[:maximum])
        ],
        unassigned=[
            {
                "name": controller["name"],
                "source": controller["path"],
                "arcade_player": controller.get("arcade_player"),
            }
            for controller in ordered[maximum:]
        ],
        multitap=entry.get("adapter_type") if entry else None,
    )
    sys.argv = ["/usr/bin/emulatorlauncher", *launcher_args]
    launcher_result = 0
    try:
        launcher_module.launch()
    except SystemExit as exc:
        launcher_result = int(exc.code or 0)
    finally:
        stop_event.set()
        watcher.join(timeout=1)
        subprocess.call(["hotkeygen", "--default-context"])
    status = record_launch(
        system,
        rom,
        cfg["selected_profile"],
        entry,
        remapped,
        maximum,
        launch_trace,
        requested_exit_event.is_set(),
    )
    log_line(
        log_path,
        "launch_health",
        status=status,
        duration_seconds=launch_trace.get("duration_seconds"),
        exit_code=launch_trace.get("exit_code"),
    )
    return launcher_result


def diagnostic_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    natural = scan_sdl()
    result: dict[str, Any] = {
        "natural": natural,
        "profiles": {},
    }
    for choice in ("arcade", "external"):
        ordered, identities = classify_and_order(cfg, natural, choice)
        result["profiles"][choice] = {
            "players": [
                {
                    "player": index + 1,
                    "name": controller["name"],
                    "path": controller["path"],
                    "arcade_player": controller.get("arcade_player"),
                    "usb_port": controller.get("usb_port"),
                }
                for index, controller in enumerate(ordered[: int(cfg["max_players"])])
            ],
            "arcade_identities": identities,
            "duplicates": len({item["path"] for item in ordered}) != len(ordered),
        }
    return result


def namespace_profile_test(cfg: dict[str, Any], choice: str) -> None:
    natural = scan_sdl()
    ordered, _ = classify_and_order(cfg, natural, choice)
    session = Path(tempfile.mkdtemp(prefix=f"el_gordo_namespace_test_{choice}.", dir="/tmp"))
    session.chmod(0o700)
    try:
        pid = os.fork()
        if pid == 0:
            try:
                remapped = enter_ordered_device_namespace(session, natural, ordered)
                enter_ephemeral_config_overlay(session)
                if [item["name"] for item in remapped] != [item["name"] for item in ordered]:
                    os._exit(2)
                marker = ROOT / "configs/.el_gordo_ephemeral_test"
                marker.write_text("temporal\n", encoding="utf-8")
                if not marker.exists():
                    os._exit(3)
            except BaseException:
                os._exit(1)
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        result = os.waitstatus_to_exitcode(status)
        if result != 0:
            raise RuntimeError(f"falló la prueba aislada del perfil {choice}: {result}")
        if (ROOT / "configs/.el_gordo_ephemeral_test").exists():
            raise RuntimeError("la superposición temporal escribió fuera de la sesión")
    finally:
        shutil.rmtree(session, ignore_errors=True)


def fifa_street_profile_test(cfg: dict[str, Any]) -> None:
    entries = []
    for filename in ("FIFA Street 2.iso", "FIFA Street 2.chd"):
        entry = multiplayer_entry("ps2", Path("/userdata/roms/ps2") / filename)
        if (
            not entry
            or entry.get("max_players") != 4
            or not entry.get("exclusive_profile")
            or not entry.get("preserve_player_order")
            or entry.get("settings", {}).get("ps2.pcsx2_multitap") != "4"
        ):
            raise RuntimeError(f"{filename} no tiene el perfil exclusivo de cuatro jugadores")
        entries.append(entry)
    entry = entries[0]

    natural = scan_sdl()
    arcade_order, _ = classify_and_order(cfg, natural, "arcade")
    external_order, _ = classify_and_order(cfg, natural, "external")
    arcade = selected_profile_controllers(arcade_order, "arcade", entry)
    if len(arcade) != 4 or any(controller.get("arcade_player") is None for controller in arcade):
        raise RuntimeError("FIFA Street 2 BOTONERA no seleccionó cuatro botoneras")

    external = [controller for controller in external_order if controller.get("arcade_player") is None]
    if len(external) < 4:
        try:
            selected_profile_controllers(external_order, "external", entry)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("FIFA Street 2 JOYSTICK mezcló perfiles con menos de cuatro externos")
    else:
        selected = selected_profile_controllers(external_order, "external", entry)
        if len(selected) != 4 or any(controller.get("arcade_player") is not None for controller in selected):
            raise RuntimeError("FIFA Street 2 JOYSTICK no seleccionó cuatro externos exclusivos")

    synthetic = [
        {"index": index, "arcade_player": None}
        for index in range(4)
    ] + [
        {"index": index + 4, "arcade_player": f"P{index + 1}"}
        for index in range(4)
    ]
    selected_external = selected_profile_controllers(synthetic, "external", entry)
    selected_arcade = selected_profile_controllers(synthetic, "arcade", entry)
    if (
        len(selected_external) != 4
        or any(controller.get("arcade_player") is not None for controller in selected_external)
        or len(selected_arcade) != 4
        or any(controller.get("arcade_player") is None for controller in selected_arcade)
    ):
        raise RuntimeError("FIFA Street 2 no mantiene aislados los perfiles BOTONERA y JOYSTICK")


def parent_launch(argv: list[str], choice_override: str | None) -> int:
    cfg = technical_config()
    log_path = rotate_log(cfg)
    system, rom = extract_launch_identity(argv)
    lock_handle = LOCK_PATH.open("w")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        message = "Ya hay un lanzamiento administrado por el selector."
        log_line(log_path, "busy", system=system, rom=rom)
        show_error(message)
        return 1

    automatic_invocation = None
    if choice_override:
        choice = choice_override
    else:
        # A certifier transaction owns authorization for its entire ES launch
        # lifecycle. The marker remains only a first-invocation receipt.
        try:
            matched, match_reason, invocation = automatic_context.authorize_invocation(
                system=system, rom=rom, dispatcher_pid=os.getpid(), ppid=os.getppid())
        except Exception as exc:
            matched, match_reason, invocation = False, "CONTEXT_CHECK_ERROR:" + type(exc).__name__, None
        if matched:
            automatic_invocation = invocation
            choice = "external"
            marker_consumed = remove_owned_marker(invocation['transaction_id'], owner='full_game_certifier')
            log_line(
                log_path,
                "automatic_selector_context_choice",
                system=system,
                rom=rom,
                choice="JOYSTICKS PRIMERO",
                internal_choice=choice,
                automatic_context_match=True,
                transaction_id=invocation['transaction_id'],
                selector_invocation_id=invocation['selector_invocation_id'],
                phase=invocation['phase'],
                one_shot_consumed=marker_consumed,
            )
        else:
            # A certifier marker without a matching active context is not an
            # authorization. Other legacy marker owners keep their old path.
            marker = read_marker(BOOT_AUDIT_ONCE)
            if automatic_context.ACTIVE_CONTEXT.exists() or (marker and marker.get('owner') == 'full_game_certifier'):
                log_line(log_path, "automatic_context_fail_closed", system=system,
                         rom=rom, reason=match_reason)
                return 1
            else:
                choice = consume_boot_audit_once(system, rom)
                if choice:
                    log_line(log_path, "boot_audit_auto_choice", system=system, rom=rom,
                             choice=marker.get('choice') if marker else 'BOTONERA',
                             internal_choice=choice, one_shot_consumed=True)
                else:
                    choice = None
            if choice is None:
                log_line(log_path, "automatic_selector_context_no_match", system=system,
                         rom=rom, reason=match_reason)
    if choice is None:
        selector_cfg = cfg.get("selector", {})
        command = [str(TOOLS / "selector_controles"), "--timeout", str(selector_cfg.get("timeout_seconds", 0))]
        if not selector_cfg.get("fullscreen", True):
            command.append("--windowed")
        try:
            selected = subprocess.run(command, text=True, capture_output=True, check=False)
        except Exception as exc:
            log_line(log_path, "selector_error", system=system, rom=rom, error=str(exc))
            show_error("Falló el selector de controles. Se canceló el lanzamiento.")
            return 1
        choice = selected.stdout.strip()
        if selected.returncode != 0 or choice not in ("arcade", "external", "cancel"):
            log_line(
                log_path,
                "selector_error",
                system=system,
                rom=rom,
                returncode=selected.returncode,
                stdout=selected.stdout,
                stderr=selected.stderr,
            )
            show_error("Falló el selector de controles. Se canceló el lanzamiento.")
            return 1
    if choice == "cancel":
        log_line(log_path, "cancel", system=system, rom=rom)
        return 0

    if automatic_invocation is not None:
        decision, reason = automatic_context.claim_emulator_launch(
            automatic_invocation,
            system=system,
            rom=rom,
            dispatcher_pid=os.getpid(),
            ppid=os.getppid(),
        )
        if decision != "ALLOW":
            event = "automatic_emulator_launch_suppressed" if decision == "SUPPRESS" else "automatic_emulator_launch_refused"
            log_line(
                log_path,
                event,
                system=system,
                rom=rom,
                transaction_id=automatic_invocation.get("transaction_id"),
                selector_invocation_id=automatic_invocation.get("selector_invocation_id"),
                decision=decision,
                reason=reason,
            )
            # A proven duplicate is a successful no-op for ES; an ambiguous
            # certification context fails closed and never reaches configgen.
            return 0 if decision == "SUPPRESS" else 1
        log_line(
            log_path,
            "automatic_emulator_launch_claimed",
            system=system,
            rom=rom,
            transaction_id=automatic_invocation.get("transaction_id"),
            selector_invocation_id=automatic_invocation.get("selector_invocation_id"),
            reason=reason,
        )

    try:
        natural = scan_sdl()
        ordered, _ = classify_and_order(cfg, natural, choice)
        if not ordered:
            raise RuntimeError("no hay mandos asignables")
        session = Path(tempfile.mkdtemp(prefix="el_gordo_controller_session.", dir="/tmp"))
        session.chmod(0o700)
        cfg["selected_profile"] = choice
        pid = os.fork()
        if pid == 0:
            try:
                result = run_official_launcher(session, argv, system, rom, ordered, cfg, log_path)
            except BaseException as exc:
                log_line(log_path, "dispatcher_error", system=system, rom=rom, error=repr(exc))
                try:
                    record_launch(
                        system,
                        Path(rom),
                        choice,
                        multiplayer_entry(system, Path(rom)),
                        [],
                        0,
                        {
                            "started_wall": time.time(),
                            "duration_seconds": 0.0,
                            "exit_code": 1,
                            "command": [],
                        },
                        False,
                    )
                except Exception as database_exc:
                    log_line(log_path, "health_database_error", error=repr(database_exc))
                os._exit(1)
            os._exit(result)
        _, status = os.waitpid(pid, 0)
        result = os.waitstatus_to_exitcode(status)
        if last_launch_failed(rom):
            show_error("El juego se cerró antes de lo esperado. El diagnóstico quedó registrado.")
        elif result != 0:
            show_error("El lanzamiento se canceló por un error en el orden temporal de controles.")
        return result
    except Exception as exc:
        log_line(log_path, "dispatcher_error", system=system, rom=rom, error=repr(exc))
        show_error("El lanzamiento se canceló por un error en el orden temporal de controles.")
        return 1
    finally:
        if "session" in locals():
            shutil.rmtree(session, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--simulate-choice", choices=("arcade", "external", "cancel"))
    known, remaining = parser.parse_known_args()
    try:
        cfg = technical_config()
        if known.self_test:
            payload = diagnostic_payload(cfg)
            if payload["profiles"]["arcade"]["duplicates"] or payload["profiles"]["external"]["duplicates"]:
                raise RuntimeError("el diagnóstico encontró dispositivos repetidos")
            fifa_street_profile_test(cfg)
            namespace_profile_test(cfg, "arcade")
            namespace_profile_test(cfg, "external")
            print("DISPATCHER_SELF_TEST_OK")
            return 0
        if known.diagnose:
            print(json.dumps(diagnostic_payload(cfg), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        return parent_launch(remaining, known.simulate_choice)
    except Exception as exc:
        print(f"controller_dispatcher: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
