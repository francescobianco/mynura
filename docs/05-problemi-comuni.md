# 05 — Problemi comuni (e soluzioni trovate)

Formato di ogni voce: **sintomo**, causa, soluzione, dispositivi su cui è successo (link al dossier).
Aggiungi qui ogni problema risolto che può capitare anche su altri telefoni.

---

### `adb devices` → `no permissions`
- **Causa**: mancano le regole udev o l'utente non è nel gruppo `plugdev`.
- **Soluzione**: vedi [01-setup-ambiente.md](01-setup-ambiente.md#permessi-usb-udev).

### Il kernel downstream non compila: `multiple definition of 'yylloc'`
- **Causa**: GCC ≥ 10 rifiuta un simbolo duplicato in `scripts/dtc`.
- **Soluzione**: applica la patch `gcc10-extern_YYLOC_global_declaration.patch` (presente in molti kernel di
  pmaports: copiala da lì).

### Il kernel downstream non compila: altri errori con GCC moderno
- **Soluzione**: guarda come hanno risolto i kernel dello stesso SoC in pmaports, che hanno quasi sempre le patch
  già pronte. Come ultima risorsa aggiungi `-Wno-error` / disabilita `CONFIG_*_WERROR`.

### Il boot si blocca, nessuna rete USB
- Controlla nella config del kernel: `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_CONFIGFS_RNDIS=y` (o
  `CONFIG_USB_G_ANDROID=y` sui kernel molto vecchi), `CONFIG_DEVTMPFS=y`.
- Esegui `pmbootstrap kconfig check`.

### Schermo nero ma SSH funziona
- Il framebuffer potrebbe non essere inizializzato. Prova `echo 0 > /sys/class/graphics/fb0/blank` e controlla la
  retroilluminazione in `/sys/class/backlight/*/brightness`.

### Rimango bloccato in "Waiting for root partition"
- Il rootfs non è dove l'initramfs lo cerca. Controlla con la debug shell (`cat /proc/partitions`) e il valore di
  `deviceinfo_flash_*_partition_*` nel deviceinfo.

---

<!-- Aggiungi le nuove voci qui sopra questa riga -->
