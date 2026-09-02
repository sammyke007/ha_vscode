# Contributing

Please write documentation, code comments, user-facing messages, pull requests,
and release notes in English.

## Proposing a change

1. Fork the repository and create a branch from `main`.
2. Make your changes and update the relevant documentation.
3. Run the regression tests and Ruff checks described in
   [INSTALLATION.md](INSTALLATION.md#running-tests).
4. Add regression coverage when fixing behavior that could break again.
5. Open a pull request describing the problem, the resulting behavior, and validation.

## Reporting a problem

If Issues are enabled, open an issue with the integration version from
`custom_components/ha_vscode/manifest.json`, your Home Assistant version, steps to
reproduce, expected behavior, and actual behavior. Include relevant error
categories and exit codes. Do not include authorization codes or tokens.

Issues are optional for this custom repository. If they are unavailable, use the
support channel through which you received the integration.

## Validation

The automated workflows run regression tests, Ruff, hassfest, and HACS validation.
The HACS checks for Issues and topics are intentionally skipped. Tests simulate
GitHub authorization and Microsoft downloads; report live testing separately.

The inherited label and release-draft workflows are optional and manual.

## License

By contributing, you agree that your contributions are distributed under the
repository's [MIT license](LICENSE).
