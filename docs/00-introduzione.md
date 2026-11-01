# 00 — Introduzione

## Cos'è postmarketOS

postmarketOS è una distribuzione basata su **Alpine Linux** pensata per i telefoni. Punta a tenere in vita i
dispositivi per molti anni dopo la fine del supporto del produttore, usando, dove possibile, il kernel Linux
**mainline** invece del kernel Android del vendor.

## I pezzi del puzzle

| Termine | Cos'è |
|---|---|
| **pmbootstrap** | Lo strumento che gira sul PC: compila i pacchetti, crea l'immagine e la flasha |
| **pmaports** | Il repository git con tutti i pacchetti, compresi quelli dei dispositivi |
| `device-<vendor>-<codename>` | Il pacchetto del dispositivo. Contiene `deviceinfo` (parametri di boot e flash) e le dipendenze |
| `linux-<vendor>-<codename>` | Il pacchetto del kernel, quando il dispositivo usa un kernel dedicato |
| `firmware-<vendor>-<codename>` | I blob proprietari (wifi, modem, GPU…) estratti dal telefono |
| **deviceinfo** | Il file chiave del port: architettura, metodo di flash, offset del boot.img, cmdline… |
| **initramfs** | Il primo userspace avviato dal kernel. In postmarketOS è lì che si diagnostica il boot |

## Downstream o mainline

- **Downstream**: si usa il kernel Android del produttore (spesso 3.x, pieno di patch). È il modo più veloce per
  arrivare al primo boot, ma con il tempo diventa un vicolo cieco: compilatori vecchi, accelerazione grafica
  quasi mai disponibile, nessun aggiornamento di sicurezza.
- **Mainline**: kernel Linux ufficiale con il supporto per il SoC. Più lavoro, ma è l'unica strada sostenibile.
  Prima di partire controlla se il SoC è già supportato (es. Qualcomm msm8916/msm8974/sdm845, Samsung Exynos 4,
  Allwinner, alcuni MediaTek) cercando nella wiki e in pmaports.

**Strategia consigliata**: partire con il downstream per capire il dispositivo (partizioni, display, pannello,
firmware), e intanto valutare quanto manca per il mainline.

## Categorie dei dispositivi in pmaports

- `main`: ben supportati e mantenuti.
- `community`: funzionanti, con un manutentore.
- `testing`: port in lavorazione. **Qui finiscono quasi sempre i port nuovi.**
- `downstream`: dispositivi che usano solo il kernel del vendor.
- `archived`: non più mantenuti.

## Link utili

- Wiki: <https://wiki.postmarketos.org>
- Porting a un nuovo dispositivo: <https://wiki.postmarketos.org/wiki/Porting_to_a_new_device>
- Elenco dispositivi: <https://wiki.postmarketos.org/wiki/Devices>
- Mainlining: <https://wiki.postmarketos.org/wiki/Mainlining>
- pmaports: <https://gitlab.postmarketos.org/postmarketOS/pmaports>
- pmbootstrap: <https://gitlab.postmarketos.org/postmarketOS/pmbootstrap>
- Chat (Matrix/IRC): <https://wiki.postmarketos.org/wiki/Matrix_and_IRC>
