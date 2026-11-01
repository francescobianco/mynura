# mynura

Dossier, guide e script per **portare vecchi telefoni Android su [postmarketOS](https://postmarketos.org)**.

Lo scopo è lasciare una traccia di tutto quello che proviamo, compresi i tentativi falliti, così chi arriva dopo
non deve ripartire da zero.

## Struttura

```
docs/                 Guide generali, valide per tutti i dispositivi
  00-introduzione.md        Concetti base (pmbootstrap, pmaports, downstream vs mainline)
  01-setup-ambiente.md      Preparare il PC di lavoro
  02-raccolta-info.md       Raccogliere informazioni dal telefono ancora con Android
  03-porting.md             Creare il port di un nuovo dispositivo
  04-flash-e-debug.md       Flash, accesso via USB, debug shell, log
  05-problemi-comuni.md     Problemi già incontrati e relative soluzioni
devices/              Un dossier per ogni telefono (cartella = codename)
  README.md                 Tabella riassuntiva di tutti i dispositivi
  _TEMPLATE/                Modello da copiare (usa scripts/new-device.sh)
scripts/              Strumenti da riga di comando
```

## Avvio rapido

```bash
# 1. Crea il dossier di un nuovo telefono
./scripts/new-device.sh samsung-i9100 "Samsung Galaxy S II"

# 2. Con il telefono ancora su Android e il debug USB attivo, raccogli le informazioni
./scripts/collect-android-info.sh samsung-i9100

# 3. (se hai root) salva le partizioni critiche PRIMA di fare qualsiasi altra cosa
./scripts/backup-partitions.sh samsung-i9100 boot recovery efs

# 4. Analizza il boot.img originale per ricavare i parametri del deviceinfo
./scripts/analyze-bootimg.sh samsung-i9100 devices/samsung-i9100/raw/backup/boot.img

# 5. Dopo il flash di postmarketOS: collegati via USB
./scripts/pmos-connect.sh            # ssh
./scripts/pmos-connect.sh --telnet   # debug shell dell'initramfs
```

## Script disponibili

| Script | A cosa serve |
|---|---|
| `scripts/new-device.sh` | Crea `devices/<codename>/` partendo dal template |
| `scripts/collect-android-info.sh` | Scarica via `adb` getprop, cpuinfo, partizioni, dmesg, moduli, device tree… |
| `scripts/backup-partitions.sh` | Backup delle partizioni via `adb` (richiede root) |
| `scripts/analyze-bootimg.sh` | Estrae offset, cmdline, pagesize e dtb da un `boot.img` |
| `scripts/pmos-connect.sh` | Collegamento SSH/telnet al telefono via USB (172.16.42.1) |
| `scripts/check-host.sh` | Controlla che sul PC ci siano tutti gli strumenti necessari |

## Regole del dossier

1. **Annota tutto**, anche i fallimenti, nella sezione *Diario* del dispositivo, con la data.
2. **Non committare file binari** (immagini delle partizioni, firmware). Possono contenere IMEI e dati personali,
   e il `.gitignore` li esclude già. Committa invece i file di testo prodotti dagli script.
3. Se una soluzione vale per più telefoni, spostala in `docs/05-problemi-comuni.md`.
4. Quando un port funziona, il traguardo è mandarlo upstream su
   [pmaports](https://gitlab.postmarketos.org/postmarketOS/pmaports) e scriverlo sulla
   [wiki](https://wiki.postmarketos.org).

Per contribuire leggi [CONTRIBUTING.md](CONTRIBUTING.md).
