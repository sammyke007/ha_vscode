# Installation, upgrades, and rollback

For a new installation, follow the [README](README.md#installation).

## Updating an existing installation

1. Create a full Home Assistant backup.
2. Close any authentication forms and turn off the tunnel switch.
3. Download the release from `sammyke007/ha_vscode` through HACS.
4. Restart Home Assistant. Your existing entry, path, URL, and wait time remain usable.
5. Turn on the switch and inspect the entity's `tunnel_status` attribute.
6. If the status is `auth_required`, turn off the switch, open **Configure**, and
   select **Check authentication / sign in again**. Authorize the new code on GitHub.
7. After a successful check, turn the switch on again.

There is no new config-entry version or required data migration in 0.2.x.
New options do not contain a temporary device code. Changing only the wait time
does not interrupt the tunnel.

## Manual installation

Copy the files from `custom_components/ha_vscode` to
`/config/custom_components/ha_vscode`. Preserve any existing `bin` directory and
stored CLI credentials. For the English-only interface in 0.2.1, remove the old
`translations/nl.json` file if your copy operation leaves obsolete files behind.
Restart Home Assistant. A missing CLI is downloaded again on startup; this does
not restore deleted credentials.

## Rollback

Turn off the switch and close authentication forms. Download the previous release
through HACS or restore the component files from your backup, then restart Home
Assistant. To restore the complete configuration, use your full backup.

## Running tests

Run these commands in a separate development environment, not inside HA Core:

```sh
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests
```

## Live checks

On your installation, check initial authorization, delayed authorization,
cancellation, switching on and off, restarting, and signing in again. Also verify
that the tunnel is actually accessible through vscode.dev. When reporting a
problem, share the error category and exit code, never device codes or tokens.
