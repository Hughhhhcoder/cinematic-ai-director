# Security Policy

## Supported version

Security fixes are provided for the latest `1.x` release. Older schemas remain readable only to report `LEGACY_SCHEMA`; they are not silently migrated.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** private security-advisory flow. Do not open a public issue for path traversal, archive extraction, checksum bypass, secret exposure, or consent/privacy vulnerabilities.

Include the affected command, operating system, Python version, minimal reproduction, impact, and whether untrusted files are required. You should receive an acknowledgement within seven days.

## Security boundary

- Runtime commands are offline and use only the Python standard library.
- The Skill does not log in to, upload to, or spend credits on Higgsfield or another generation platform.
- Generated references may contain sensitive likeness information; keep real-person assets outside public repositories unless rights and identity consent are documented.
- Verify release `SHA256SUMS` and the installed `runtime-manifest.json` before use.
