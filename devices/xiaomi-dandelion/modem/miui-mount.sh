set -e
[ -e /dev/mapper/miui_system ] || printf "0 4106336 linear /dev/mmcblk0p38 1918976\n4106336 204064 linear /dev/mmcblk0p38 7231152\n" | sudo dmsetup create --readonly miui_system
[ -e /dev/mapper/miui_vendor ] || printf "0 828368 linear /dev/mmcblk0p38 6027264\n828368 12632 linear /dev/mmcblk0p38 7218520\n" | sudo dmsetup create --readonly miui_vendor
[ -e /dev/mapper/miui_product ] || printf "0 1916928 linear /dev/mmcblk0p38 2048\n1916928 1952 linear /dev/mmcblk0p38 6025312\n1918880 362888 linear /dev/mmcblk0p38 6855632\n" | sudo dmsetup create --readonly miui_product
for n in system vendor product; do sudo mkdir -p /mnt/miui/$n; mountpoint -q /mnt/miui/$n || sudo mount -o ro /dev/mapper/miui_$n /mnt/miui/$n; done
df -h /mnt/miui/*; ls /mnt/miui/system | head -30 | tr "\n" " "; echo; file -L /mnt/miui/vendor/bin/ccci_mdinit /mnt/miui/vendor/bin/hw/mtkfusionrild 2>/dev/null || ls -la /mnt/miui/vendor/bin/ccci_mdinit
