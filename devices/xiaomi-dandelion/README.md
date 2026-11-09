# Xiaomi Redmi 9AT — M2006C3LVG (`xiaomi-dandelion`)

> Referente: @francesco · Dossier aperto il 2026-11-01

⚠️ = dato preso da fonti pubbliche, **da confermare** con `collect-android-info.sh` sul nostro esemplare.

## Riepilogo

| | |
|---|---|
| Codename pmOS | `xiaomi-dandelion` (Android: `ro.product.device=dandelion`, `ro.product.name=dandelion_eea`) ✅ |
| Modello / varianti | M2006C3LVG = **Redmi 9AT** (confermato dal descrittore USB, vedi diario), variante del Redmi 9A. Dispositivi fratelli sulla stessa piattaforma: Redmi 9A, Redmi 9C (`angelica`), Redmi 10A ⚠️ |
| SoC | MediaTek Helio G25: `ro.boot.hardware=mt6762`, `ro.board.platform=mt6765` ✅ |
| Architettura | **kernel arm64**, userspace Android a 32 bit (`armeabi-v7a`) → per pmOS: `aarch64` ✅ |
| RAM / Storage | 2 GB (`MemTotal` 1,8 GB) ✅ / 32 GB eMMC (`mmcblk0`) |
| Display | 720×1600, densità 320 ✅. Pannello: `ft8006s_vdo_hdp_boe_helitai_drv` ✅ (log di LK in `expdb`). Altri esemplari possono montare uno degli altri driver LCM compilati |
| Bootloader | fastboot (Vol Giù + Accensione) |
| Sblocco bootloader | Mi Unlock ufficiale (account Mi associato, attesa di giorni). Alternativa MediaTek: mtkclient via BROM ⚠️ |
| Firmware Android | MIUI V12.0.5.0.QCDEUTI (EEA), Android 10, patch build 2021 ✅ |
| Partizioni | Niente A/B. **Partizioni dinamiche** (`super`), `boot`=p33, `recovery`=p2, `dtbo`, `vbmeta`, `vbmeta_system`, `vbmeta_vendor`, `userdata`=p41 ✅ (`raw/android-info/by-name.txt`) |
| Stato bootloader | **Sbloccato** dal 2026-11-09 (`unlocked: yes`, `secure: no`) ✅ |
| Recovery custom | TWRP non ufficiale? ⚠️ da cercare |
| Kernel downstream | **4.9.190** (`4.9.190-perf-gafd7236`, clang 9, build 2021-07-21) ✅. Config completa in `raw/android-info/kernel-config.txt`. dtb: `mediatek/mt6765` accodato + overlay `mediatek/dandelion` in `dtbo`. Sorgenti: <https://github.com/MiCode/Xiaomi_Kernel_OpenSource>, branch `dandelion-q-oss` ✅ |
| Supporto mainline | MT6765 ha solo un supporto minimo in mainline: per ora la strada è il **downstream** |
| Pagina wiki | non verificata: il wiki (ora `wiki.nura.eco`) blocca gli accessi automatici, va aperto da browser |
| Pacchetti pmaports | nessun port di dandelion o MT6765 né merge request (controllato il 2026-11-09). Riferimento vicino: `device/testing/device-xiaomi-lancelot` (MT6769, kernel `linux-postmarketos-mediatek-mt6768`) |
| Tentativo precedente | <https://github.com/SheatNoisette/postmarket_redmi_9a> (fermo al 2023, non avvia). Utile per le patch `drvgen` a Python 3 e la config del kernel |

## Note specifiche MediaTek / Xiaomi

- **Partizioni da salvare prima di tutto**: `nvram`, `nvdata`, `nvcfg`, `protect1`, `protect2`, `persist`
  (contengono IMEI e calibrazioni), più `boot`, `recovery`, `vbmeta`, `dtbo` se presenti.
  Dopo lo sblocco/root: `./scripts/backup-partitions.sh xiaomi-dandelion --list` per vedere cosa c'è.
- **Lo sblocco cancella tutti i dati** del telefono.
- **vbmeta / AVB**: sui MediaTek con Android 10 di solito bisogna flashare un `vbmeta` con la verifica
  disattivata, altrimenti un boot.img modificato non parte:
  `fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img` ⚠️ (vedi `deviceinfo_flash_fastboot_partition_vbmeta`).
- **mtkclient** può leggere/scrivere le partizioni anche con bootloader bloccato o telefono "brickato"
  (modalità BROM: telefono spento, tieni premuti i tasti volume e collega l'USB). È la nostra rete di sicurezza.
- Il boot.img MediaTek ha spesso un **header MTK** sul kernel/ramdisk: controlla l'output di
  `analyze-bootimg.sh` (`deviceinfo_bootimg_mtk_mkimage`).
- Il dtb è di solito nel boot.img (header v2) oppure in `dtbo`: verifica `deviceinfo_header_version` e
  `deviceinfo_bootimg_qcdt`/`dtb`.

## Menu nascosti MIUI

- **Opzioni sviluppatore** (serve per il debug USB): Impostazioni → Info sul telefono → tocca **7 volte
  "Versione MIUI"**. Poi Impostazioni aggiuntive → Opzioni sviluppatore → Debug USB.
- **CIT** (menu di test hardware di fabbrica): si apre toccando **5 volte "Versione kernel"** in Info sul
  telefono → Tutte le specifiche. Non modifica niente, si esce con Indietro.
  Usalo **prima del flash** per segnare quali componenti funzionano su Android (touch, display, audio, sensori,
  vibrazione, fotocamera). Così, se qualcosa non va su postmarketOS, sappiamo se è il port o il telefono.

## Note dalla config del kernel stock

- ✅ `CONFIG_USB_CONFIGFS=y`, `USB_CONFIGFS_RNDIS=y`: la rete USB di pmOS dovrebbe funzionare
- ❌ `CONFIG_DEVTMPFS` **non è attivo**: va attivato (lo richiede pmOS, `pmbootstrap kconfig check`)
- ❌ `CONFIG_VT` non è attivo: va attivato per la console sul display
- Il kernel ha una `CONFIG_CMDLINE` incorporata (`console=ttyMT3,921600n1 root=/dev/ram …`): controlla come
  si combina con quella del boot.img
- Wi-Fi/BT/GPS/FM: chip integrato `CONSYS_6765`, moduli `wmt_drv`, `wlan_drv_gen4m`, `bt_drv`, `gps_drv`
  (sono moduli caricabili, non compilati nel kernel)
- GPU: PowerVR `rgx` (`MTK_GPU_VERSION="rgx doma m1.9ED4940716"`)

## Stato delle funzionalità

Legenda: ✅ funziona · ⚠️ parziale · ❌ non funziona · ❔ non testato

| Funzione | Stato | Note |
|---|---|---|
| Avvio kernel | ✅ | 4.9.190 con initramfs (2026-11-09) |
| Rete USB / SSH | ✅ | `ssh francesco@172.16.42.1`, circa 3 minuti dopo il riavvio |
| Display | ✅ | Sxmo dwm tramite `mtkfb` e X11 `fbdev` |
| Touchscreen | ✅ | `fts_ts` con firmware `focaltech_aa_ts_fw_helitai.bin` dalla partizione `vendor`, incluso nell'initramfs. Scala 720×1600 corretta |
| Tasti fisici | ❔ | |
| Storage interno / SD | ⚠️ | eMMC ✅, rootfs in `userdata` esteso a 21,5 GB. SD non provata |
| Batteria / ricarica | ⚠️ | `status` = Charging, ma `capacity` = -1: livello non letto |
| Wi-Fi | ❔ | MediaTek connsys (combo wifi/BT integrato): sui downstream di solito è il punto più difficile |
| Bluetooth | ❔ | |
| Audio | ❔ | |
| Modem (chiamate/SMS/dati) | ❔ | Su Android stock: chiamate ✅ con CoopVoce (rete TIM) dopo ~10 min dall'inserimento della SIM, via 2G (VoLTE spento). Vedi diario |
| GPS | ❔ | |
| Fotocamera | ❔ | |
| Sensori | ❔ | |
| Accelerazione 3D | ❔ | GPU PowerVR GE8320: niente driver liberi, aspettati solo rendering software |
| Sospensione | ❔ | |

## Piano di lavoro

1. [x] Leggere versione MIUI / RAM del nostro esemplare
2. [x] `./scripts/collect-android-info.sh xiaomi-dandelion` (senza root, prima di sbloccare)
3. [x] Ottenere `boot.img` e `vbmeta.img` stock: usati quelli del backup BROM, stessa versione del telefono
4. [x] Analizzare il boot.img: `raw/bootimg-analyze.txt` (header letto a mano, vedi diario)
5. [x] Cercare port esistenti in pmaports, MR e GitHub (resta da controllare il wiki da browser e le chat)
6. [x] Sbloccare il bootloader (Mi Unlock), 2026-11-09: `fastboot getvar unlocked` → `yes`
7. [x] Backup delle partizioni nvram/nvdata/persist (mtkclient via BROM, 2026-11-01)
8. [x] `pmbootstrap init` → nuovo dispositivo `xiaomi-dandelion`, kernel downstream. Bozza di `deviceinfo` e cmdline in `pmaports/device-xiaomi-dandelion/`. La base del kernel è il port di SheatNoisette (sorgenti `dandelion-q-oss`, patch `drvgen`, config con `DEVTMPFS` e `VT` già attivi)
9. [x] Primo boot e rete USB: riuscito scrivendo `boot` con footer AVB (l'avvio dalla RAM non funziona su questo telefono)
10. [x] Scrivere il rootfs in `userdata` e avviare il sistema completo (2026-11-09): SSH funzionante
11. [ ] Automatizzare il footer AVB nel port, così `pmbootstrap flasher` produce un boot.img già avviabile
12. [ ] Display e console sullo schermo
13. [ ] Batteria, Wi-Fi, modem

## Come si flasha

`fastboot boot` **non funziona**: LK risponde `OKAY` ma poi va in panic, anche con il boot.img stock.

Il boot.img va scritto nella partizione `boot` con un footer AVB, altrimenti LK va in panic (`g_boot_info.hdr_loaded`).
`vbmeta` non è stato necessario toccarla.

```bash
avbtool add_hash_footer --image boot.img --partition_name boot --partition_size 67108864
fastboot flash boot boot.img
fastboot reboot
```

Il rootfs va in `userdata`, con l'immagine completa di `pmbootstrap install`. Il `fastboot` del PC la divide da solo in blocchi
(`max-download-size` 128 MB), senza bisogno di `deviceinfo_flash_sparse`:

```bash
fastboot flash userdata ~/.local/var/pmbootstrap/chroot_native/home/pmos/rootfs/xiaomi-dandelion.img
```

Il telefono si presenta come `18d1:d001`, indirizzo `172.16.42.1`, SSH dopo circa 3 minuti. Senza rootfs compare invece la
shell di debug su telnet (porta 23). Il `pmbootstrap` attuale non aggiunge il footer: va fatto a mano o automatizzato nel port.

## Problemi aperti

- [x] Confermare codename, SoC e architettura sul nostro esemplare
- [x] Capire quale pannello LCM monta il nostro esemplare
- [x] Capire se LK accetta `fastboot boot` da RAM su questo telefono: **no**. Riceve l'immagine ma va in panic, anche con il boot.img stock (2026-11-09)
- [ ] Provare l'avvio scrivendo l'immagine nella partizione `boot`
- [x] Decidere come fornire il dtb: entrambi i modi, come nello stock

## Diario

Più recente in alto. Formato: `### AAAA-MM-GG — titolo (autore)`.

### 2026-11-09 — Sxmo dwm parte e resta acceso, touch e tasti ancora da sistemare (Claude per @francesco)

- Interfaccia scelta: `sxmo-de-dwm`, con X11 sul framebuffer (`xorg.conf` con driver `fbdev`). Schermo funzionante.
- **Ciclo di riavvii, tre cause in fila.** `wireplumber` manda il kernel in Oops in `mtk_pcm_dl2_params`: audio disattivato
  con `SXMO_NO_AUDIO=1`. Poi uno spegnimento ordinato circa 25 s dopo X (`openrc shutdown`, nessun panic): `upower` vede la
  batteria allo 0% perché `capacity` = -1 e fa l'azione critica. Risolto con `UPower.conf.d/90-dandelion.conf`
  (`CriticalPowerAction=Ignore`): **senza spegnimento automatico a batteria scarica**. Sospensione di Sxmo disattivata per prudenza.
- **Avvio da 3 minuti a circa 15 s.** GPU e touch chiedevano firmware assenti, con 60 s di attesa a tentativo (tre per la
  GPU). `CONFIG_FW_LOADER_USER_HELPER_FALLBACK` non basta, il Kconfig MediaTek la riattiva: `prepare()` porta `loading_timeout` a 1 s.
- Aggiunto il profilo Sxmo `sxmo_deviceprofile_mediatek,MT6765.sh`; il warning sparisce.
- **Touch:** nessun evento. Il controller `ft8006s` cerca `focaltech_ts_fw_helitai.bin`, che manca. Letta `super` via BROM ed
  estratta `vendor`: contiene `firmware/focaltech_aa_ts_fw_helitai.bin` e `..._ab_...`. Il telefono riporta `chip id = 0x8632`
  (`_FT8006S_AA`), quindi va usata la **AA**, installata col nome richiesto dal driver. Il file sta in
  `raw/backup/firmware/` e non è nel repo. In `/lib/firmware` non basta: il driver lo chiede a 2 s dall'avvio, quindi va
  anche nell'initramfs (`30-touch-firmware.files`). Con quello: `fw download successfully`, interrupt ed eventi arrivano,
  il cursore segue il dito. L'errore `fts_fw_recovery: check boot id fail` subito dopo il download non impedisce il funzionamento.
- **Tasti:** `bonsaid` fallisce con `Unable to initialize socket: Operation not supported`. Causa da capire.

### 2026-11-09 — 🎉 Sistema completo avviato, SSH funzionante (Claude per @francesco)

- `fastboot flash userdata` dell'immagine da 1,19 GB, 5 blocchi, 35 s. Gli UUID di `boot` e `root` coincidevano con il
  boot.img già scritto, quindi non è servito ricostruire nulla.
- Dopo il riavvio SSH si apre in circa 3 minuti: `Nura edge`, `Linux xiaomi-dandelion 4.9.190-perf`, aarch64, `/` da
  21,5 GB, 96 MB di RAM usati su 1772. Output in `raw/build-logs/first-ssh-*.txt`.
- Da verificare: `capacity` della batteria a -1, interfacce modem `ccmni*` presenti ma spente, nessuna interfaccia Wi-Fi
  (i moduli connsys non sono caricati), `chronyd` in stato crashed. Sullo schermo resta il logo Redmi.

### 2026-11-09 — 🎉 Il kernel parte: rete USB e shell di debug (Claude per @francesco)

- Aggiunto il footer AVB con `avbtool add_hash_footer` (`--partition_size 67108864`, algoritmo NONE) e riscritta solo `boot`
  (sha256 `35735d38…`). `vbmeta` non toccata. Al riavvio LK mostra "Orange State" e avvia il kernel.
- 15 s dopo il riavvio il PC vede `18d1:d001`, interfaccia con `172.16.42.2`, ping OK. Il display resta sul logo Redmi.
- Dopo circa 3 minuti l'initramfs non trova il rootfs (mai scritto, atteso) ed entra nella shell di debug: telnet 172.16.42.1:23.
- Da lì: `Linux 4.9.190-perf`, gcc 15.2.0, RAM 1,8 GB, 47 nodi `mmcblk*`, `/dev/fb0` a 720×1600, UDC `musb-hdrc`.
  Output in `raw/build-logs/first-telnet-*.txt`.
- Il log dell'initramfs segnala moduli `vfat` e `uinput` assenti: non bloccano il boot, da guardare poi.

### 2026-11-09 — Scrittura della partizione `boot` (Claude per @francesco)

- `fastboot flash boot raw/backup/pmos-boot-20261109-174227.img` (sha256 `c40f9e25…`), ramdisk gzip, `vbmeta` non toccata.
  Scrittura `OKAY`, poi `fastboot reboot`.
- Il telefono sparisce dalla USB alle 18:02:05 e non ricompare per oltre 2 minuti: né Android, né fastboot, né rete USB.
- Per tornare allo stock: in fastboot, `fastboot flash boot raw/backup/mtk-2026-11-01/boot.bin`.
- Ciclo di riavvii. Log da `expdb` (via BROM), in ogni giro:
  ```
  avb_footer.c:41: ERROR: Footer magic is incorrect.
  avb_slot_verify.c:742: ERROR: boot: Error verifying vbmeta image: invalid vbmeta header
  [avb] ret = 2 / boot state: orange  ("Your device will boot in 5 seconds")
  [6348] panic (...): ASSERT at (platform/common/boot/boot_info.c:341): g_boot_info.hdr_loaded
  lk_wdt_dump(): watchdog timeout in LK....
  ```
  Il kernel anche qui non parte. LK si aspetta un footer AVB in fondo alla partizione `boot`, che il nostro boot.img non ha.
- `fastboot oem poweroff` spegne il telefono da fastboot. Il modo più comodo per la BROM: telefono in fastboot, tenere premuti
  Vol Su + Vol Giù e lanciare `fastboot reboot`.

### 2026-11-09 — Il log di `expdb`: panic in LK, il kernel non parte (Claude per @francesco)

- Letta `expdb` via BROM in sola lettura (`mtk.py r expdb`, file in `raw/backup/`). Il log di LK riporta la nostra cmdline
  e `decompress_kernel` riuscito, poi:
  ```
  ERROR: EMI info incorrect
  ERROR: debug info base and size incorrect
  panic (caller 0x48023c6f): ERROR: root node search failed , while(1)
  lk_wdt_dump(): watchdog timeout in LK....
  ```
- Il panic compare **in entrambi i tentativi**, quindi il ramdisk non c'entra: il kernel non è mai stato avviato. Gzip resta
  necessario per questo kernel, ma non era la causa. Il riavvio in Android arriva dal watchdog di LK, dopo circa 10 s.
- Il problema è nella preparazione del device tree da parte di LK. Stringhe utili in `lk.bin`: `can't find v2 dtb`,
  `main dtb is not packed with valid fdt format!`, `prepare_kernel_dtb`.
- Prova di controllo: `fastboot boot` del boot.img **stock** del backup. **Stesso panic** (terzo caso in `expdb`, con
  `Command: bootopt=64S3,32N2,64N2 buildvariant=user`). Il difetto è quindi nel percorso `fastboot boot` di questo LK, non
  nella nostra immagine: su questo telefono l'avvio dalla RAM non si può usare.
- Attenzione: `fastboot boot` risponde comunque `OKAY`, e il telefono torna su Android dopo il watchdog di LK. Non è un segno
  che l'immagine sia partita.
- Per entrare in BROM: spegnere dal menu di Accensione, poi Vol Su + Vol Giù mentre si collega il cavo. Passando da un
  riavvio forzato si finisce facilmente in fastboot.

### 2026-11-09 — Primo avvio dalla RAM: il telefono torna su Android (@francesco, con Claude)

- `./scripts/first-boot-xiaomi-dandelion.sh`. `fastboot boot` risponde `Sending OKAY`, `Booting OKAY` (ma vedi la voce
  sopra: LK va poi in panic). Il telefono si sconnette e dopo 65 s ricompare come `2717:ff40`, cioè Android stock. Nessuna rete USB.
- Il boot.img generato ha header, indirizzi e dtb uguali allo stock. Differenza sospetta: il ramdisk è **zstd**, mentre la
  config del kernel ha solo `CONFIG_RD_GZIP`. Con `CONFIG_PANIC_TIMEOUT=1`, un panic riavvierebbe subito in Android.
  **Ipotesi, non ancora verificata**: aggiunto `deviceinfo_initfs_compression="gzip"`.
- Altra differenza: `os_version` a 0 nel nostro boot.img. Da guardare se gzip non basta.
- Se non basta: i log di LK e del kernel dovrebbero finire in `expdb`, leggibile via BROM con mtkclient.

### 2026-11-09 — Prima compilazione del kernel (@francesco, con Claude)

- `./scripts/port-xiaomi-dandelion.sh`, da un terminale vero (con il prefisso `!` di Claude Code non si può rispondere a
  `sudo` e `init`). Kernel e pacchetto del dispositivo compilati al primo colpo in circa 7 minuti.
- Ostacoli di `pmbootstrap`: serve `kpartx` sul PC e pmaports deve avere come remote il vecchio URL
  `gitlab.postmarketos.org`. Con kernel 4.9 il service manager va impostato a **openrc**: systemd richiede 5.4+.
- `vmlinuz` è un `Image.gz-dtb`, come nello stock, ma il pacchetto non conteneva un dtb in `/boot/dtbs`. Senza,
  `boot-deploy` si fermerebbe con header v2. Ora l'APKBUILD installa `mediatek/mt6765.dtb` avvolto nella tabella Android
  DT dello stock, e `deviceinfo_append_dtb` è `false` per non accodarlo due volte.
- Il dtb compilato differisce dallo stock per pochi valori: ricarica al freddo (JEITA) più alta nel sorgente pubblico
  (1,5 A contro 1,38 A; 540 mA contro 430 mA; soglia 15 °C contro 17 °C). Riportati ai valori stock in `prepare()`.
  Resta una differenza innocua: `g_FG_PSEUDO100` 99 contro 100.

### 2026-11-09 — Sblocco del bootloader con Mi Unlock (Claude per @francesco)

- Prima dello sblocco: `sha256sum -c` del backup BROM, 42 file su 42 OK.
- Primo tentativo con `miunlock` 1.7.4: `code 10005` — "Invalid nonce param". Il nonce è monouso e lo strumento lo
  riusava per la seconda chiamata. Telefono rimasto bloccato e intatto.
- Corretto upstream lo stesso giorno. Con `miunlock` **1.7.5** (`git pull` nel clone e `pip install ./MiUnlockTool` nel
  venv): "Unlock successful". Il telefono si è riavviato da solo, ha cancellato i dati ed è comparsa la scritta MIUI.
- Verifica al rientro in fastboot: `unlocked: yes`, `secure: no`.
- Dopo la cancellazione il Debug USB è di nuovo spento, ma per il port basta la modalità fastboot.

### 2026-11-09 — Analisi del boot.img e ricerca di port esistenti (Claude per @francesco)

- Bootloader ancora bloccato (`fastboot getvar`: `unlocked: no`, `secure: yes`). Telefono in fastboot, batteria 4,38 V.
- `boot.bin` del backup: header **v2**, pagesize 2048, base `0x40078000`, nessun header MTK. `pmbootstrap` e
  `unpack_bootimg` non sono installati, quindi l'header è stato letto a mano. Dettagli e `deviceinfo` proposto in
  `raw/bootimg-analyze.txt`.
- Il dtb compare **due volte**: accodato al `Image.gz` e nella sezione dtb, dove è avvolto in una tabella Android DT
  (magic `0xd7b7ab1e`, 64 byte in testa). Un `mkbootimg --dtb` con un dtb nudo produrrebbe un'immagine diversa dallo stock.
- Tentativo di SheatNoisette: usa lo stesso kernel (`dandelion-q-oss`, commit `8974b91`) ma `header_version="0"` e
  nessun dtb accodato, mentre lo stock ha header v2 e dtb. **Ipotesi, non verificata**: potrebbe essere il motivo per
  cui lì il bootloader non caricava il kernel.
- Pannello trovato nei log di LK dentro `expdb`: `ft8006s_vdo_hdp_boe_helitai_drv`.
- Il progetto postmarketOS ora si chiama **Nura**: `gitlab.postmarketos.org` reindirizza a `gitlab.nura.eco`, il wiki a
  `wiki.nura.eco`.

### 2026-11-01 — Mi Unlock: conto alla rovescia avviato (@francesco)

> ⏳ **Sblocco possibile da domenica 2026-11-08, circa alle 12:08** (167 ore dalla verifica delle 13:08 del 2026-11-01).

- Strumento: MiUnlockTool (`~/.local/share/mynura-tools/venv-miunlock/bin/miunlock`), su Linux, con il telefono in
  fastboot. Region account `IT`, dataCenterZone `Europe`.
- Primo tentativo: `code 20041` — "your MI ID is not associated with a phone number". Il problema non era la SIM del
  telefono: all'account Mi mancava un numero di telefono. Risolto aggiungendolo su
  <https://account.xiaomi.com/pass/serviceLogin?checkSafePhone=true>.
- Secondo tentativo: `code 20036` — "Please unlock 167 hours later".
- ⚠️ **Non rimuovere e non riaggiungere l'account Mi in MIUI** ("Stato Mi Unlock"), altrimenti l'attesa riparte da capo.
- Attenzione: la richiesta "Press 'Enter' to continue — unlock" compare **sempre**. Dopo l'Invio, se l'attesa è finita,
  il telefono viene sbloccato e **cancellato** subito.
- Quando scade l'attesa: telefono in fastboot, si rilancia `miunlock`. Il backup BROM è già fatto.

### 2026-11-01 — Backup completo delle partizioni via BROM con mtkclient (@francesco)

- `./scripts/setup-tools.sh` e poi `./scripts/mtk-backup.sh xiaomi-dandelion --copy-to <disco esterno>`.
  **Funziona con bootloader bloccato e senza root.**
- Ingresso in BROM: telefono spento (Accensione premuto 10-15 s), **Vol Su + Vol Giù** premuti mentre si collega il
  cavo. Il PC vede `0e8d:0003` (BROM). Lo schermo resta nero.
- Info dal SoC (mtkclient): `MT6765/MT8768t`, HW code `0x766`, **SBC, SLA e DAA attivi**, ma mtkclient li aggira
  ("Security check patched") e carica il proprio DA.
- `printgpt` funziona al primo colpo. Per la seconda fase (`rl`) bisogna **ricollegare il telefono in BROM**, altrimenti
  si vede `Handshake failed` in loop.
- ModemManager fermato prima (`sudo systemctl stop ModemManager`): può occupare la porta `ttyACM`.
- Il comando `mtk` installato da pip è rotto (`No module named 'mtkclient.mtk'`): lo script usa `python mtk.py`.
- Risultato: 42 partizioni, 1,6 GB (escluse `userdata`, `super`, `cache`), tutte con sha256. Presenti `nvram`, `nvdata`,
  `nvcfg`, `persist`, `protect1/2`, `proinfo`, `seccfg`, `md1img`, `boot`, `recovery`, `lk`, `dtbo`, `vbmeta*`.
  Copia verificata su un disco esterno. **Non versionato.**
- Nota: mtkclient può anche sbloccare il bootloader direttamente (`mtk da seccfg unlock`), senza attendere Mi Unlock.
  Lo teniamo come piano B.

### 2026-11-01 — Modem su Android stock: SIM CoopVoce (@francesco)

Verifica del modem su Android, da usare come riferimento per il port. Operatore: **CoopVoce**, operatore virtuale
(MVNO) su rete **TIM**: SIM `222 53`, rete registrata `222 10`. Configurazione dual SIM `dsds`, SIM nello slot 1.

- La SIM viene riconosciuta subito (`gsm.sim.state=LOADED`), con voce e dati `IN_SERVICE` su LTE.
- Prime chiamate in uscita fallite. Dal log di `dumpsys telecom`:
  ```
  5 chiamate in uscita tra le 12:09 e le 12:16, nessuna arriva a SET_ACTIVE
  2 finite con DisconnectCause ERROR (CM_SER_UNAVAILABLE) dopo ~60 s di composizione
  3 interrotte dall'utente (LOCAL)
  ```
- Causa probabile: **VoLTE disattivato** (`persist.vendor.mtk.volte.enable=0`). Senza VoLTE la chiamata deve passare
  dal 4G al 2G (CSFB), perché il 3G di TIM è spento, e con segnale debole il passaggio fallisce.
- Segnale LTE: all'inizio `rsrp=-115` dBm (livello 2/4), dopo qualche minuto `rsrp=-99` dBm.
- ✅ **Dopo circa 10 minuti dall'inserimento della SIM le chiamate funzionano**: tempo di attivazione lato operatore
  più il miglioramento del segnale. Chiamata di prova alle 12:21: `SET_DIALING` → `SET_ACTIVE` in 8 s,
  conversazione regolare, chiusa dall'altra parte (`DisconnectCause REMOTE`). VoLTE ancora spento, quindi
  la chiamata è passata dal 2G.
- Comandi utili per ripetere la verifica:
  ```bash
  adb shell getprop gsm.sim.state; adb shell getprop gsm.network.type
  adb shell dumpsys telephony.registry | grep -m1 -oE 'mVoiceRegState=[^,]*|rsrp=-?[0-9]+'
  adb shell dumpsys telecom | grep -E ' - (SET_DIALING|SET_ACTIVE|SET_DISCONNECTED)|callTerminationReason'
  ```
- **Per postmarketOS**: il modem MediaTek con kernel downstream è un punto critico. Senza VoLTE, l'unica via per le
  chiamate in Italia su TIM/CoopVoce è il 2G (CSFB). Annotare se il modem in pmOS riesce a fare CSFB o VoLTE.

### 2026-11-01 — Alleggerimento di MIUI via adb (@francesco)

- Con 2 GB di RAM e circa 25-65 MB liberi, il telefono era lentissimo.
- `./scripts/android-debloat.sh devices/xiaomi-dandelion/android-debloat.txt`: 34 pacchetti rimossi per l'utente 0
  (pubblicità/telemetria MIUI, Facebook, store Xiaomi, servizi Google superflui). `fashiongallery` dava
  `Failure [-1000]` e l'ho disattivato con `pm disable-user`. Elenco "prima" in `raw/backup/` (non versionato: contiene le app personali).
  Per annullare: aggiungere `--restore`.
- Le animazioni non si possono cambiare via adb: MIUI richiede "Debug USB (Impostazioni di sicurezza)",
  quindi vanno impostate a mano.
- Ricompilazione delle app: `cmd package compile -m speed-profile -a` (completata senza errori).

### 2026-11-01 — Raccolta info da Android, senza root (@francesco)

- Attivato il Debug USB → ID USB `2717:ff48` (MTP + ADB). Prima era `ff40` (solo MTP).
- `collect-android-info.sh`: codename, SoC, kernel 4.9.190 arm64, partizioni, config del kernel completa (`/proc/config.gz`
  è leggibile anche senza root!). Senza root: niente dmesg, cmdline o device tree.
- Trovati IMEI, seriale e MAC dentro `getprop`: lo script ora li oscura. La copia completa è in `raw/backup/`.
- Il collegamento passava da un hub e dava `error -71` (reset USB): meglio usare una porta diretta del PC.

### 2026-11-01 — Primo collegamento USB (@francesco)

- Al primo tentativo il PC non vedeva niente (nessuna riga in `lsusb`). Dopo aver ricollegato il cavo il telefono
  compare:
  ```
  usb 1-4.4: New USB device found, idVendor=2717, idProduct=ff40, bcdDevice= 2.23
  usb 1-4.4: Product: Redmi 9AT
  usb 1-4.4: Manufacturer: Xiaomi
  ```
- `2717:ff40` = modalità MTP. adb non lo vede ancora: manca il Debug USB (vedi "Menu nascosti MIUI").
- Il modello si presenta come **Redmi 9AT**, non 9A.

### 2026-11-01 — Apertura dossier (@francesco)

- Creato il dossier, primo dispositivo del progetto.
- Dati di partenza da fonti pubbliche, ancora da verificare sul telefono.

## File in questo dossier

- `raw/android-info/` — output di `collect-android-info.sh` (testo, committato)
- `raw/bootimg-analyze.txt` — output di `analyze-bootimg.sh`
- `raw/backup/` — dump delle partizioni (**NON committato**, conservalo altrove)
- `pmaports/` — copie di `deviceinfo`, `APKBUILD` e config del kernel nelle versioni importanti
