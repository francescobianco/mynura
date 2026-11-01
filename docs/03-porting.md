# 03 — Creare il port di un nuovo dispositivo

Riferimento ufficiale: <https://wiki.postmarketos.org/wiki/Porting_to_a_new_device>

## 1. Analizza il boot.img originale

```bash
./scripts/analyze-bootimg.sh <codename> path/del/boot.img
```

Lo script usa `pmbootstrap bootimg_analyze`, che stampa già le righe `deviceinfo_*` corrette (offset, pagesize,
cmdline, header version, dtb). Salva il risultato in `raw/bootimg-analyze.txt`.

## 2. Crea i pacchetti con il wizard

```bash
pmbootstrap init
# Vendor: <vendor>   Device codename: <codename>
# "Device not found, create a new device?" -> y
```

Il wizard chiede: architettura, se ha tastiera fisica, se ha SD esterna, il metodo di flash, ed eventualmente il
percorso del boot.img da analizzare. Alla fine crea in pmaports:

```
device/testing/device-<vendor>-<codename>/APKBUILD
device/testing/device-<vendor>-<codename>/deviceinfo
device/testing/linux-<vendor>-<codename>/APKBUILD
device/testing/linux-<vendor>-<codename>/config-<vendor>-<codename>.<arch>
```

Copia (o linka) le versioni importanti di questi file nel dossier, in `devices/<codename>/pmaports/`, così
restano nella storia di questo repo anche se il branch di pmaports cambia.

## 3. Il kernel

### Downstream

1. Trova i sorgenti: sito open source del vendor (Samsung OSRC, Sony, Motorola su GitHub…) oppure il kernel di
   LineageOS per quel dispositivo.
2. Nell'`APKBUILD` del kernel imposta `_repository`/`_commit` (o il tarball) e il `defconfig` giusto
   (lo trovi in `arch/arm*/configs/`, spesso si chiama come il codename o il SoC).
3. Genera la config e controlla le opzioni richieste da postmarketOS:

   ```bash
   pmbootstrap kconfig edit linux-<vendor>-<codename>
   pmbootstrap kconfig check linux-<vendor>-<codename>
   ```

4. I kernel vecchi non compilano con GCC moderni: servono le patch che pmaports applica di solito (cerca
   `gcc10-extern_YYLOC_global_declaration.patch` e simili nei kernel di altri dispositivi), oppure
   `CC="${CC:-gcc}"` con flag specifici. Vedi `05-problemi-comuni.md`.

### Mainline

Se il SoC è supportato, invece di un kernel dedicato si usa il pacchetto del SoC (es. `linux-postmarketos-qcom-msm8916`)
e bisogna scrivere il device tree (`.dts`) del telefono partendo da uno simile. Per molti Qualcomm vecchi (msm8916,
msm8974…) serve **lk2nd**, un bootloader secondario che rende il boot molto più semplice.

## 4. Build e checksum

```bash
pmbootstrap checksum linux-<vendor>-<codename>
pmbootstrap checksum device-<vendor>-<codename>
pmbootstrap build linux-<vendor>-<codename>
pmbootstrap install          # crea l'immagine rootfs
```

Per la prima prova `pmbootstrap install --no-fde` e interfaccia `console`.

## 5. Avanti

Flash e debug: [04-flash-e-debug.md](04-flash-e-debug.md).
