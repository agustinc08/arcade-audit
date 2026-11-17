# Certificación prioritaria — priority_batch_10

- Considerados: 100
- Lanzados: 100
- AUTO_PASS: 98
- GAME_FAIL: 2
- STATIC_FAIL: 0
- FLAKY: 0
- ENGINE_FAIL activos: 0
- Restores: 100/100
- Restore failures: 0
- Audio route changes: 0
- Wrong dispatch: 0
- NEXT_GAME: `mame:/userdata/roms/mame/wndrplnt.zip`

## SESSION INTERRUPTION

- Hubo una desconexión de la sesión SSH/Codex cuando se habían observado aproximadamente 69/100 entradas.
- Al inspeccionar el estado recuperado ya no había un proceso `full_game_certifier.py`; no se inició otro certifier ni se repitieron Batches 1–9.
- La evidencia local demuestra que el proceso original continuó: Batch 10 terminó a las 23:21:11 con 100/100 resultados terminales y 100/100 restores; luego Batch 11 alcanzó 10 entradas antes de pausarse por un `ENGINE_FAIL` en `xmultipl`.
- `CERTIFIER_SESSION_DEPENDENCY: NO` según esa evidencia de progreso posterior a la desconexión. El PID/argv ya no existía al momento de la inspección; no se pudo recuperar su PID histórico.
- Progreso recuperado de Batch 10: 100/100. Aproximadamente 31 entradas se completaron después del último estado observado (69/100); no se repitió ningún juego de Batch 10.
- Se encontró una transacción abierta `20261116T232721_b94c27f525`, etiquetada `xexex`, en `PRE_STATE`. Las diez rutas coincidían con su snapshot previo. Se respaldó el manifest y se ejecutaron `certification_transaction.py seal` y `restore`; quedó `RESTORE_VERIFIED` 10/10. `batocera.conf` mantuvo SHA-256 `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2` antes y después, y el marker quedó ausente.
- Esa transacción de `xexex` se creó después de que Batch 11 ya tuviera un resultado terminal `AUTO_PASS` para el mismo juego. No hay resultado ni evidencia de un segundo lanzamiento, y las rutas seguían intactas; sin embargo, sí hubo una selección/transacción duplicada y el self-check de Batch 11 no pasa. La causa no está determinada.
- Los agregados propios de Batch 10 concuerdan. Tras el avance parcial de Batch 11, el checkpoint universal y el CSV también coinciden (`AUTO_CERTIFIED=897`; cursor `xsleena`, igual al primer candidato de la cola determinística local), pero `arcade_master_checkpoint.json` aún refleja el cierre de Batch 10 (`AUTO_CERTIFIED=888`, 909 transacciones, cursor `wndrplnt`). La reconciliación global posterior a Batch 11 queda `FAIL/PENDIENTE`; no se reescribió el checkpoint master con un lote incompleto.
- Resultados de Batch 10 conservados: `tetris` y `vigilant` siguen `GAME_FAIL`; `tgmj` sigue `AUTO_PASS` con su sospecha visual preservada. No se modificaron esos resultados.
- GitHub ya contenía Batch 10 en `5110e8e1a0186a06ee9be43a698ca28ca63448b6` (`arcade: certify priority batch 10`); SHA confirmado mediante la API.
- Estado al cerrar esta reconciliación: Batch 10 `COMPLETE`; Batch 11 `PAUSED_ENGINE_FAILURE`. El diagnóstico actual no encuentra EmulationStation y la API local no responde, por lo que no se lanzaron más juegos.
- `FULL_GAME_CERTIFICATION_SUMMARY.md` se regeneró desde el checkpoint universal y el CSV: `REPORT_RECONCILIATION_PASS`, con `ENGINE_FAIL_ACTIVE=1`. `ARCADE_CURRENT_STATE.md` no se regeneró porque su constructor exige API y diagnóstico live de controles, ambos no disponibles.

## Seguimiento posterior (2026-11-16, 23:34 local)

La nota anterior sobre API/EmulationStation no disponible describe el momento inicial de la interrupción. Después se canceló explícitamente el selector abierto con Escape; una nueva lectura confirmó `/isIdle=true`, `runningGame=NO GAME RUNNING`, marker ausente y cero procesos de la cadena launcher/selector/emulator. HDMI quedó en `alsa_output.pci-0000_01_00.1.hdmi-stereo`; `batocera.conf` conservó SHA-256 `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2`; P1–P4 y los 18 overrides permanecieron intactos.

Batch 11 continuó después de Batch 10: nueve juegos se lanzaron y pasaron; `xmultipl` se detuvo antes de `/launch` porque `boot_audit_once.json` apareció entre el snapshot transaccional y la apertura exclusiva. El certifier restauró el marker ausente de PRE_STATE, pero no se conservó el contenido ni se identificó su escritor; se mantiene un `ENGINE_FAIL` activo y no se autoriza continuar lanzando. Ver `PRIORITY_CERTIFICATION_BATCH_11.md`.
