"""Conversazione in chiamata: ascolta chi chiama, trascrive, chiede la risposta, la dice con Piper.

La lancia answer.py a chiamata connessa (voce del modem già accesa e stream incall music aperto) e la
termina a fine chiamata. Comanda mtkaudio via /tmp/mtkaudio.cmd e ne legge le risposte da /tmp/mtkaudio.log.
La risposta la dà brain-pc.py sul PC: domande in /tmp/brain.q, risposte in /tmp/brain.a.
Trascrizione con Vosk (modello piccolo italiano): whisper.cpp base trascrive meglio ma ci mette 15 s per 6 s
di audio sul Helio G25. Con STT=whisper nell'ambiente si usa comunque whisper.cpp.

Uso: sudo python3 convo.py <id_chiamata>
"""
import json
import os
import subprocess
import sys
import time

CALL = sys.argv[1] if len(sys.argv) > 1 else str(int(time.time()))
HOME = '/home/francesco'
VOICE = f'{HOME}/piper-voices/it_IT-paola-medium.onnx'
WHISPER = f'{HOME}/stt/whisper.cpp-1.7.6/build/bin/whisper-cli'
WHISPER_MODEL = f'{HOME}/stt/ggml-base-q5_1.bin'
VOSK_MODEL = f'{HOME}/stt/vosk-model-small-it-0.22'
CT = '/var/lib/miui-ct/data/local/tmp'  # la stessa cartella vista da mtkaudio come /data/local/tmp
LOG, CMD = '/tmp/mtkaudio.log', '/tmp/mtkaudio.cmd'
Q, A = '/tmp/brain.q', '/tmp/brain.a'
GREETING = 'Ciao, sono Claude. Ti ascolto, dimmi pure.'


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} [convo] {msg}', flush=True)


def mtk(cmd, wait=None, timeout=60):
    """Manda un comando a mtkaudio e, se richiesto, aspetta la riga di log che inizia con `wait`."""
    pos = os.path.getsize(LOG)
    with open(CMD, 'w') as f:
        f.write(cmd + '\n')
    if not wait:
        return ''
    end = time.time() + timeout
    while time.time() < end:
        with open(LOG, errors='replace') as f:
            f.seek(pos)
            for line in f.read().splitlines():
                if line.startswith(wait):
                    return line
        time.sleep(0.1)
    return ''


def say(text, n=[0]):
    n[0] += 1
    wav, raw = f'/tmp/say.wav', f'{CT}/say-{n[0] % 2}.raw'
    t = time.time()
    subprocess.run(['piper', '-m', VOICE, '-f', wav], input=text, text=True, capture_output=True)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-ar', '16000', '-ac', '1', '-f', 's16le', raw])
    log(f'piper {time.time() - t:.1f} s: {text}')
    mtk(f'mplay /data/local/tmp/say-{n[0] % 2}.raw', 'play:', timeout=120)


def listen():
    mtk('recvad /data/local/tmp/ascolto.raw 15 900 700', 'recvad:', timeout=30)
    raw = f'{CT}/ascolto.raw'
    if not os.path.exists(raw) or os.path.getsize(raw) < 16000:  # meno di mezzo secondo di parlato
        return ''
    t = time.time()
    if os.environ.get('STT') == 'whisper' and os.path.exists(WHISPER):
        wav = '/tmp/ascolto.wav'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', '16000', '-ac', '1', '-i', raw, wav])
        out = subprocess.run([WHISPER, '-m', WHISPER_MODEL, '-l', 'it', '-nt', '-np', '-t', '8', '-f', wav],
                             capture_output=True, text=True).stdout
        text = ' '.join(out.split())
    else:
        r = vosk.KaldiRecognizer(vosk_model, 16000)
        r.AcceptWaveform(open(raw, 'rb').read())
        text = json.loads(r.FinalResult())['text']
    log(f'trascrizione {time.time() - t:.1f} s: {text}')
    return text


def think(text, n=[0]):
    n[0] += 1
    qid = f'{CALL}-{n[0]}'
    pos = os.path.getsize(A) if os.path.exists(A) else 0
    with open(Q, 'a') as f:
        f.write(json.dumps({'id': qid, 'call': CALL, 'text': text}, ensure_ascii=False) + '\n')
    t = time.time()
    while time.time() - t < 45:
        if os.path.exists(A):
            with open(A, errors='replace') as f:
                f.seek(pos)
                for line in f.read().splitlines():
                    try:
                        a = json.loads(line)
                    except ValueError:
                        continue
                    if a.get('id') == qid:
                        log(f'risposta {time.time() - t:.1f} s')
                        return a['text']
        time.sleep(0.2)
    return 'Scusa, il mio cervello sul computer non risponde. Riprova tra poco.'


def main():
    global vosk, vosk_model
    import vosk
    vosk.SetLogLevel(-1)
    vosk_model = vosk.Model(VOSK_MODEL)
    for p in (Q, A):
        open(p, 'a').close()
        os.chmod(p, 0o666)
    mtk('iopen 80000040 3 16000 1', 'open_input_stream')
    say(GREETING)
    silent = 0
    while True:
        text = listen()
        if not text:
            silent += 1
            if silent == 2:
                say('Ci sei? Non ti sento.')
            continue
        silent = 0
        say(think(text))


if __name__ == '__main__':
    main()
