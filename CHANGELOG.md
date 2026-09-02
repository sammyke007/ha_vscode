# Changelog

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
