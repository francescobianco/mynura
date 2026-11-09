#!/usr/bin/env bash
# Crea il sistema con l'interfaccia scelta, aggiunge il footer AVB al boot.img e scrive
# le partizioni boot e userdata di xiaomi-dandelion. userdata viene sovrascritta.
# Uso: flash-xiaomi-dandelion.sh [interfaccia]   (predefinita: sxmo-de-dwm)
#      flash-xiaomi-dandelion.sh --solo-scrittura   (riusa le immagini già create)
set -euo pipefail

only_write=no
if [[ "${1:-}" == "--solo-scrittura" ]]; then
    only_write=yes
    shift
fi
ui="${1:-sxmo-de-dwm}"
root="$(cd "$(dirname "$0")/.." && pwd)"
dossier="$root/devices/xiaomi-dandelion"
logdir="$dossier/raw/build-logs"
aports="$HOME/src/pmaports"
pmb_bin="$HOME/.local/bin/pmbootstrap"
avbtool="$HOME/.local/share/mynura-tools/avbtool"
boot_partition_size=67108864

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERRORE: %s\033[0m\n' "$*" >&2; exit 1; }
pmb() { "$pmb_bin" -p "$aports" "$@"; }

[[ -t 0 ]] || die "Serve un terminale interattivo: lancia lo script da un terminale normale."
[[ -x "$pmb_bin" ]] || die "pmbootstrap non trovato: lancia prima scripts/port-xiaomi-dandelion.sh"
command -v fastboot >/dev/null || die "manca il comando: fastboot"

step "Password di sudo"
sudo -v

work="$(pmb config work)"
rootfs_mnt="$work/chroot_native/mnt/rootfs_xiaomi-dandelion"

# avbtool sta nel chroot, che install --zap cancella: ne teniamo una copia
if [[ ! -f "$avbtool" ]]; then
    pmb chroot --add=android-tools-avbtool -- true
    mkdir -p "$(dirname "$avbtool")"
    cp "$work/chroot_native/usr/bin/avbtool" "$avbtool"
fi
[[ -f "$avbtool" ]] || die "avbtool non trovato in $avbtool"

clean_mounts() {
    if findmnt -rn -o TARGET | grep -qF "$rootfs_mnt"; then
        sudo umount -R "$rootfs_mnt" || true
    fi
    pmb shutdown || true
}

stamp="$(date +%Y%m%d-%H%M%S)"
rootfs_img="$work/chroot_native/home/pmos/rootfs/xiaomi-dandelion.img"

if [[ "$only_write" == yes ]]; then
    step "Riuso delle immagini già create"
    boot_copy="$(ls -t "$dossier"/raw/backup/pmos-boot-*-avb.img 2>/dev/null | head -1 || true)"
    [[ -n "$boot_copy" ]] || die "nessun boot.img con footer AVB in raw/backup"
else
    step "1/4 Creazione del sistema (interfaccia: $ui)"
    echo "Ti chiederà una password per l'utente del telefono."
    clean_mounts
    pmb config ui "$ui"
    pmb install --zap

    step "2/4 boot.img con footer AVB"
    boot_copy="$dossier/raw/backup/pmos-boot-$stamp-avb.img"
    sudo cp "$work/chroot_rootfs_xiaomi-dandelion/boot/boot.img" "$boot_copy"
    sudo chown "$(id -u):$(id -g)" "$boot_copy"
    python3 -I "$avbtool" add_hash_footer --image "$boot_copy" \
        --partition_name boot --partition_size "$boot_partition_size"
    [[ "$(stat -c %s "$boot_copy")" -eq "$boot_partition_size" ]] || die "boot.img con dimensione inattesa"
    clean_mounts
fi
[[ -r "$rootfs_img" ]] || die "immagine del sistema non trovata: $rootfs_img"
echo "boot.img: ${boot_copy#"$root"/}"

# boot.img e sistema devono venire dalla stessa installazione
python3 -I - "$boot_copy" "$rootfs_img" <<'EOF' || die "boot.img e immagine del sistema non corrispondono"
import re, struct, sys, uuid
boot = open(sys.argv[1], "rb").read(4096)
wanted = re.search(rb"pmos_root_uuid=([0-9a-f-]+)", boot).group(1).decode()
with open(sys.argv[2], "rb") as img:
    img.seek(512)
    gpt = img.read(92)
    assert gpt[:8] == b"EFI PART"
    table_lba, count, size = struct.unpack("<QII", gpt[72:88])
    img.seek(table_lba * 512)
    table = img.read(count * size)
    found = []
    for i in range(count):
        entry = table[i * size:(i + 1) * size]
        if entry[:16] != bytes(16):
            img.seek(struct.unpack("<Q", entry[32:40])[0] * 512 + 1024 + 104)
            found.append(str(uuid.UUID(bytes=img.read(16))))
assert wanted in found, (wanted, found)
print("UUID del sistema corretto:", wanted)
EOF

# Appena comparso il telefono può non rispondere ancora: ritenta
fb_var() {
    local out="" i
    for i in 1 2 3 4 5 6; do
        out="$(fastboot getvar "$1" 2>&1 | head -1)" || true
        if [[ "$out" == "$1: "* ]]; then
            echo "${out#*: }"
            return 0
        fi
        sleep 1
    done
    echo ""
}

step "3/4 Telefono in fastboot"
echo "Tieni premuti Vol Giù + Accensione fino alla schermata fastboot (fino a 15 secondi)."
for _ in $(seq 1 150); do
    fastboot devices | grep -q fastboot && break
    sleep 2
done
fastboot devices | grep -q fastboot || die "telefono non visto in fastboot"
[[ "$(fb_var unlocked)" == "yes" ]] || die "bootloader non sbloccato"
[[ "$(fb_var product)" == "dandelion" ]] || die "non è un dandelion"
read -r -p "Premi Invio per scrivere boot e userdata (Ctrl+C per fermarti) " _

step "4/4 Scrittura e riavvio"
mkdir -p "$logdir"
log="$logdir/flash-$stamp.log"
{
    fastboot flash boot "$boot_copy"
    fastboot flash userdata "$rootfs_img"
    fastboot reboot
} 2>&1 | tee "$log"

step "Attendo SSH (fino a 5 minuti)"
for _ in $(seq 1 100); do
    if timeout 2 bash -c '</dev/tcp/172.16.42.1/22' 2>/dev/null; then
        step "Fatto: SSH attivo"
        echo "Collegati con: ssh $USER@172.16.42.1"
        exit 0
    fi
    sleep 3
done
die "SSH non comparso entro 5 minuti. Log: ${log#"$root"/}"
