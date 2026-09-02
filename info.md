# Home Assistant VSCode Tunnel

Run a Microsoft VS Code Remote Tunnel from Home Assistant and control it with a
switch. Authentication uses a GitHub device code.

This fork is available as a custom HACS repository:
`https://github.com/sammyke007/ha_vscode`.

## Getting started

1. Download the integration through HACS and restart Home Assistant.
2. Open **Settings → Devices & services → Add integration** and search for
   **Home Assistant VSCode Tunnel**.
3. Follow the setup form and authorize the displayed code on GitHub.
4. After setup, turn on the tunnel switch.
5. Open [vscode.dev](https://vscode.dev) and select your tunnel.

The wait time applies to each authentication check, not the lifetime of the
tunnel. Changing only this setting does not interrupt a running tunnel.

See the [README](https://github.com/sammyke007/ha_vscode#readme) for settings,
status attributes, and troubleshooting, and the
[installation guide](https://github.com/sammyke007/ha_vscode/blob/main/INSTALLATION.md)
for upgrades and rollback.

## Credits

Originally created by [adechant](https://github.com/adechant/ha_vscode), using the
[Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component)
and [integration blueprint](https://github.com/custom-components/integration_blueprint)
templates. Distributed under the [MIT license](LICENSE).
