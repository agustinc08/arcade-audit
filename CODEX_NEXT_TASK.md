# Próxima tarea requerida por Codex

TASK: VISUAL-BLACK-CAPTURE — Investigar sospechas de captura negra

WHY:
19 casos BLACK_SCREEN_SUSPECT; el mecanismo de captura puede no representar salida visible.

EVIDENCE:
- arcade_master_checkpoint.json: CERT-004
- reports/ROOT_CAUSES.md

FILES:
- full_game_certification_checkpoint.json
- reports/ARCADE_VISUAL_MEDIA_AUDIT.md

DO NOT CHANGE:
- No marcar BLACK_SCREEN_SUSPECT como GAME_FAIL automáticamente
- No relanzar juegos masivamente

SUCCESS CRITERIA:
Explicación aceptada, backend identificado o tarea manual de TV documentada.

AFTER COMPLETION:

