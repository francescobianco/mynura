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
| Display | 720×1600, densità 320 ✅. Pannello: uno di 11 driver LCM compilati (`nt36525b`, `ft8006s`, `hx83102d`, `ili9882n`, `icnl9911c`…): quale sia il nostro si vede dal dmesg/cmdline (serve root) |
| Bootloader | fastboot (Vol Giù + Accensione) |
| Sblocco bootloader | Mi Unlock ufficiale (account Mi associato, attesa di giorni). Alternativa MediaTek: mtkclient via BROM ⚠️ |
| Firmware Android | MIUI V12.0.5.0.QCDEUTI (EEA), Android 10, patch build 2021 ✅ |
| Partizioni | Niente A/B. **Partizioni dinamiche** (`super`), `boot`=p33, `recovery`=p2, `dtbo`, `vbmeta`, `vbmeta_system`, `vbmeta_vendor`, `userdata`=p41 ✅ (`raw/android-info/by-name.txt`) |
| Stato bootloader | **Bloccato** (`flash.locked=1`, `verifiedbootstate=green`), `sys.oem_unlock_allowed=0` → attivare "Sblocco OEM" nelle Opzioni sviluppatore ✅ |
| Recovery custom | TWRP non ufficiale? ⚠️ da cercare |
| Kernel downstream | **4.9.190** (`4.9.190-perf-gafd7236`, clang 9, build 2021-07-21) ✅. Config completa in `raw/android-info/kernel-config.txt`. dtb: `mediatek/mt6765` accodato + overlay `mediatek/dandelion` in `dtbo`. Sorgenti: <https://github.com/MiCode/Xiaomi_Kernel_OpenSource> (cerca il branch `dandelion-*`) |
| Supporto mainline | MT6765 ha solo un supporto minimo in mainline: per ora la strada è il **downstream** |
| Pagina wiki pmOS | da cercare: <https://wiki.postmarketos.org/wiki/Devices> |
| Pacchetti pmaports | da cercare in pmaports (anche nei merge request aperti) prima di crearne di nuovi |

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
| Avvio kernel | ❔ | |
| Rete USB / SSH | ❔ | |
| Display | ❔ | |
| Touchscreen | ❔ | |
| Tasti fisici | ❔ | |
| Storage interno / SD | ❔ | |
| Batteria / ricarica | ❔ | |
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
3. [ ] Scaricare il firmware fastboot stock della stessa versione MIUI ed estrarre `boot.img`, `vbmeta.img`
4. [ ] `./scripts/analyze-bootimg.sh xiaomi-dandelion <boot.img stock>`
5. [ ] Cercare port esistenti (wiki, pmaports, MR, chat) per dandelion/angelica/MT6765
6. [ ] Sbloccare il bootloader (Mi Unlock) — **cancella i dati**. ⏳ Possibile dal 2026-11-08 ~12:08
7. [x] Backup delle partizioni nvram/nvdata/persist (mtkclient via BROM, 2026-11-01)
8. [ ] `pmbootstrap init` → nuovo dispositivo `xiaomi-dandelion`, kernel downstream
9. [ ] Primo boot: `pmbootstrap flasher boot` (dalla RAM, senza scrivere) e cercare la rete USB

## Come si flasha

_Da compilare quando il metodo è stato provato._

## Problemi aperti

- [x] Confermare codename, SoC e architettura sul nostro esemplare
- [ ] Capire quale pannello LCM monta il nostro esemplare

## Diario

Più recente in alto. Formato: `### AAAA-MM-GG — titolo (autore)`.

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
