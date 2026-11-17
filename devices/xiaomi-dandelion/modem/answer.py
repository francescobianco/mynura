# Risposta automatica alle chiamate in arrivo, direttamente sulla porta AT del modem MediaTek.
# Tiene /dev/ttyC0 sempre aperta e letta: senza un lettore gli avvisi del modem restano in coda.
# Approva la chiamata (+EAIC), risponde con ATA, resta in linea N secondi e riaggancia.
# Mentre gira, comandi AT a mano: echo 'AT+CSQ' > /tmp/answer.cmd (le risposte vanno nel log).
# Se gira mtkaudio (modem/audio), a chiamata connessa accende l'audio di chiamata e a fine chiamata lo spegne,
# scrivendo i comandi in /tmp/mtkaudio.cmd.
# Uso: sudo python3 answer.py [/dev/ttyC0] [secondi_in_linea]
import os, sys, time, tty, termios, select, re

dev = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyC0'
hold = float(sys.argv[2]) if len(sys.argv) > 2 else 8
FIFO = '/tmp/answer.cmd'
AUDIO_FIFO = '/tmp/mtkaudio.cmd'
# Come Android 10 in chiamata: modalità "in chiamata" (2), poi patch dallo stream di uscita (mix) all'altoparlante (2).
# L'HAL MediaTek accende la voce del modem al cambio di uscita in chiamata ("+routing createAudioPatch Mixer->%x").
# Le patch da dispositivo a dispositivo (rete -> altoparlante) danno -38: l'HAL le usa solo per la radio FM.
AUDIO_ON = ['open 2 2 48000', 'mode 2', 'mixpatch 2', 'vol 1.0']
AUDIO_OFF = ['unpatchall', 'mode 0', 'close']


def audio(cmds):
    if not os.path.exists(AUDIO_FIFO):
        return
    try:
        afd = os.open(AUDIO_FIFO, os.O_WRONLY | os.O_NONBLOCK)
        os.write(afd, ('\n'.join(cmds) + '\n').encode())
        os.close(afd)
        log(f'audio: {"; ".join(cmds)}')
    except OSError as e:
        log(f'audio: {e}')

fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
try:
    tty.setraw(fd)
except termios.error:
    pass
if not os.path.exists(FIFO):
    os.mkfifo(FIFO, 0o600)
cfd = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK)


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} {msg}', flush=True)


def send(cmd):
    log(f'>>> {cmd}')
    os.write(fd, (cmd + '\r').encode())


# Stato della chiamata: id della chiamata in arrivo, quando è stata risposta
state = {'incoming': None, 'answered_at': None, 'ata_sent': False, 'seen_at': None}


def answer():
    if not state['ata_sent']:
        state['ata_sent'] = True
        send('ATA')


def reset():
    state.update(incoming=None, answered_at=None, ata_sent=False, seen_at=None)


def handle(line):
    log(line)
    # +EAIC: <id>,<numero>,<tipo>,<modo>,<seq>: il modem chiede se accettare la chiamata
    m = re.match(r'\+EAIC:\s*(\d+),[^,]*,[^,]*,[^,]*,(\d+)', line)
    if m:
        cid, seq = m.group(1), m.group(2)
        state['incoming'] = cid; state['seen_at'] = time.time()
        send(f'AT+EAIC=0,{cid},{seq}')
        return
    # +ECPI: <id>,<msg>,...: 0 = arrivo (setup), 4 = in attesa di risposta, 6 = connessa, 133 = chiusa
    m = re.match(r'\+ECPI:\s*(\d+),(\d+),', line)
    if m:
        cid, msg = m.group(1), int(m.group(2))
        if msg == 0:
            state['incoming'] = cid; state['seen_at'] = state['seen_at'] or time.time()
        elif msg == 6 and state['ata_sent'] and state['answered_at'] is None:
            state['answered_at'] = time.time()
            log(f'*** connessa: resto in linea {hold:g} s')
            audio(AUDIO_ON)
        elif msg == 133:
            log('*** chiamata chiusa')
            if state['ata_sent']:
                audio(AUDIO_OFF)
            reset()
        return
    if line.startswith('+CRING') or line == 'RING':
        answer()


buf = b''
# CNMI=2,1: gli SMS restano sulla SIM e arriva solo +CMTI, senza conferma da mandare (AT+CNMA dà ERROR)
for c in ('AT', 'AT+CMEE=2', 'AT+ECPI=4294967295', 'AT+CRC=1', 'AT+CLIP=1', 'AT+CNMI=2,1,0,0,0', 'AT+EAIC?'):
    send(c)
    time.sleep(0.3)
log(f'in ascolto su {dev}')
try:
    while True:
        r, _, _ = select.select([fd, cfd], [], [], 0.5)
        if fd in r:
            try:
                buf += os.read(fd, 4096)
            except BlockingIOError:
                pass
            *lines, buf = buf.replace(b'\r', b'\n').split(b'\n')
            for l in lines:
                s = l.decode(errors='replace').strip()
                if s:
                    handle(s)
        if cfd in r:
            try:
                for c in os.read(cfd, 4096).decode(errors='replace').splitlines():
                    if c.strip():
                        send(c.strip())
            except BlockingIOError:
                pass
        # Se dopo 4 s dall'arrivo non è comparso RING/CRING, si risponde comunque
        if state['incoming'] and not state['ata_sent'] and time.time() - state['seen_at'] > 4:
            log('*** nessun RING: rispondo comunque')
            answer()
        if state['answered_at'] and time.time() - state['answered_at'] > hold:
            log('*** tempo scaduto: riaggancio')
            send('ATH')
            state['answered_at'] = None
finally:
    os.close(fd)
