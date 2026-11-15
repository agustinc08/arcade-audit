# Bucle de reparación — causas raíz conocidas

- No se ejecutaron retries en esta fase: no hubo lanzamientos nuevos.
- Fallos históricos no se convierten a NOT_TESTED; se mantienen en `arcade_games_audit.csv` y reportes BATCH.
- Preflight smoke actual: ES idle, no juego, sin marker/procesos; diferencia protegida única = `batocera.conf` con 18 overrides autorizados posteriores al backup de noviembre 13.
- El baseline del runner antiguo no es reutilizable porque su restaurador repondría esa versión antigua. La causa fue reconciliada; no hubo una modificación no explicada del sistema.
- Audio: default WirePlumber apunta al sink del DualShock 4 en vez de HDMI; HDMI rule instalada coincide con BDF obsoleto. Sigue abierto.
- Contenido arcade: recurrencias de missing parent/member/BIOS/CHD descritas en los reportes BATCH y planes; no hubo reparación/descarga.

## Política de retry

Primer fallo nuevo => RETRY_REQUIRED; se limpia estado y se usa segundo intento independiente sólo tras restore verificado. Un PASS tras fallos previos se marca FLAKY. Dos fallos repetidos => CONFIRMED_FAIL/NEEDS_REPAIR. Los fingerprints deben incluir sistema/core/dependencia/identidad del error.
