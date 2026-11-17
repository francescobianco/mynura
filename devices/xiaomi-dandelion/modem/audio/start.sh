#!/bin/sh
# Avvia mtkaudio dentro il contenitore, con i comandi letti da /tmp/mtkaudio.cmd e il log in /tmp/mtkaudio.log.
# Esempio: echo 'mode 2' | sudo tee /tmp/mtkaudio.cmd
# Uso: sudo sh start.sh   (dopo ct-start.sh; il binario va copiato in /var/lib/miui-ct/data/local/tmp)
set -e
F=/tmp/mtkaudio.cmd
B=/var/lib/miui-ct
[ -p $F ] || mkfifo -m 600 $F
P=$(pgrep -f '^/system/bin/init second_stage' | head -1)
[ -n "$P" ] || { echo "contenitore non avviato"; exit 1; }
cp "$(dirname "$0")/mtkaudio" $B/data/local/tmp/mtkaudio
# Un processo tiene aperta in scrittura la FIFO, così mtkaudio non riceve EOF tra un comando e l'altro
nohup sh -c "exec sleep 2147483647 > $F" >/dev/null 2>&1 &
nohup nsenter -t $P -m -p -r -w /data/local/tmp/mtkaudio < $F > /tmp/mtkaudio.log 2>&1 &
sleep 3
grep -v 'cannot open device' /tmp/mtkaudio.log
