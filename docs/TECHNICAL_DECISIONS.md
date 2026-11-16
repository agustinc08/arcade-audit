# Decisiones técnicas permanentes

Estas decisiones reflejan evidencia y reglas autorizadas del proyecto; revisar si aparece evidencia nueva.

1. **Core global MAME: `mame078plus`.** Se conserva el core predeterminado y se utilizan overrides individuales sólo cuando una prueba real los valida.
2. **Lanzamiento por ruta oficial.** Las pruebas de invitado pasan por EmulationStation, `controller_dispatcher`, selector y launcher Batocera; un lanzamiento directo del emulador no certifica la experiencia real.
3. **Identidad extremo a extremo.** La ROM solicitada debe coincidir con la informada por ES/dispatcher y la recibida por el core/launcher adecuado.
4. **Restore por transacción.** Volver al estado inmediatamente previo al test con hashes y guardas de conflicto; nunca a un snapshot histórico completo.
5. **AUTO_CERTIFIED ≠ CONTROL_CERTIFIED.** Un boot/runtime correcto no demuestra botones físicos ni P1–P4 simultáneos.
6. **Guest Ready requiere controles y salida certificados.** No elevar automáticamente los juegos de boot a Guest Mode.
7. **P1–P4 se identifican por USB/event/perfil.** `jsN` es complementario y puede cambiar de orden.
8. **No actualizar Batocera sin evaluación y regresión.** La versión actual verificada es 43.1; no se actualiza en esta auditoría.
9. **No exponer API/servicios de Batocera a WAN.** El acceso remoto futuro se diseña por LAN/VPN privada; no abrir port forwarding.
10. **Publicación GitHub aislada del arcade.** Se usa un publisher HTTPS/REST con token local, allowlist y scans. La red/publisher no es dependencia de juegos/arranque.
11. **No distribuir contenido comercial.** ROMs, BIOS, CHD, saves, NVRAM y media pesada quedan fuera del repo; el contenido faltante se documenta por nombre, tamaño y CRC.
12. **No certificar sin evidencia.** Input sintético/software no certifica botones físicos; metadata de jugadores no prueba simultaneidad.

## Preguntas abiertas

- ¿La captura X11 actual puede clasificar juegos negros correctamente con todos los renderers? `gunbird2` sigue bajo revisión.
- ¿El audio HDMI persiste al desconectar/reconectar DS4 y tras reboot? Faltan ambas pruebas físicas.
