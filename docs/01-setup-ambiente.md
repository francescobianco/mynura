# 01 — Preparare l'ambiente sul PC

Prima di tutto lancia `./scripts/check-host.sh`: dice cosa manca.

## pmbootstrap

Metodo consigliato (versione sempre aggiornata):

```bash
git clone https://gitlab.postmarketos.org/postmarketOS/pmbootstrap.git ~/src/pmbootstrap
mkdir -p ~/.local/bin
ln -s ~/src/pmbootstrap/pmbootstrap.py ~/.local/bin/pmbootstrap
pmbootstrap --version
```

In alternativa: `pipx install pmbootstrap`, oppure il pacchetto della tua distribuzione (spesso è vecchio).

Inizializzazione:

```bash
pmbootstrap init
```

Durante `init` sceglierai: canale (`edge` per il porting), vendor/dispositivo, interfaccia utente (per i primi
test conviene `console` o `none`: meno cose che si possono rompere), utente e hostname.

La cartella di lavoro predefinita è `~/.local/var/pmbootstrap`. Il checkout di pmaports che userai per il port
si trova con:

```bash
pmbootstrap config aports
```

## Strumenti per il flash

| Strumento | Per quali telefoni | Pacchetto (Debian/Ubuntu) |
|---|---|---|
| `adb`, `fastboot` | quasi tutti (Nexus, Motorola, LG, Xiaomi, Sony…) | `android-sdk-platform-tools` / SDK |
| `heimdall` | Samsung (modalità Download/Odin) | `heimdall-flash` |
| `mtkclient` | MediaTek (BROM) | `pip install` da GitHub (bkerler/mtkclient) |
| `edl` | Qualcomm in modalità EDL 9008 | da GitHub (bkerler/edl) |

pmbootstrap usa da solo lo strumento giusto in base a `deviceinfo_flash_method`.

## Permessi USB (udev)

Se `adb devices` mostra `no permissions`:

```bash
sudo apt install android-sdk-platform-tools-common   # installa le regole udev
sudo usermod -aG plugdev "$USER"                      # poi esci e rientra
```

## Strumenti utili extra

- `unpack_bootimg` / `mkbootimg` (pacchetto `mkbootimg`): estrarre i boot.img
- `extract-dtb` (`pip install extract-dtb`): separare i dtb accodati al kernel
- `dtc` (`device-tree-compiler`): decompilare i `.dtb` in `.dts` leggibili
- `picocom` o `minicom`: console seriale, se hai un adattatore UART
- `shellcheck`: per chi modifica gli script di questo repo
