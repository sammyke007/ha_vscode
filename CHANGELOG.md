# Changelog

## 0.2.4

- Open the tunnel URL directly in the Home Assistant `/config` workspace.
- Prevent the entity's tunnel link from opening the container root (`/`), which
  could trigger expensive full-filesystem searches in VS Code.
- Add regression coverage for tunnel URL normalization.

## 0.2.3

- Store VS Code CLI metadata, server data, and remote extensions in dedicated
  persistent directories below `/config/.ha_vscode`.
- Reuse the configured tunnel name instead of requesting a random name for each
  process start.
- Protect the runtime directories with owner-only permissions.
- Existing installations may require one final GitHub authentication after
  upgrading because credentials move to the new persistent CLI data directory.

## 0.2.2

- Create a persistent Home Assistant notification when GitHub authentication is
  required, with instructions for starting the authentication flow.
- Dismiss that notification automatically when the tunnel becomes ready.
- Retry once, after a short delay, when the first tunnel start immediately after
  successful authentication exits with code 1.
- Expose the last CLI exit code as `last_exit_code` for troubleshooting.

## 0.2.1

- Use English throughout the repository documentation and integration interface.
- Replace the Dutch installation guide with INSTALLATION.md.
- Refresh the HACS information page and contribution instructions.
- Add English GitHub release descriptions in RELEASE_NOTES.md.
- Remove the Dutch translation so Home Assistant uses the English fallback.
- No changes to tunnel behavior or configuration.

## 0.2.0

- One authentication state handler observes both devicecodes and tunnel URLs,
  including delayed responses. Unknown readiness is never reported as success.
- Settings are separate from explicit authentication checks. Saving a timeout
  does not reload the integration or disconnect a running tunnel.
- A probe reserves the shared CLI; starting another process is rejected.
- Probes stop on success, cancellation, failure, HA shutdown or ten-minute expiry.
- New setup and options both expose the same timeout setting.
- Process state is separate from URL readiness in switch attributes.
- Error categories and observed process exit codes are logged without raw CLI output.
- A missing CLI is installed again on start. Existing binaries are preserved.
- Dutch and English UI, updated installation/rollback instructions, and CI tests.

Validation: 26 local tests passed with Home Assistant 2026.8.3 / Python 3.14.6;
Ruff and Python compilation passed. Tests include real subprocesses, but
GitHub authorization and Microsoft downloads are simulated. Full live HAOS
operation and HA 2026.9 compatibility remain unverified.

## 0.1.53

Clarify the timeout label and explain its scope.

## 0.1.52

Keep pending authorization sessions alive after a URL wait timeout.

## 0.1.51

Repair the deprecated OptionsFlow assignment, process EOF handling and cleanup.
