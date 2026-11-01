# __NAME__ (`__CODENAME__`)

> Referente: @__AUTHOR__ · Dossier aperto il __DATE__

## Riepilogo

| | |
|---|---|
| Codename pmOS | `__CODENAME__` |
| Modello / varianti | |
| SoC | |
| Architettura | armv7 / aarch64 |
| RAM / Storage | |
| Display | risoluzione, pannello (dal dmesg) |
| Bootloader | fastboot / Odin (heimdall) / altro |
| Sblocco bootloader | procedura, link |
| Recovery custom | TWRP? link |
| Kernel downstream | versione, URL sorgenti, defconfig |
| Supporto mainline | SoC supportato? dts esistente? |
| Pagina wiki pmOS | |
| Pacchetti pmaports | `device-__CODENAME__`, `linux-__CODENAME__` (categoria, MR) |

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
| Wi-Fi | ❔ | |
| Bluetooth | ❔ | |
| Audio | ❔ | |
| Modem (chiamate/SMS/dati) | ❔ | |
| GPS | ❔ | |
| Fotocamera | ❔ | |
| Sensori | ❔ | |
| Accelerazione 3D | ❔ | |
| Sospensione | ❔ | |

## Come si flasha

Passi precisi e testati per questo dispositivo (combinazioni di tasti, modalità, comandi).

```bash
# es.
pmbootstrap flasher flash_rootfs
pmbootstrap flasher flash_kernel
```

## Problemi aperti

- [ ] …

## Diario

Più recente in alto. Formato: `### AAAA-MM-GG — titolo (autore)`.

### __DATE__ — Apertura dossier (@__AUTHOR__)

- Creato il dossier.

## File in questo dossier

- `raw/android-info/` — output di `collect-android-info.sh` (testo, committato)
- `raw/bootimg-analyze.txt` — output di `analyze-bootimg.sh`
- `raw/backup/` — dump delle partizioni (**NON committato**, conservalo altrove)
- `pmaports/` — copie di `deviceinfo`, `APKBUILD` e config del kernel nelle versioni importanti
