# 02 — Raccogliere informazioni dal telefono (prima di cancellare Android!)

Finché il telefono ha Android funzionante è una miniera di informazioni. **Una volta flashato, molte di queste
non si recuperano più facilmente.**

## 1. Abilita il debug USB

Impostazioni → Info sul telefono → tocca 7 volte "Numero build" → Opzioni sviluppatore → Debug USB.

## 2. Raccogli tutto con lo script

```bash
./scripts/collect-android-info.sh <codename>
```

Salva in `devices/<codename>/raw/android-info/`:

| File | Perché serve |
|---|---|
| `getprop.txt` | codename, piattaforma, versione Android, densità schermo |
| `cpuinfo.txt`, `soc.txt` | SoC e architettura (armv7 / aarch64) |
| `partitions.txt`, `by-name.txt` | nomi e dimensioni delle partizioni (boot, recovery, system, userdata…) |
| `cmdline.txt` | cmdline del kernel Android (spesso serve root) |
| `dmesg.txt` | driver caricati, nome del pannello del display, touchscreen, chip wifi (serve root) |
| `lsmod.txt`, `modules-*.txt` | moduli del kernel e firmware |
| `dt-model.txt`, `dt-compatible.txt` | modello e `compatible` del device tree (fondamentali per il mainline) |
| `firmware-files.txt` | elenco dei blob in `/vendor/firmware`, `/system/etc/firmware` |
| `input-devices.txt`, `i2c-devices.txt` | touchscreen, tasti, sensori |
| `kernel-config.txt` | `/proc/config.gz`, se esposto dal kernel |

Senza root lo script raccoglie comunque quello che può e segna cosa è fallito.

> **Il repo è pubblico.** `getprop` contiene IMEI, numero di serie, MAC di Wi-Fi/BT, IMSI/ICCID e gli ID univoci del
> SoC (`ro.boot.chipid`, `ro.boot.cpuid`, che Xiaomi usa anche per lo sblocco). Lo script li oscura (`REDACTED`) e
> salva la copia integrale in `raw/backup/`, che è escluso da git. Prima di ogni commit controlla comunque:
> `git diff --cached | grep -iE 'imei|serial|[0-9]{15}|([0-9a-f]{2}:){5}'`

## 3. Backup delle partizioni (se hai root)

```bash
./scripts/backup-partitions.sh <codename> boot recovery
```

**Partizioni da salvare assolutamente, se esistono**: `efs` (Samsung, contiene l'IMEI!), `modemst1`, `modemst2`,
`fsg`, `persist` (Qualcomm: calibrazioni dei sensori, wifi, MAC), `nvram`/`nvdata` (MediaTek: IMEI).
Se le perdi, il modem potrebbe non funzionare mai più, nemmeno tornando ad Android.

I backup vanno in `raw/backup/`, che **è escluso da git**. Conservali altrove (disco esterno).

## 4. Senza root?

- Scarica il **firmware stock** ufficiale (es. da siti di firmware Samsung, Motorola, LineageOS) ed estrai il
  `boot.img`.
- Se esiste una build di **LineageOS / TWRP** per il dispositivo, i sorgenti del kernel e il device tree Android
  sono su GitHub (`android_kernel_<vendor>_<soc>`, `android_device_<vendor>_<codename>`): sono la fonte migliore
  per il kernel downstream.
- Da TWRP hai una shell root via `adb shell` e puoi fare il backup lo stesso.

## 5. Cerca prima di cominciare

- C'è già una pagina sulla wiki? `https://wiki.postmarketos.org/wiki/<Vendor>_<Modello>_(<vendor>-<codename>)`
- C'è già un pacchetto? Cerca il codename in pmaports (anche nei merge request aperti).
- Ci sono telefoni "fratelli" con lo stesso SoC già portati? Il loro `deviceinfo` e la loro configurazione del
  kernel sono un ottimo punto di partenza.
