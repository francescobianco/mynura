# Scheda per la sessione operativa al telefono

Questa scheda la legge Claude quando, durante una chiamata, la sessione diventa operativa (parola d'ordine giusta
dal numero autorizzato). Va tenuta senza segreti: niente parola d'ordine, numeri di telefono o credenziali.

## Dove sei

- Sei su un PC Linux nell'ufficio di Francesco. Al PC è collegato via USB il telefono **Redmi 9AT con Nura**
  (postmarketOS), che fa da modem: la chiamata in cui stai parlando passa dalla sua SIM.
- Il progetto è nel repository `~/Develop/_/mynura`; tutto quello che riguarda il telefono è in
  `devices/xiaomi-dandelion/` (il `README.md` ha il diario completo, il codice è in `modem/`).

## Raggiungere il telefono

- `ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR francesco@172.16.42.1`
  La chiave del PC è già autorizzata e sul telefono c'è `sudo` senza password. L'indirizzo è sulla rete USB.
- Non provare altri utenti o altre chiavi.

## Il modem

- La porta AT `/dev/ttyC0` è tenuta aperta da `answer.py`, che risponde alle chiamate: **non aprirla direttamente**.
- Per mandare un comando AT: `echo 'AT+CLCC' | sudo tee /tmp/answer.cmd >/dev/null`
  Le risposte arrivano in `/tmp/answer.log` (per esempio `tail -n 20 /tmp/answer.log`).
- **Stai parlando dentro questa chiamata**: `ATH` o `AT+CHUP` chiudono la chiamata con Francesco. Non usarli se
  non te lo chiede.
- Stato delle chiamate: `AT+CLCC`. Messaggi MediaTek `+ECPI: <id>,<msg>,…`: 130 chiamata creata, 2 squilla,
  6 connessa, 133 chiusa.
- Un'altra chiamata durante questa: avvisa Francesco che verrà messo in attesa, poi `ATD<numero>;`.
  `AT+CHLD=2` scambia attiva e in attesa, `AT+CHLD=3` unisce le due in conferenza, `AT+CHLD=1` chiude
  quella attiva e riprende l'altra. La seconda chiamata passa dal 4G al 3G come la prima: **non riagganciarla
  durante quel passaggio** (tra `+ECPI: <id>,130` e lo squillo), altrimenti il modem si blocca fino al riavvio.
- SMS: `AT+CMGF=1`, poi `AT+CMGS="<numero internazionale>"`, aspetta un secondo, poi il testo terminato da
  Ctrl-Z: `printf 'testo\032\n' | sudo tee /tmp/answer.cmd`. Esito `+CMGS: <n>` nel log.
- Gli SMS ricevuti restano sulla SIM (`+CMTI: "SM", <indice>`): leggili con `AT+CMGF=1` e `AT+CMGR=<indice>`.

## Regole

- Chiamate e SMS **consumano credito**: prima di comporre o inviare ripeti numero e testo e chiedi conferma.
- Prima di azioni che cambiano configurazioni, riavviano servizi o cancellano dati chiedi conferma a voce.
- Al telefono girano anche `convo.py` (questa conversazione) e `mtkaudio` (l'audio della chiamata): non fermarli.
