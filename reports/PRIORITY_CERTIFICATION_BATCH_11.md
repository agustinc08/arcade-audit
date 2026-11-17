# Certificación prioritaria — Batch 11 (parcial, pausado)

Fecha de la pausa: 2026-11-16, 23:27 local.

- Considerados por la cola: 100.
- Juegos lanzados realmente por EmulationStation: 9.
- AUTO_PASS: 9 (`wndrplnt`, `wow`, `wrally`, `ws`, `wseries`, `wwfmania`, `wwjgtin`, `xevious`, `xexex`).
- GAME_FAIL: 0.
- STATIC_FAIL: 0.
- Transacciones iniciadas: 10; las 10 quedaron con `RESTORE_VERIFIED` en sus manifiestos.
- Fallo de motor activo: 1; sin `WRONG_GAME_DISPATCH`, cambio de audio ni restore failure.
- El décimo candidato, `xmultipl.zip`, no llegó a `POST /launch`: la creación exclusiva de `/userdata/system/state/boot_audit_once.json` falló con `FileExistsError`.
- El juego no fue clasificado como fallo de contenido o de ejecución.

## Incidente y límite de evidencia

El manifiesto de la transacción `20261116T232721_823ec5e49e` indica que el marker estaba ausente al tomar PRE_STATE y presente al capturar POST_STATE. La apertura con modo exclusivo falló, así que el certifier no creó el marker. La restauración dejó el archivo ausente, igual que el PRE_STATE, y obtuvo `RESTORE_VERIFIED`; sin embargo, no quedó preservado el contenido del marker que apareció durante la carrera y su escritor no pudo identificarse. Por eso no se considera resuelta la concurrencia ni se autoriza otro lanzamiento.

Durante la recuperación posterior, EmulationStation estaba en el selector de controles colgado tras el retorno de `xexex`. Se canceló el selector con Escape; la API volvió a `idle`, `runningGame` indicó `NO GAME RUNNING` y desapareció la cadena dispatcher/selector. Una transacción local `20261116T232721_b94c27f525` corresponde al snapshot/restore de recuperación de `xexex` (PRE_STATE y POST_STATE del marker ausentes); no es evidencia de un segundo lanzamiento ni identifica al escritor del marker. La transacción de `xmultipl` capturó marker presente en POST_STATE y su restore lo quitó para volver al PRE_STATE ausente. Esto restableció el estado del frontend, pero no identifica quién creó el marker.

## Estado al pausar

- Checkpoint: `PAUSED_ENGINE_FAILURE`.
- `engine_fail_active`: 1.
- Cursor de cola ordinaria que devuelve el código: `mame:/userdata/roms/mame/xsleena.zip`.
- `xmultipl` conserva un registro `ENGINE_FAIL` pre-launch y queda pendiente de una vía explícita de reintento después de reparar/validar el guard de concurrencia. El cursor ordinario no autoriza lanzamientos mientras el checkpoint siga pausado.
- No se modificaron ROMs, cores, overrides, mappings ni resultados históricos.

Evidencia transaccional: `runtime/20261116T232721_823ec5e49e/manifest.json` y `result.json`. La captura del selector se conservó localmente en el runtime de recuperación, no se exporta como media.
