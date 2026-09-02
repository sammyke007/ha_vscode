# Home Assistant VSCode Tunnel

Herstelversie 0.1.52 van [adechant/ha_vscode](https://github.com/adechant/ha_vscode).
Deze integratie start een VS Code Remote Tunnel vanuit Home Assistant, met een
switch om de verbinding aan en uit te zetten.

## Status

Dertien regressietests slagen met Home Assistant 2026.8.3 en Python 3.14.6.
De tests gebruiken echte Home Assistant-klassen, lokale testprocessen en
nagebootste download- en authenticatieantwoorden. Een echte verbinding op HAOS
en Home Assistant 2026.9 zijn nog niet gevalideerd.

## Installatie via HACS

Gebruik de repository `sammyke007/ha_vscode`:

1. Open HACS → menu → Aangepaste repositories.
2. Voeg `https://github.com/sammyke007/ha_vscode` toe, categorie **Integratie**.
3. Installeer Home Assistant VSCode Tunnel en herstart Home Assistant.
4. Voeg de integratie toe via Instellingen → Apparaten & diensten.
5. Volg de GitHub-device-login en zet daarna de tunnelswitch aan.
6. Open https://vscode.dev en selecteer de tunnel.

Gebruik niet tegelijk de oorspronkelijke repository en deze fork in HACS voor
het beheren van dezelfde componentmap. Maak bij overstappen eerst een back-up.

## Bestaande installatie en handmatige installatie

Zie [INSTALLATIE-NL.md](INSTALLATIE-NL.md) voor het behouden van de bestaande
`bin`-map, installatie, controle, terugzetten en reproduceerbare tests.

## Wijzigingen

- Home Assistant beheert de OptionsFlow-config-entry.
- Opties vallen terug op bestaande entry-data en worden door de switch gebruikt.
- Downloads en procesbeheer draaien buiten de eventloop.
- De proceslezer stopt op EOF; stoppen ruimt de eigen procesgroep op.
- De switch rapporteert de processtatus en stopt bij unload en HA-afsluiting.
- CLI-download met TLS-controle en beperkte extractie.
- Geen login-codes of geforceerde debuglogging in de logs.

Een wijziging van opties herlaadt de integratie; zet de switch daarna weer aan.
Bestaande CLI-bestanden worden behouden en niet automatisch bijgewerkt.

## Herkomst en licentie

Gebaseerd op upstream-commit `664bde4d4bfaf2d661873a5a1a7c6d80a2aadb25`.
Oorspronkelijke auteur: adechant. De oorspronkelijke MIT-licentie blijft behouden.
Zie [LICENSE](LICENSE).

## Fix in 0.1.52

Een ontbrekende tunnel-URL na de wachttijd breekt een nog actief aanmeldproces
niet meer af. Bevestig GitHub-autorisatie, wacht 15 seconden en dien het
formulier opnieuw in. Dit geldt ook voor herauthenticatie. Een gestopt
CLI-proces krijgt een afzonderlijke melding. Dit is geen bewijs dat alle
mogelijke oorzaken van aanmeldproblemen zijn opgelost.
