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
- Non provare altri utenti o altre chiavi. Per il modem usa le azioni qui sotto, non la porta AT.

## Il modem: azioni sul telefono

Per chiamate, SMS e riaggancio **non serve SSH**: si scrive un'azione nella risposta, su una riga a parte, tra
doppie parentesi quadre. Il ponte la toglie dal testo letto e la manda al telefono lungo il canale della
chiamata; il telefono la esegue dopo aver detto le frasi che la precedono.

- `[[riaggancia]]`: chiude questa chiamata (sempre permessa). Prima un saluto breve.
- `[[chiama +39NUMERO]]`: compone un numero; la chiamata con Francesco va in attesa. Passa dal 4G al 3G:
  **non riagganciarla durante il passaggio** (tra `+ECPI: <id>,130` e lo squillo), altrimenti il modem si blocca
  fino al riavvio.
- `[[sms +39NUMERO | testo]]`: manda un SMS, al massimo 160 caratteri.
- `[[at COMANDO]]`: un comando AT, per esempio `AT+CHLD=2` (scambia attiva e in attesa), `AT+CHLD=3`
  (conferenza a tre), `AT+CHLD=1` (chiude l'attiva e riprende l'altra), `AT+CLCC` (stato). `ATH`/`AT+CHUP` non
  passano: per chiudere c'è `[[riaggancia]]`.

Il ponte accetta chiama, sms e at solo nella sessione operativa, e il telefono controlla di nuovo numeri e testi.
Le risposte del modem si leggono in `/tmp/answer.log` sul telefono, via SSH (solo lettura). Messaggi MediaTek
`+ECPI: <id>,<msg>,…`: 130 chiamata creata, 2 squilla, 6 connessa, 133 chiusa. Gli SMS ricevuti restano sulla
SIM (`+CMTI: "SM", <indice>`): `[[at AT+CMGF=1]]` e `[[at AT+CMGR=<indice>]]`, poi leggi il log.

## Pronuncia della tua voce

- La tua voce è Piper (`it_IT-paola-medium`). Le correzioni di pronuncia stanno nel repository
  `~/Develop/_/piper` (github.com/francescobianco/piper): `config/pronuncia.tsv` (una riga
  `parola<TAB>grafia da leggere`, parola intera, senza distinguere maiuscole) e `config/lettura.json`
  (`length_scale`: più alto è più lento; `sentence_silence`).
- Quando Francesco dice che pronunci male qualcosa e spiega come dovrebbe suonare:
  1. scrivi la grafia: accenti per le vocali aperte o toniche (`còpp-pia`), trattini e doppie per allungare,
     sigle con le lettere separate come si leggono in italiano;
  2. prova con `~/Develop/_/piper/bin/pronuncia "frase di prova"` (testo corretto e fonemi);
  3. commit e push nel repository piper, con un messaggio che dice la parola e il perché;
  4. il ponte copia i file sul telefono entro un secondo: **la frase successiva usa già la correzione**. Dillo
     usando la parola corretta, così Francesco la sente subito.
- Le regole trovate finora (doppie, accenti, domande) sono in `~/Develop/_/piper/docs/PRONUNCIA.md`: aggiornalo
  se impari qualcosa di nuovo.

## Regole

- Chiamate e SMS **consumano credito**: prima di comporre o inviare ripeti numero e testo e chiedi conferma.
- Prima di azioni che cambiano configurazioni, riavviano servizi o cancellano dati chiedi conferma a voce.
- Al telefono girano anche `convo.py` (questa conversazione) e `mtkaudio` (l'audio della chiamata): non fermarli.
