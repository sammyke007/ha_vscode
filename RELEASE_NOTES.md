# Release notes

These descriptions are provided for GitHub releases. An entry here does not mean
that its release has been published.

## v0.2.1 – English documentation and interface

- Translate the README and installation guide into English.
- Use English for integration-specific setup, settings, and error messages.
- Update the HACS information page and contribution instructions.
- Provide English descriptions for current and previous releases.

Tunnel behavior and configuration are unchanged. Standard Home Assistant controls
still follow the user's Home Assistant language preference.

Installation: update through HACS and restart Home Assistant. For manual upgrades,
remove the obsolete `translations/nl.json` file.

## v0.2.0 – Improved authentication and tunnel management

- Handle delayed GitHub authorization and tunnel startup.
- Change the wait time without interrupting an active tunnel.
- Prevent competing tunnel and authentication processes.
- Clean up authentication checks on cancellation, shutdown, and session expiry.
- Provide clearer status and, in this release, Dutch and English interfaces.
- Adapt HACS validation to a custom repository.

Validation: 26 regression tests with Home Assistant 2026.8.3. HACS validation,
hassfest, and regression tests passed. Full live HAOS operation and HA 2026.9
compatibility were not verified by these checks.

Installation: update through HACS and restart Home Assistant.

## v0.1.53 – HA VSCode Tunnel

- Fix the deprecated OptionsFlow config_entry assignment.
- Improve tunnel status reporting and process cleanup.
- Keep delayed GitHub sign-in sessions open for another check.
- Clarify the timeout setting.

Validation: 13 regression tests with Home Assistant 2026.8.3. These tests did not
cover a full live tunnel session or HA 2026.9 compatibility.

Installation: update through HACS and restart Home Assistant.
