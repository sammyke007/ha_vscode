# HA VSCode Tunnel – herstelversie 0.1.53

Dit is een aangepaste testversie op basis van adechant/ha_vscode, commit
664bde4d4bfaf2d661873a5a1a7c6d80a2aadb25. Geen officiële upstream-release.

## Validatie

13 gerichte regressietests geslaagd met de echte Home Assistant 2026.8.3
Python-klassen en Python 3.14.6. Tests gebruiken lokale testprocessen en
nagebootste download/authenticatie-antwoorden. Ook Python-syntax en Ruff gecontroleerd.
Home Assistant 2026.9.0 was op 2 september 2026 niet beschikbaar via de gebruikte
pakketbron. Een volledige HAOS-installatie, echte CLI-download, GitHub-device-login
en externe VS Code-verbinding zijn hier niet getest. Compatibiliteit met 2026.9
is dus nog niet bewezen.

## Wat is hersteld?

- OptionsFlow laat Home Assistant `config_entry` beheren en leest die pas in de flow.
- Opties vallen terug op bestaande config-entry-data; de switch gebruikt opties ook.
- Wijzigen van opties herlaadt de integratie. De switch staat daarna uit.
- Downloads, bestandstoegang en procesbeheer draaien buiten de HA-eventloop.
- De stdout-lezer eindigt op EOF; geen eindeloze leeslus na procesexit.
- Stoppen heeft tijdslimieten en ruimt de eigen Linux-procesgroep op.
- De status kijkt naar de echte processtatus. Opnieuw inschakelen start geen dubbel proces.
- De tunnel stopt bij verwijderen/herladen van de integratie en bij HA-afsluiting.
- Download met TLS-controle; alleen het verwachte uitvoerbare bestand wordt uitgepakt.
- Geen geforceerde debuglogging of login-codes in logs.
- Bestaande CLI wordt behouden. Deze versie regelt geen automatische CLI-updates.

Dit bewijst niet dat jouw eerdere CPU-probleem door deze integratie kwam.

## Handmatig installeren op je bestaande installatie

1. Maak een Home Assistant-back-up en bewaar een kopie van
   `/config/custom_components/ha_vscode` buiten `custom_components`.
2. Zet de bestaande VS Code-tunnelswitch uit. Gebruik een andere editor of
   bestandsverbinding voor het vervangen van de bestanden.
3. Pak dit archief uit op je computer.
4. Kopieer de inhoud van `custom_components/ha_vscode` over de bestanden in
   `/config/custom_components/ha_vscode`. **Behoud de bestaande map `bin`** en
   verwijder geen configuratie of opgeslagen aanmeldgegevens.
5. Herstart Home Assistant. Je bestaande integratie hoeft niet verwijderd te worden.
6. Open Instellingen → Apparaten & diensten → Home Assistant VSCode Tunnel →
   Configureren. Controleer dat de oude `config_entry`-fout niet terugkomt.
7. Doorloop eventueel de GitHub-device-login die het formulier aangeeft.
8. Zet de tunnelswitch aan. Open de tunnel via https://vscode.dev en controleer
   dat je je configuratiebestanden kunt openen.
9. Zet de switch uit en controleer dat de verbinding stopt. Test ook herladen.

Voor een nieuwe installatie: kopieer dezelfde map naar `custom_components`,
herstart HA en voeg Home Assistant VSCode Tunnel toe via Apparaten & diensten.
Nieuwe installatie downloadt de Microsoft CLI. De CLI wordt gestart met dezelfde
licentieacceptatie-optie als upstream.

Een HACS-update van de oorspronkelijke repository kan deze wijzigingen overschrijven.
Bewaar dit pakket totdat een eigen fork of upstream-oplossing beschikbaar is.

## Via een eigen HACS-repository

De herstelversie staat in `https://github.com/sammyke007/ha_vscode`.
Voeg deze URL in HACS toe als Aangepaste repository, categorie Integratie.
Laat niet tegelijk twee HACS-repositories dezelfde integratiemap beheren.
Maak bij overstappen een back-up en behoud de bestaande `bin`-map en configuratie.

## Terugzetten

Zet de switch uit. Zet de eerder bewaarde componentbestanden terug en herstart HA.
Deze herstelversie migreert de config-entry niet naar een ander formaat.
Het toevoegen van een unique_id maakt de switch beheerbaar in het entiteitenregister;
controleer na installatie dat dashboards en automatisaties de juiste entiteit gebruiken.

## Reproduceerbare tests

Vanuit de repositorymap, in een aparte ontwikkelomgeving (niet in HA Core):

```sh
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python homeassistant==2026.8.3 pytest==9.1.1 pytest-asyncio==1.4.0 ruff==0.16.5
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests
```

## Referenties

- https://developers.home-assistant.io/blog/2024/11/12/options-flow/
- https://developers.home-assistant.io/docs/asyncio_blocking_operations/
- https://github.com/adechant/ha_vscode
