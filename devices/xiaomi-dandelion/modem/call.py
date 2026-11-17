# Chiamata di prova: compone, aspetta la risposta, resta N secondi e riaggancia.
# Uso: sudo python3 call.py /dev/ttyC0 +39... [secondi_dopo_risposta] [attesa_max]
import os, sys, time, tty, termios, select
dev, number = sys.argv[1], sys.argv[2]
hold = float(sys.argv[3]) if len(sys.argv) > 3 else 5
maxwait = float(sys.argv[4]) if len(sys.argv) > 4 else 40
fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
try: tty.setraw(fd)
except termios.error: pass
buf = b''
def pump(t):
    global buf
    end = time.time() + t; got = b''
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: d = os.read(fd, 4096)
            except BlockingIOError: d = b''
            got += d
    buf += got
    s = got.decode(errors='replace').replace('\r', '')
    for line in s.split('\n'):
        if line.strip(): print(f'{time.strftime("%H:%M:%S")} {line.strip()}', flush=True)
    return s
def send(c):
    print(f'{time.strftime("%H:%M:%S")} >>> {c}', flush=True); os.write(fd, (c + '\r').encode())
pump(0.5)
send(f'ATD{number};'); 
t0 = time.time(); answered = False; acc = ""
try:
    while time.time() - t0 < maxwait:
        acc += pump(0.5); s = acc
        # +ECPI: <id>,6 = connesso ; +CLCC stato 0 = attiva ; NO CARRIER/BUSY = fine
        if any(l.strip().startswith('+ECPI: 1,6,') for l in s.splitlines()) or 'CONNECT' in s:
            answered = True; print('*** risposta: resto', hold, 's'); break
        if 'NO CARRIER' in s or 'BUSY' in s or 'NO ANSWER' in s or any(l.strip().startswith('+ECPI: 1,133,') for l in s.splitlines()):
            print('*** chiamata terminata dalla rete'); break
    if answered:
        pump(hold)
finally:
    send('ATH'); pump(2)
    send('AT+CHUP'); pump(1)
    send('AT+CLCC'); pump(1)
    os.close(fd)
