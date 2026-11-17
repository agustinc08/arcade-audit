# Próxima tarea física

TASK: CTRL-REPRESENTATIVE-SAMPLE — Certificar muestra física representativa de controles

TEST:
Final Fight 2

GAME: mame:ffight2b.zip

PRESS:
Fighting, six-button; MAME-current BOOT_OK. Verify no duplicate/double inputs and exit combo.

WHY:
14 secuencias físicas siguen pendientes; no inferir control desde AUTO_PASS.

STEPS:
Probar muestra acordada: P1/P2 fighter, MAME 4P, beat-em-up, deporte y joystick externo.

EVIDENCE:
- manual_physical_test_queue.csv
- reports/ARCADE_CONTROL_CERTIFICATION.md

DO NOT CHANGE:
- No remapear P1-P4 durante la prueba
- No declarar juegos físicos certificados sin observación

EXPECTED:
Resultados humanos registrados por secuencia y controles/restore sin regresión.
