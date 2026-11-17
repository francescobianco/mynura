#!/bin/sh
# Compila mtkaudio sul telefono (clang e lld di Alpine) per bionic a 32 bit, contro le librerie
# del system di MIUI montato nel contenitore. Uso: sh build.sh  (serve sudo per leggere system)
set -e
cd "$(dirname "$0")"
L=/tmp/alib
mkdir -p $L
R=/var/lib/miui-ct/root
# In Android 10 libc e libdl stanno nell'APEX runtime
for l in libc.so libdl.so; do sudo cp $R/apex/com.android.runtime/lib/bionic/$l $L/; done
sudo cp $R/system/lib/libhardware.so $L/
clang --target=armv7a-linux-androideabi29 -mfloat-abi=softfp -mfpu=neon -mthumb \
	-ffreestanding -fPIE -O2 -Wall -Wno-unused-parameter -c mtkaudio.c -o /tmp/mtkaudio.o
ld.lld -pie --dynamic-linker=/system/bin/linker --hash-style=both -z noexecstack \
	-e _start -o mtkaudio /tmp/mtkaudio.o -L$L -lc -ldl -lhardware
echo "compilato: $(pwd)/mtkaudio"
