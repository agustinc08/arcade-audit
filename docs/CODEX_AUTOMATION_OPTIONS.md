# Opciones de automatización de Codex

Estado: investigación read-only; no activado.

La documentación oficial describe `codex exec` como modo no interactivo para
scripts/CI, con sandbox y salida JSONL mediante `--json`. Una integración futura
requiere handoff explícito, sandbox mínimo y revisión humana del patch. Esta
versión del Autopilot nunca arranca Codex ni ejecuta un loop de IA.

Fuente: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

En este Batocera, `/userdata/system/.local/bin/codex` es un wrapper Node
(`#!/usr/bin/env node`), pero `node` no está disponible en PATH; el CLI local no
arranca. No se instaló paquete ni runtime. Por eso la capacidad documentada no
está disponible en el equipo.

Posible diseño futuro: un operador aprueba un `CODEX_NEXT_TASK.md` y ejecuta
`codex exec` con filesystem/red restringidos. Codex produce un patch/informe
revisable; Autopilot no lo aplica automáticamente. Integración desactivada.
