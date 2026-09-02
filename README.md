# Home Assistant VSCode Tunnel

Versie **0.2.0** van de fork van [adechant/ha_vscode](https://github.com/adechant/ha_vscode).
Start een Microsoft VS Code Remote Tunnel vanuit Home Assistant en bedien het
proces met een switch. Aanmelden gebeurt via de GitHub-devicecode.

## Installatie

1. Maak een Home Assistant-back-up.
2. Voeg `https://github.com/sammyke007/ha_vscode` in HACS toe als aangepaste
   repository, categorie **Integratie**.
3. Download en herstart Home Assistant.
4. Voeg Home Assistant VSCode Tunnel toe via Instellingen → Apparaten & diensten.
5. Kies de wachttijd per controle. De CLI wordt zo nodig gedownload.
6. Autoriseer de getoonde code op GitHub. Klik vervolgens op Verzenden.
   Een laat antwoord sluit de sessie niet: controleer opnieuw als daarom wordt gevraagd.
7. Na de succesvolle controle staat de switch uit. Zet hem aan en open
   [vscode.dev](https://vscode.dev) om de tunnel te selecteren.

Gebruik één HACS-repository om de componentmap te beheren. Als je overstapt van
upstream: bewaar je bestaande configuratie en CLI-bestanden. Verwijder niet
onnodig de integratie-entry. Zie [INSTALLATIE-NL.md](INSTALLATIE-NL.md).

## Instellingen en aanmelden

Instellingen openen start **geen** proces en controleert de verbinding niet.
Alleen de wachttijd opslaan herlaadt de integratie niet en onderbreekt de tunnel niet.

Voor een expliciete controle: zet de switch uit, open Configureren, vink
**Aanmelding controleren / opnieuw aanmelden** aan en verstuur het formulier.
Deze controle reserveert dezelfde CLI als de switch. De switch kan tijdens de
controle geen tweede proces starten. Na succes of annuleren stopt de controle.
Een verlaten aanmeldsessie wordt na tien minuten opgeruimd; ook HA-afsluiting
ruimt haar op. Handmatig herladen van de integratie tijdens een controle kan die
controle laten mislukken; sluit het formulier en probeer opnieuw.

De wachttijd is 1–120 seconden **per controle**. Bij nieuwe installatie is de
standaard 7 seconden. Bestaande waarden worden behouden. Er is geen afzonderlijke
hardgecodeerde eerste wachtperiode meer. De wachttijd is geen maximale looptijd
van de tunnel. Dit is ook in de Nederlandse en Engelse interface uitgelegd.

## Status en foutdiagnose

De switch is aan zolang het CLI-proces draait. Dat bewijst niet dat een externe
verbinding werkt. Bekijk daarom ook de attributen:

| Attribuut | Betekenis |
| --- | --- |
| `tunnel_status` | `starting`, `auth_required`, `ready` of `stopped` |
| `tunnel_url` | URL uit het huidige proces, alleen bij `ready` |
| `last_error_category` | Herkende foutcategorie, indien beschikbaar |
| `configuration_in_progress` | Een aanmeldcontrole heeft het proces gereserveerd |

`ready` betekent dat de CLI een URL heeft gemeld, niet dat er permanent een
netwerk-healthcheck loopt. De attributen volgen de normale HA-pollingcyclus.

Een onverwachte procesexit wordt met exitcode gelogd wanneer de outputlezer de
exit waarneemt. Bekende meldingen worden ingedeeld als authenticatie-, netwerk-,
TLS- of platformfout. Onbekende fouten kunnen `unknown` blijven. Ruwe CLI-output,
aanmeldcodes en tokens worden niet gelogd. Nieuwe devicecodes worden niet in
config-entries opgeslagen; bestaande oude entry-data blijven compatibel.

## Proces- en downloadbeheer

- Downloads, bestandstoegang en starten/stoppen draaien buiten de HA-eventloop.
- De lezer eindigt op EOF; stoppen heeft begrensde wachttijden en beëindigt de
  eigen Linux-procesgroep, inclusief normale onderliggende processen.
- Een ontbrekende CLI wordt bij een volgende start opnieuw geïnstalleerd.
- Downloads gebruiken TLS-controle. Alleen het verwachte uitvoerbare bestand
  wordt uit het archief overgenomen, met limieten op de bestandsgrootte.
- Een bestaande CLI wordt behouden; automatische CLI-updates zijn niet inbegrepen.
- De CLI start met `--accept-server-license-terms`, zoals in upstream.
- Na HA-herstart of herladen blijft de switch uit. Automatisch herstellen van de
  vorige aan-stand is niet ingeschakeld.

## Validatie en grenzen

Zie [CHANGELOG.md](CHANGELOG.md) en de testworkflow. De tests gebruiken echte
Home Assistant-flowklassen, nagebootste authenticatie/downloads en lokale
subprocessen. Ze bewijzen geen volledige werking op jouw HAOS-installatie of
tegen de live Microsoft/GitHub-diensten. Er is geen claim dat de code foutloos is.

## Herkomst

Gebaseerd op upstream-commit `664bde4d4bfaf2d661873a5a1a7c6d80a2aadb25`.
Oorspronkelijke auteur: adechant. De oorspronkelijke [MIT-licentie](LICENSE)
blijft behouden.
