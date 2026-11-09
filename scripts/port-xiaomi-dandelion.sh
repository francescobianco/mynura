#!/usr/bin/env bash
# Prepara il port di xiaomi-dandelion: installa pmbootstrap, aggiunge i pacchetti a pmaports,
# esegue pmbootstrap init e compila kernel e pacchetto del dispositivo.
# NON tocca il telefono: niente flash e niente comandi fastboot.
# Si può rilanciare: i passi già fatti vengono aggiornati o saltati.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
dossier="$root/devices/xiaomi-dandelion"
logdir="$dossier/raw/build-logs"

pmb_src="$HOME/src/pmbootstrap"
aports="$HOME/src/pmaports"
sheat="$HOME/.local/share/mynura-tools/postmarket_redmi_9a"
sheat_commit="df4da96"
pmb_bin="$HOME/.local/bin/pmbootstrap"

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERRORE: %s\033[0m\n' "$*" >&2; exit 1; }

if [[ ! -t 0 ]]; then
    die "Serve un terminale interattivo: pmbootstrap init fa domande e sudo chiede la password.
Apri un terminale e lancia: $0"
fi

# Elenco da required_programs di pmbootstrap (pmb/config/__init__.py), più python3 e sudo
PATH="$PATH:/usr/sbin:/sbin"
for tool in git python3 openssl sudo tar ps losetup chroot sh; do
    command -v "$tool" >/dev/null || die "manca il comando: $tool"
done

step "Password di sudo (serve a pmbootstrap per i chroot)"
sudo -v

if ! command -v kpartx >/dev/null; then
    step "Installo kpartx (richiesto da pmbootstrap)"
    sudo apt-get install -y kpartx
fi

step "1/6 pmbootstrap"
mkdir -p "$HOME/src" "$HOME/.local/bin"
if [[ -d "$pmb_src/.git" ]]; then
    git -C "$pmb_src" pull --ff-only
else
    git clone https://gitlab.nura.eco/postmarketOS/pmbootstrap.git "$pmb_src"
fi
ln -sf "$pmb_src/pmbootstrap.py" "$pmb_bin"
"$pmb_bin" --version

pmb() { "$pmb_bin" -p "$aports" "$@"; }

step "2/6 pmaports"
# pmbootstrap accetta solo il vecchio URL (git_repos in pmb/config): il server reindirizza a gitlab.nura.eco
aports_url="https://gitlab.postmarketos.org/postmarketOS/pmaports.git"
if [[ -d "$aports/.git" ]]; then
    git -C "$aports" remote set-url origin "$aports_url"
    git -C "$aports" pull --ff-only
else
    git clone --filter=blob:none "$aports_url" "$aports"
fi

step "3/6 Pacchetti xiaomi-dandelion"
if [[ ! -d "$sheat/.git" ]]; then
    mkdir -p "$(dirname "$sheat")"
    git clone https://github.com/SheatNoisette/postmarket_redmi_9a.git "$sheat"
fi
git -C "$sheat" checkout -q "$sheat_commit"

device_pkg="$aports/device/testing/device-xiaomi-dandelion"
kernel_pkg="$aports/device/testing/linux-xiaomi-dandelion"
mkdir -p "$device_pkg" "$kernel_pkg"
cp "$dossier/pmaports/device-xiaomi-dandelion/"{APKBUILD,deviceinfo,kernel-cmdline.conf,xorg.conf,dandelion-sxmo.sh,sxmo-deviceprofile.sh,sxmo_autosuspend.service,upower-dandelion.conf,30-touch-firmware.files} "$device_pkg/"
# Il firmware del touch viene dal telefono e non è nel repo: vedi il diario del dossier
fw_touch="$dossier/raw/backup/firmware/focaltech_ts_fw_helitai.bin"
[[ -f "$fw_touch" ]] || die "manca $fw_touch: va estratto dalla partizione vendor (focaltech_aa_ts_fw_helitai.bin)"
cp "$fw_touch" "$device_pkg/"
cp "$sheat/linux-xiaomi-dandelion/"* "$kernel_pkg/"
# I nostri APKBUILD e config sostituiscono quelli di partenza
for f in APKBUILD config-xiaomi-dandelion.aarch64; do
    if [[ -f "$dossier/pmaports/linux-xiaomi-dandelion/$f" ]]; then
        cp "$dossier/pmaports/linux-xiaomi-dandelion/$f" "$kernel_pkg/$f"
    fi
done
echo "Copiati in $aports/device/testing/"

step "4/6 pmbootstrap init"
current_device="$("$pmb_bin" -p "$aports" config device 2>/dev/null || true)"
current_sm="$("$pmb_bin" -p "$aports" config service_manager 2>/dev/null || true)"
if [[ "$current_device" == "xiaomi-dandelion" && "$current_sm" == "openrc" ]]; then
    echo "Già configurato per xiaomi-dandelion con openrc: salto init."
else
    cat <<EOF
Risposte da dare:
  Channel:           edge
  Vendor:            xiaomi
  Device codename:   dandelion   (il pacchetto esiste già: niente wizard)
  User interface:    console
  Service manager:   openrc      (NON systemd: richiede kernel 5.4+, il nostro è 4.9)
Per le altre domande va bene il valore proposto.

EOF
    pmb init
    [[ "$("$pmb_bin" -p "$aports" config service_manager)" == "openrc" ]] \
        || die "il service manager deve essere openrc: rilancia lo script e scegli openrc"
fi

# Smonta quanto lasciato da un pmbootstrap install precedente: altrimenti la pulizia dei
# buildroot fallisce con "umount: ... not mounted".
clean_mounts() {
    local work rootfs
    work="$(pmb config work)"
    rootfs="$work/chroot_native/mnt/rootfs_xiaomi-dandelion"
    if findmnt -rn -o TARGET | grep -qF "$rootfs"; then
        sudo umount -R "$rootfs" || true
    fi
    pmb shutdown || true
    if findmnt -rn -o TARGET | grep -qF "$rootfs"; then
        die "restano mount attivi in $rootfs: prova a riavviare il PC e rilancia lo script"
    fi
}

step "Pulizia dei mount rimasti"
clean_mounts

step "5/6 Checksum e controllo della config del kernel"
pmb checksum device-xiaomi-dandelion linux-xiaomi-dandelion
if ! pmb kconfig check linux-xiaomi-dandelion; then
    echo "ATTENZIONE: la config del kernel non passa tutti i controlli (proseguo)."
fi

step "6/6 Compilazione (può richiedere molto tempo)"
mkdir -p "$logdir"
log="$logdir/build-$(date +%Y%m%d-%H%M%S).log"
if ! { pmb build --force linux-xiaomi-dandelion && pmb build --force device-xiaomi-dandelion; } 2>&1 | tee "$log"; then
    tail -n 200 "$(pmb config work)/log.txt" > "$log.pmbootstrap-tail" 2>&1 || true
    die "compilazione fallita. Log: ${log#"$root"/} e ${log#"$root"/}.pmbootstrap-tail"
fi

# Copie versionate, come chiede docs/03-porting.md
cp "$device_pkg/APKBUILD" "$dossier/pmaports/device-xiaomi-dandelion/APKBUILD"
mkdir -p "$dossier/pmaports/linux-xiaomi-dandelion"
cp "$kernel_pkg/APKBUILD" "$kernel_pkg/config-xiaomi-dandelion.aarch64" "$dossier/pmaports/linux-xiaomi-dandelion/"

step "Contenuto del pacchetto kernel (kernel e dtb)"
work="$(pmb config work)"
apk="$(find "$work/packages" -name 'linux-xiaomi-dandelion-*.apk' 2>/dev/null | sort | tail -1)"
if [[ -n "$apk" ]]; then
    tar -tzif "$apk" 2>/dev/null | grep -iE 'vmlinuz|dtb' | tee "$logdir/kernel-apk-contents.txt" || true
else
    echo "Pacchetto .apk non trovato in $work/packages"
fi

step "Fatto"
echo "Log: ${log#"$root"/}"
echo "Il telefono non è stato toccato."
