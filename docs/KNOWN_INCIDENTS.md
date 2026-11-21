# Incidentes conocidos y lecciones

Los resultados de compatibilidad por juego viven en el checkpoint/CSV de certificación. Este documento conserva incidentes estructurales, guardas y estados; no sustituye evidencia runtime.

| ID | Fecha | Síntoma / causa | Resolución o guarda | Estado |
|---|---|---|---|---|
| LAUNCH-001 | 2026-11-15 | Se solicitó `altair` pero EmulationStation informó `kinstb`; el dispatcher recibió la ROM equivocada y no llegó a RetroArch. | Se preservó evidencia, se reinició EmulationStation por su ruta controlada y el control positivo `altair` pasó con identidad extremo a extremo. `kinstb` resultó ser un bootleg SNES, excluido de prioridad arcade. | MITIGADO; vigilar identidad en cada lanzamiento |
| AUDIO-001 | 2026-11 | Un endpoint de audio del gamepad podía desplazar HDMI como default. | Política persistente acotada de selección HDMI iniciada por `custom_service`; HDMI se mantuvo default durante pruebas de juegos. | MITIGADO; falta reconexión física DS4 y prueba post-reboot |
| RESTORE-001 | 2026-11-15 | Un runner histórico podía restaurar una copia vieja de `batocera.conf`, perdiendo overrides legítimos. | Motor transaccional usa el estado inmediatamente anterior, hash/conflict guard y restore verificado por transacción; sin restaurar backups históricos completos. | MITIGADO; lote 5: 409 restores verificados |
| GITHUB-001 | 2026-11-15 | Guard `LARGE_CHANGESET` detuvo una publicación inicial de documentación. | Se auditó el manifiesto exacto, se autorizó sólo ese changeset y no se redujeron límites globales. | CERRADO para ese changeset |
| CLEANUP-001 | 2026-11 | `hotkeygen` produjo `ProcessLookupError` al enviar señal a un PID que ya terminó correctamente. | Separar la carrera de limpieza del resultado del juego; exigir salida, ES idle y restore como evidencia. | MITIGADO; no cuenta como GAME_FAIL si se demuestra la carrera |
| VISUAL-001 | 2026-11-16 | `gunbird2` mantuvo captura negra en T+5/T+15, aunque el proceso estuvo estable, exit 0, HDMI correcto y restore verificado. | Se agrupó con el root issue visual; falta contrastar otra ruta de captura/renderer. No reintentar automáticamente. | EN INVESTIGACIÓN |
| CONTENT-001 | 2026-11-16 | Preflight de MAME actual para `evosocc` requiere `mx27l1000-alt.u14` dentro del set BIOS `crysbios`; el ZIP contiene sólo la variante base. | Registrar miembro, CRC `1e8175c8`, tamaño 131072; no editar/descargar ROMs. | ABIERTO |
| GAME-001 | 2026-11 | `mvp` produjo SIGSEGV en MAME 0.78 Plus; `hoops95` tiene CRC incorrecto en `hoops.b2`. | Mantener en repair queue; no relanzar hasta análisis/contenido correcto. | ABIERTO |
| SELECTOR-001 | 2026-11-20 | Un marker one-shot dejó sin autorización a la segunda llamada del selector. Se implementó contexto de autorización por transacción con identidad estable; el retry de Doom eligió `JOYSTICKS PRIMERO` y pasó `safety_after`. ES abrió otra cadena Doom después del cierre de contexto; el motivo/origen de esa apertura sigue UNKNOWN y el selector permaneció manual/fail-closed. | Mantener la selección manual. No aceptar llamadas tardías por ROM/tiempo solamente. Correlacionar nueva evidencia de ES antes de reanudar certificación. | EN INVESTIGACIÓN |
| AUTOPILOT-0068-001 | 2026-11-20 | El retry único terminó su batch y el contador `max_batches=1` se reinició; el worker avanzó a Batch 69. MrBoom no alcanzó a iniciar el emulador, pero dejó un `SYSTEM_SAFETY_FAILURE / ES_LAUNCH_PROCESS_ACTIVE` con restore verificado. | Se añade parada terminal específica después de publicar el batch de un retry único; prueba sintética y publicación pendientes. No modificar ni reconciliar a mano el resultado Batch 69. | EN PRUEBA |

## Proceso de certificación

El visual checker es una señal heurística. `BLACK_SCREEN_SUSPECT` no prueba por sí solo un juego roto. `AUTO_CERTIFIED` no significa control físico certificado ni Guest Ready.
