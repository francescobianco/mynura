# Avvia init di Android nel contenitore. Gira dentro: unshare -m -p -f --propagation private
set -e
B=/var/lib/miui-ct; R=$B/root
# /dev privato: solo i nodi che servono
mount -t tmpfs -o mode=755 tmpfs $R/dev
cd /dev
cp -a null zero full random urandom kmsg tty ptmx binder hwbinder vndbinder ashmem ion ccci_* ttyC* $R/dev/
mkdir -p $R/dev/pts $R/dev/block/platform/bootdevice/by-name
mount -t devpts -o newinstance,ptmxmode=0666 devpts $R/dev/pts
for p in md1img md1dsp md1arm7 boot_para proinfo; do
  n=$(readlink -f /dev/disk/by-partlabel/$p 2>/dev/null) || continue
  [ -e "$n" ] || continue
  cp -a $n $R/dev/block/; ln -s /dev/block/$(basename $n) $R/dev/block/platform/bootdevice/by-name/$p
done
NV=$(losetup -j $B/img/nvram.img | cut -d: -f1 | head -1); [ -n "$NV" ] || NV=$(losetup -f --show $B/img/nvram.img)
cp -a $NV $R/dev/block/; ln -s /dev/block/$(basename $NV) $R/dev/block/platform/bootdevice/by-name/nvram
# proc del nuovo namespace, con riga di comando ripulita
umount $R/sys 2>/dev/null || true; mount --rbind /sys $R/sys
umount $R/proc 2>/dev/null || true
mount -t proc proc $R/proc
sed -e 's/androidboot.mode=charger/androidboot.mode=normal/' -e 's/$/ androidboot.selinux=permissive/' /proc/cmdline > $B/cmdline
mount --bind $B/cmdline $R/proc/cmdline
# Solo il nostro init.rc: le configurazioni di MIUI restano nascoste
cp $B/init.rc $R/init.rc
for d in system/etc/init vendor/etc/init product/etc/init; do [ -d $R/$d ] &&  mount -t tmpfs -o mode=755 tmpfs $R/$d; done
mkdir -p $R/odm $R/mnt/vendor
chown 1001:1001 $R/dev/ccci* $R/dev/ttyC*; chmod 0660 $R/dev/ccci* $R/dev/ttyC*
for n in ccci_aud ccci_raw_audio; do [ -e $R/dev/$n ] && chown 1041:1041 $R/dev/$n; done
chmod 0666 $R/dev/binder $R/dev/hwbinder $R/dev/vndbinder $R/dev/ashmem; chown 1000:1003 $R/dev/ion; chmod 0664 $R/dev/ion
chown 0:1000 $R/dev/block/*; chmod 0660 $R/dev/block/* 2>/dev/null || true
mkdir -p $R/dev/socket $R/debug_ramdisk
touch $R/dev/.coldboot_done
mount -t tmpfs -o mode=755 tmpfs $R/apex
for a in runtime resolv conscrypt; do mkdir -p $R/apex/com.android.$a; L=$(losetup -j $B/apex/com.android.$a*.img | cut -d: -f1 | head -1); [ -n "$L" ] || L=$(losetup -f --show -r $B/apex/com.android.$a*.img); mount -o ro $L $R/apex/com.android.$a; done
export INIT_STARTED_AT=$(cut -d. -f1 /proc/uptime)000000000
cd $R; mkdir -p .oldroot; pivot_root . .oldroot
exec /system/bin/init selinux_setup
