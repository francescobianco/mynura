# Come contribuire

## Aggiungere un telefono

```bash
./scripts/new-device.sh <vendor>-<codename> "Nome commerciale"
```

Per il codename usa il formato di postmarketOS, `vendor-codename` in minuscolo (es. `samsung-i9100`,
`lg-hammerhead`, `motorola-osprey`). Il codename si trova con `adb shell getprop ro.product.device`, oppure
cercando il modello su [wiki.postmarketos.org](https://wiki.postmarketos.org/wiki/Devices).

Poi aggiungi una riga in `devices/README.md`.

## Aggiornare un dossier

- Scrivi nel **Diario** in ordine cronologico: `### AAAA-MM-GG — titolo`, poi cosa hai provato, cosa è
  successo e il log rilevante (solo l'estratto utile, il resto va in `raw/`).
- Aggiorna la **tabella delle funzionalità** solo per cose che hai verificato di persona.
- Legenda stati: ✅ funziona · ⚠️ parziale · ❌ non funziona · ❔ non testato.

## Script

- Bash con `set -euo pipefail`, eseguibili, con un `--help`.
- Prima di committare: `shellcheck scripts/*.sh`.
- Gli script che scrivono sul telefono (flash, dd) devono chiedere conferma.

## Commit

Messaggi brevi con il prefisso del dispositivo o dell'area:

```
samsung-i9100: wifi funziona con firmware da /vendor
docs: aggiunta sezione su lk2nd
scripts: collect-android-info salva anche /proc/iomem
```
