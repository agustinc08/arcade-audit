# Hardware del gabinete

Inventario de lectura de Batocera, 2026-11-16. Se omiten números de serie, MAC, IP y credenciales.

| Componente | Dato observado | Fuente / límite |
|---|---|---|
| Sistema | Batocera 43.1, Linux 6.18.16, x86_64 | `/etc/os-release`, `uname` |
| CPU | Intel Core i5-12400F, 6 núcleos / 12 hilos | `lscpu` |
| GPU | NVIDIA GeForce GTX 1060 3 GB, GP106, PCI `01:00.0` | `lspci`; modelo coincide con ficha previa |
| RAM | 16 GiB instalados; el sistema reportó unos 15 GiB utilizables | `free -h` |
| Motherboard | Gigabyte H610M K DDR4 | DMI/sysfs y ficha previa |
| Audio HDMI | NVIDIA GP106 HDA, PCI `01:00.1` | `lspci`, ALSA |
| Red cableada | Realtek RTL8111/8168/8211, Gigabit Ethernet | `lspci`; no se publica dirección |
| Wi-Fi | Adaptador TP-Link TL-WN722N v2/v3 detectado | `lsusb`; SSID/clave excluidos |
| Bluetooth | Adaptador TP-Link UB500 detectado | `lsusb`; no implica que un gamepad esté conectado |
| Panel arcade | Cuatro encoders DragonRise USB | `lsusb`, dispatcher; asignación por puerto/event en `CONTROLLERS.md` |
| Discos | Sistema/`/userdata`, volumen ROM secundario y volumen ROM principal | `lsblk`, `df -h` |

## Almacenamiento observado

| Montaje | Dispositivo/FS | Capacidad | Uso al observar |
|---|---|---:|---:|
| `/userdata` | `sda2`, ext4 | 213.6 GiB | 120 GiB usados, 83 GiB disponibles |
| `/media/BATOCERA_ROMS` | `sdb1`, ext4 | 931.5 GiB | no usado como destino de auditoría activa en esta consulta |
| `/media/ROMS` | `sdc1`, ext4 | 3.6 TiB | 1.0 TiB usados, 2.5 TiB disponibles |

Los valores de espacio cambian. La inspección no ejecutó pruebas SMART ni de superficie. El modelo/serial de discos se omite de la documentación pública; verificar SMART por separado antes de declarar salud física.

## Pantalla

La ficha previa registra TV por HDMI, aproximadamente 42 pulgadas, 1920×1080 a 60 Hz. El EDID/modelo de pantalla no se confirmó en esta lectura. La salida de audio HDMI identificada se documenta en `reports/ARCADE_AUDIO_POLICY.md`.
