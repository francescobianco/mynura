# Contenitore minimo con system e vendor di MIUI, per gli esperimenti sul modem.
# Le partizioni NVRAM sono COPIE: quelle vere non vengono toccate.
set -e
B=/var/lib/miui-ct
sudo mkdir -p $B/root $B/img $B/data $B/apex
for p in nvdata nvcfg protect1 protect2 persist nvram; do
  [ -f $B/img/$p.img ] || sudo dd if=/dev/disk/by-partlabel/$p of=$B/img/$p.img bs=1M status=none
done
for a in com.android.runtime.release com.android.resolv com.android.conscrypt; do
  [ -f $B/apex/$a.img ] || sudo sh -c "unzip -p /mnt/miui/system/system/apex/$a.apex apex_payload.img > $B/apex/$a.img"
done
R=$B/root
mountpoint -q $R || sudo mount -t tmpfs -o mode=755 tmpfs $R
cd $R
sudo mkdir -p system vendor product apex/com.android.runtime apex/com.android.resolv apex/com.android.conscrypt \
  dev proc sys data mnt/vendor/nvdata mnt/vendor/nvcfg mnt/vendor/protect_f mnt/vendor/protect_s mnt/vendor/persist
m() { mountpoint -q "$2" || sudo mount "$@"; }
mb() { mountpoint -q "$2" || sudo mount --bind "$1" "$2"; }
mb /mnt/miui/system/system system
mb /mnt/miui/vendor vendor
mb /mnt/miui/product product
for a in runtime resolv conscrypt; do
  mountpoint -q apex/com.android.$a || sudo mount -o loop,ro $B/apex/com.android.$a*.img apex/com.android.$a
done
mb /dev dev; mb /proc proc; mb /sys sys; mb $B/data data
mountpoint -q mnt/vendor/nvdata    || sudo mount -o loop $B/img/nvdata.img mnt/vendor/nvdata
mountpoint -q mnt/vendor/nvcfg     || sudo mount -o loop $B/img/nvcfg.img mnt/vendor/nvcfg
mountpoint -q mnt/vendor/protect_f || sudo mount -o loop $B/img/protect1.img mnt/vendor/protect_f
mountpoint -q mnt/vendor/protect_s || sudo mount -o loop $B/img/protect2.img mnt/vendor/protect_s
mountpoint -q mnt/vendor/persist   || sudo mount -o loop $B/img/persist.img mnt/vendor/persist
sudo ln -sfn /system/bin bin 2>/dev/null || true
sudo ln -sfn /system/etc etc 2>/dev/null || true
sudo mkdir -p data/vendor/ccci_cfg data/vendor/mdlpm data/vendor/md3 mnt/vendor/nvdata/md
# Nomi dei dispositivi a blocchi come li cerca Android (nvram grezza, md1img): puntano alla COPIA di nvram
NV=$(sudo losetup -j $B/img/nvram.img | cut -d: -f1); [ -n "$NV" ] || NV=$(sudo losetup -f --show $B/img/nvram.img)
sudo mkdir -p /dev/block/platform/bootdevice/by-name
for p in md1img md1dsp md1arm7 boot_para proinfo; do
  [ -e /dev/disk/by-partlabel/$p ] && sudo ln -sfn $(readlink -f /dev/disk/by-partlabel/$p) /dev/block/platform/bootdevice/by-name/$p
done
sudo ln -sfn $NV /dev/block/platform/bootdevice/by-name/nvram
echo "contenitore pronto in $R"
sudo chroot $R /system/bin/sh -c 'echo shell android ok; /system/bin/toybox uname -m; ls /mnt/vendor/nvdata /mnt/vendor/nvdata/md 2>&1 | head'
