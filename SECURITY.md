# Security Policy

## Reporting a Vulnerability

Please do not open public issues for security vulnerabilities.

Report security concerns privately to the project maintainer through your hosting platform's private channel (for example, private security advisory or direct maintainer contact).

When reporting, include:

- affected version or commit
- reproduction steps
- expected vs actual behavior
- impact assessment

## Response Expectations

- Initial acknowledgment target: within 7 days
- Triage/update target: within 14 days

## Scope

This project is local-first and does not run a hosted backend. Security-sensitive areas include:

- local data handling (`~/.worklog/` paths)
- launch agent install/uninstall behavior
- packaging and distribution artifacts
