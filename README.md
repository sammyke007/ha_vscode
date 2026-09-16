# Home Assistant VSCode Tunnel

Run a Microsoft VS Code Remote Tunnel from Home Assistant and control it with a
switch. Sign in using a GitHub device code.

This is a maintained fork of [adechant/ha_vscode](https://github.com/adechant/ha_vscode).
See [releases](https://github.com/sammyke007/ha_vscode/releases) for published versions
and [CHANGELOG.md](CHANGELOG.md) for changes, including unreleased work.

## Installation

1. Create a Home Assistant backup.
2. Add `https://github.com/sammyke007/ha_vscode` to HACS as a custom repository,
   using the **Integration** category.
3. Download the integration and restart Home Assistant.
4. Add Home Assistant VSCode Tunnel under **Settings → Devices & services**.
5. Choose the wait time per check. The Microsoft CLI is downloaded if needed.
6. Authorize the displayed code on GitHub, then submit the form.
   A delayed response does not close the session: check again when prompted.
7. After successful setup, the switch is off. Turn it on and open
   [vscode.dev](https://vscode.dev) to select your tunnel.

Use one HACS repository to manage the component directory. When switching from
upstream, preserve your existing configuration and CLI files. You do not need to
remove the integration entry. See [INSTALLATION.md](INSTALLATION.md).

## Settings and authentication

Opening settings does **not** start a process or check the connection.
Saving only the wait time does not reload the integration or interrupt the tunnel.

To check authentication explicitly, turn off the switch, open **Configure**, select
**Check authentication / sign in again**, and submit the form. This check reserves
the same CLI used by the switch, preventing a second process from starting.
The check stops after success or cancellation. An abandoned authentication session
is cleaned up after ten minutes or when Home Assistant shuts down. Reloading the
integration during a check may cause that check to fail; close the form and retry.

The wait time is 1–120 seconds **per check**, with a default of 7 seconds for new
installations. Existing values are preserved. There is no separate hardcoded
initial wait. This setting does not limit how long the tunnel can run.
Integration-specific forms and messages are in English. Standard Home Assistant
buttons and navigation follow your Home Assistant language preference.

## Status and troubleshooting

The switch is on while the CLI process is running. This does not prove that a
remote connection works. Check the entity attributes as well:

| Attribute | Meaning |
| --- | --- |
| `tunnel_status` | `starting`, `auth_required`, `ready`, or `stopped` |
| `tunnel_url` | Tunnel URL opening the Home Assistant `/config` workspace, available only when `ready` |
| `last_error_category` | Recognized error category, if available |
| `last_exit_code` | Exit code from the most recently stopped CLI process |
| `configuration_in_progress` | An authentication check has reserved the process |

`ready` means the CLI reported a URL; it is not a continuous network health check. The integration appends `/config` so the entity link opens the Home Assistant configuration workspace instead of the container root.
Attributes follow Home Assistant's normal polling cycle.

Unexpected process exits are logged with the exit code when the output reader
observes the exit. Recognized messages are categorized as authentication, network,
TLS, or platform errors. Unrecognized errors may remain `unknown`. Raw CLI output,
authorization codes, and tokens are not logged. New device codes are not stored in
config entries; existing entry data remains compatible.

When authentication is required, Home Assistant creates a persistent notification
with the steps needed to sign in again. The notification has a fixed ID, so repeated
checks update the same notification instead of creating duplicates. It is dismissed
automatically after the tunnel becomes ready.

After a successful authentication check, the preceding CLI process may briefly
remain registered by the remote service. If the first normal start then exits with
code 1, the integration waits three seconds and retries once. Other starts and exit
codes are never retried automatically.

## Process and download management

- Downloads, file access, and process startup/shutdown run outside the HA event loop.
- The output reader stops at EOF. Shutdown uses bounded waits and terminates the
  integration's own Linux process group, including ordinary child processes.
- A missing CLI is installed again on the next start.
- Downloads verify TLS. Only the expected executable is extracted from the
  archive, with limits on file size.
- An existing CLI is preserved. Automatic CLI updates are not included.
- The CLI starts with `--accept-server-license-terms`, as in upstream.
- CLI authentication metadata, VS Code server data, and remote extensions are
  stored persistently under `/config/.ha_vscode` with owner-only permissions.
- The tunnel reuses its configured name instead of requesting a random name.
- After a Home Assistant restart or integration reload, the switch stays off.
  Automatic restoration of its previous on-state is not enabled.

After upgrading from a release before 0.2.3, perform GitHub authentication one
final time when requested. Install remote extensions such as Home Assistant Config
Helper, YAML, or Color Lens once under **Homeassistant – Installed**. They are then
stored in `/config/.ha_vscode/extensions` and remain available across tunnel and
Home Assistant restarts. Existing extensions from the former container-local
location are not copied automatically.

## Validation

See [CHANGELOG.md](CHANGELOG.md) and the regression test workflow. Tests use real
Home Assistant flow classes, simulated authentication/downloads, and local
subprocesses. They do not establish full compatibility with every HAOS installation
or the live Microsoft/GitHub services.

## Custom repository checks

This fork is distributed as a custom HACS repository. The HACS workflow skips only
the optional Issues and topics checks. Other HACS checks, Home Assistant validation,
and regression tests remain enabled.

The inherited label and release-draft workflows run manually only. They require
separate write permissions if you choose to use them. Releases can be published
through GitHub. See [RELEASE_NOTES.md](RELEASE_NOTES.md) for release descriptions.

## Credits and license

Based on upstream commit `664bde4d4bfaf2d661873a5a1a7c6d80a2aadb25`.
Original author: adechant. The original [MIT license](LICENSE) is preserved.
