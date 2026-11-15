# Inventario de sistemas

La reconciliación detecta 51 sistemas con al menos una entrada de gamelist (de 253 IDs configurados en ES y 254 directorios visibles). `full_game_certification.csv` incluye 8.426 registros deduplicados y comprueba existencia de la ruta de contenido asociada; no recorre payloads completos ni valida BIOS/CHD por checksum. Hay 8.400 rutas presentes y 26 entradas de gamelist sin archivo localizado.

Se prepararon 51 archivos `CERTIFICATION_<SYSTEM>.md` con resumen por sistema. Todos separan historial de BOOT del auto-cert nuevo; ninguna consola se lanzó en esta fase. No se hicieron deduplicaciones/borrados. El siguiente trabajo prioriza PS2/PS1/Dreamcast/N64, colecciones multijugador y favoritos; extensas NES/GBA/GB/GBC pasan luego por curation estática y revisión regional antes de gastar tiempo en pruebas de baja prioridad.
