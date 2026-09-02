# Installatie en terugzetten

## Bestaande installatie bijwerken naar 0.2.0

1. Maak een volledige Home Assistant-back-up.
2. Sluit eventuele aanmeldformulieren en zet de tunnelswitch uit.
3. Download de versie via HACS uit `sammyke007/ha_vscode`.
4. Herstart Home Assistant. Je bestaande entry, pad, URL en wachttijd blijven bruikbaar.
5. Zet de switch aan. Bekijk `tunnel_status` bij de entiteit.
6. Bij `auth_required`: zet de switch uit, open Configureren en kies
   Aanmelding controleren / opnieuw aanmelden. Autoriseer de nieuwe code op GitHub.
7. Zet na succesvolle controle de switch opnieuw aan.

Er is geen nieuwe config-entry-versie of verplichte datamigratie. De nieuwe
opties bevatten geen tijdelijke devicecode. Alleen de wachttijd wijzigen
onderbreekt de tunnel niet meer.

## Handmatige installatie

Kopieer de bestanden uit `custom_components/ha_vscode` naar
`/config/custom_components/ha_vscode`. Behoud een bestaande `bin`-map en
opgeslagen CLI-aanmeldgegevens. Herstart HA. Een ontbrekende CLI wordt bij
starten opnieuw gedownload; dit garandeert niet dat verwijderde aanmeldgegevens
hersteld kunnen worden.

## Terugzetten

Zet de switch uit en sluit aanmeldformulieren. Download de vorige release via
HACS of herstel de componentbestanden uit je back-up; herstart daarna HA.
Als de hele configuratie moet worden teruggezet, gebruik je volledige back-up.

## Tests uitvoeren

Voer dit uit in een aparte ontwikkelomgeving, niet in HA Core:

```sh
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests
```

## Praktijkcontrole

Controleer op jouw installatie: eerste autorisatie, trage autorisatie,
annuleren, in- en uitschakelen, herstarten en opnieuw aanmelden. Controleer ook
of de tunnel via vscode.dev daadwerkelijk toegankelijk is. Deel bij problemen
alleen de foutcategorie en exitcode; geen devicecodes of tokens.
