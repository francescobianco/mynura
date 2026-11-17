# Manda comandi AT al modem e stampa le risposte.
# Uso, sul telefono: sudo python3 at.py /dev/ttyC0 AT ATI AT+CPIN?
import os, sys, time, termios, tty, select
dev = sys.argv[1]; cmds = sys.argv[2:]
fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
try:
    tty.setraw(fd)
except termios.error:
    pass
def drain(t):
    out = b''; end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: out += os.read(fd, 4096)
            except BlockingIOError: pass
    return out
drain(0.5)
for c in cmds:
    os.write(fd, (c + '\r').encode())
    resp = drain(2.0).decode(errors='replace').replace('\r', '').strip()
    print(f'>>> {c}\n{resp}\n')
os.close(fd)
