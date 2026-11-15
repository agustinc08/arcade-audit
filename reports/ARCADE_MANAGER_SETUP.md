# Arcade Manager — preparación read-only

Herramienta: `/userdata/system/el_gordo_tools/arcade_manager.py`. Usa solamente Python estándar, sirve UI local y endpoints GET `/api/status`, `/api/games`. POST devuelve 405; no hay acciones de control remoto, no crea servicio/autostart, no se inicia en esta fase. Default bind `127.0.0.1:8765`. Para una sesión LAN deliberada, el usuario puede ejecutar manualmente `python3 /userdata/system/el_gordo_tools/arcade_manager.py --host <IP-LAN>`; no configurar port forwarding, WAN ni EmulationStation API externa. Acceso remoto futuro debe ser por VPN privada.

No requiere contraseña porque sólo expone lectura y metadatos; los endpoints no publican secrets ni rutas de saves. Las acciones administrativas, Guest/Admin, cierre de juego y reinicio ES no están implementadas. No se inspeccionó/alteró `custom.sh` y no hay autostart.
