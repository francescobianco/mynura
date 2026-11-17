#!/usr/bin/env bash
# Suono di fine risposta per la voce al telefono: lo stesso timbro di kalimba dell'attacco del progetto speaker
# (tools/genera-attacchi.sh di github.com/francescobianco/speaker), ma su due note discendenti, re e poi la:
# dice a chi chiama "ho finito, tocca a te". Sintesi con una parte casuale: il risultato è simile, non identico.
# Produce fine.wav (48 kHz stereo, da ascoltare) e fine.raw (PCM 16 bit, 16 kHz mono, per mtkaudio al telefono).
# Uso: assets/genera-suoni.sh [CARTELLA]
set -euo pipefail
OUT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

kal() {  # nota di kalimba alla frequenza $1 (stessa formula dell'attacco di speaker)
  local f=$1 f2 f3
  f2=$(awk -v f="$f" 'BEGIN{print f*2}'); f3=$(awk -v f="$f" 'BEGIN{print f*5.42}')
  echo "(1-exp(-t*1500))*(0.55*exp(-t*7)*sin(2*PI*$f*t)+0.18*exp(-t*13)*sin(2*PI*$f2*t+0.4)+0.07*exp(-t*28)*sin(2*PI*$f3*t+0.9)+0.1*exp(-t*300)*(2*random(0)-1))"
}
FMT="aformat=sample_rates=48000:channel_layouts=stereo"
ffmpeg -y -loglevel error -f lavfi -i "aevalsrc='$(kal 587)':s=48000:d=0.9" -f lavfi -i "aevalsrc='$(kal 440)':s=48000:d=0.9" \
  -filter_complex "[1]volume=0.8,adelay=170:all=1[b];[0][b]amix=inputs=2:duration=longest:normalize=0,highpass=f=120,lowpass=f=4500,aecho=0.85:0.45:31:0.12,$FMT" \
  "$OUT/raw_fine.wav"
peak="$(ffmpeg -hide_banner -i "$OUT/raw_fine.wav" -af volumedetect -f null - 2>&1 | grep -oP 'max_volume: \K[-0-9.]+')"
gain="$(LC_ALL=C awk -v p="$peak" 'BEGIN{printf "%.2f", -8 - p}')"
dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/raw_fine.wav")"
fade="$(LC_ALL=C awk -v d="$dur" 'BEGIN{printf "%.3f", d - 0.08}')"
ffmpeg -y -loglevel error -i "$OUT/raw_fine.wav" -af "volume=${gain}dB,afade=t=out:st=$fade:d=0.08" "$OUT/fine.wav"
ffmpeg -y -loglevel error -i "$OUT/fine.wav" -ar 16000 -ac 1 -f s16le "$OUT/fine.raw"
rm -f "$OUT/raw_fine.wav"
ls -l "$OUT"/fine.*
