# 04 — Flash, accesso e debug

## Flash

```bash
pmbootstrap flasher flash_rootfs     # scrive il rootfs (di solito sulla partizione userdata/system)
pmbootstrap flasher flash_kernel     # scrive kernel + initramfs sulla partizione boot
```

**Prova prima senza scrivere niente** (solo fastboot): avvia il kernel dalla RAM.

```bash
pmbootstrap flasher boot
```

Per Samsung si entra in Download mode (di solito Vol Giù + Home + Accensione) e pmbootstrap usa heimdall.
Alternativa: `pmbootstrap export` crea i file in `/tmp/postmarketOS-export/` da flashare a mano o via TWRP.

## Il telefono è collegato? Rete via USB

Quando il boot va a buon fine, il telefono espone una scheda di rete USB:

- IP del telefono: **172.16.42.1**
- Il PC riceve un indirizzo `172.16.42.x` via DHCP

```bash
./scripts/pmos-connect.sh           # ssh <utente>@172.16.42.1
```

Se non compare nessuna interfaccia nuova (`ip link`), il problema è prima: kernel che non parte, initramfs che si
blocca o USB gadget non configurato nel kernel.

## Debug shell dell'initramfs

Se il rootfs non si monta, puoi farti dare una shell già dentro l'initramfs aggiungendo `pmos.debug-shell` alla
cmdline:

```bash
pmbootstrap flasher boot --cmdline pmos.debug-shell
# poi
./scripts/pmos-connect.sh --telnet   # telnet 172.16.42.1
```

Dalla shell: `dmesg`, `cat /proc/partitions`, `ls /dev/disk`, `cat /pmOS_init.log` (o file analoghi in `/`)
per capire dove si ferma.

## Log utili

```bash
pmbootstrap log                      # log della build/flash sul PC
# sul telefono:
dmesg
cat /proc/last_kmsg                  # kernel downstream: log del boot precedente
cat /sys/fs/pstore/*                 # mainline con ramoops: log del crash precedente
```

**Trucco per i kernel che si riavviano subito**: fai il boot di postmarketOS, poi riavvia subito in TWRP o
Android e leggi `/proc/last_kmsg` o `/sys/fs/pstore/`. Spesso c'è il kernel panic completo.

## Il telefono resta su schermo nero?

Non vuol dire che non stia funzionando. In ordine:

1. Compare la rete USB? → il kernel funziona, il problema è il display (framebuffer, pannello, retroilluminazione).
2. Niente rete USB → prova `pmos.debug-shell`; controlla `CONFIG_USB_CONFIGFS*` o `CONFIG_USB_G_ANDROID`
   nella config.
3. Niente di niente → offset del boot.img sbagliati, dtb mancante/sbagliato, kernel non compilato per il SoC
   giusto. Ricontrolla `analyze-bootimg.sh`.
4. Se il telefono ha i punti di test UART, una **console seriale** risolve il 90% dei misteri.

## Tornare indietro

Tieni sempre a portata di mano il firmware stock o il `boot.img` di backup:

```bash
fastboot flash boot devices/<codename>/raw/backup/boot.img
```
