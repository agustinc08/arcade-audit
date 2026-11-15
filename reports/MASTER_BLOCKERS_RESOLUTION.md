# Resolución de bloqueos del Master Audit

Fecha: 2026-11-15T10:52:13+00:00

## AUDIO

Causa observada: el default de salida era el sink USB del DualShock 4 pese a existir HDMI; la regla de prioridad antigua bajo `/etc/wireplumber` apuntaba a un BDF obsoleto. Se instaló una política mínima en `/userdata/system/el_gordo_tools/arcade_audio_policy_service.sh`, llamada por el `custom_service` ya habilitado. El helper encuentra HDMI por `node.name` estable, resuelve el ID de runtime y establece/verifica el default. El endpoint de audio del DS4 y sus controles permanecen disponibles. Durante el positivo `altair`, HDMI siguió default durante 21,25 s. Estado: `AUDIO_POLICY_INSTALLED`; reconexión física y reboot validation pendientes.

## RESTORE TRANSACCIONAL

No se usa el runner histórico ni sus baselines viejos. `/userdata/system/el_gordo_tools/certification_transaction.py` crea snapshots acotados por `transaction_id`, guarda pre/post SHA, verifica conflicto concurrente antes de tocar archivos y restaura sólo al PRE_STATE de esa misma prueba. Self-test pasó para archivo, árbol existente, árbol nuevo y `RESTORE_CONFLICT`.

Control positivo `altair` por ES API → `controller_dispatcher` → launcher oficial → RetroArch/MAME actual: POST 200; core exacto `/usr/lib/libretro/mame_libretro.so`; cmdfile `altair.cmd`; proceso estable 21,25 s; HDMI monitorizado; `game_health` id 8174, exit 0/signal null; retorno a ES. Transaction `20261115T074956_d283099c84` restauró 62 paths, incluidos `/userdata/saves/mame/mame` y `/userdata/saves/mame/plugins`; `batocera.conf` SHA before/after idéntico `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2`. Resultado `TRANSACTIONAL_RESTORE=PASS` para este adaptador MAME.

En el control previo el runner viejo del experimento no cubría esos árboles; se identificaron los ficheros generados ausentes en PRE_STATE, se quitaron únicamente tras comprobar esa ausencia y se verificó el baseline. El motor actualizado ahora incluye esos árboles explícitamente; el segundo positivo verificó la restauración de forma transaccional. No hubo cambios en ROM/BIOS/CHD, mappings, selector, dispatcher, core global u overrides.

## GITHUB

El guard normal rechazó legítimamente un changeset grande y sigue intacto. La revisión identificó solamente artefactos permitidos del Master Audit; el único delete remoto era `data/github_api_publish_test.json`, evidencia de test autorizada, y se recuperó byte por byte en el source local, por lo que el plan final debe tener cero deletions. Se añadió una autorización one-time ligada al repo/branch/HEAD y lista exacta de path/status/size/SHA, con expiración/digest; no es un bypass genérico. Publicación aún pendiente de regenerar inventory, scans, validar manifest exacto y confirmar SHA remoto.

## FBNEO

`FBNEO_DAT=VERIFIED`: DAT runtime Batocera v1.0.0.03 localizado en `/usr/share/batocera/datainit/bios/fbneo` y `/userdata/bios/fbneo`; hashes iguales y versión coincide con `fbneo_libretro.info`. CRC/tamaño completos de `sfiii3` y `captcomm` coinciden. No se lanzó ningún candidato FBNeo.

## CERTIFIER PILOT

El control `altair` sólo valida la cadena y restore transaccional; no es certificación nueva. `FULL_CERTIFIER_READY=NO`: `full_game_certifier.py` sigue siendo un planificador con lanzamiento explícitamente bloqueado y no tiene adapters por sistema ni el piloto variado de 10 juegos. No se inicia una pasada masiva. Próximo paso técnico: adapters por sistema con rutas persistentes allowlisted, verificación de identidad/core/audio/retorno y estados por juego; luego piloto de 10. Mantener muestreo HDMI en cada ejecución.

## Estado protegido

ES activo y API idle; no game running; marker ausente; no procesos launcher/emulator residuales. Core global `mame078plus`; 18 overrides; P1–P4 esperados; `batocera.conf` SHA igual al baseline. Sin regresión detectada.
