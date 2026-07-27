# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest (main) | ✅ |

## Reporting a Vulnerability

Please **do not** report security vulnerabilities via public GitHub Issues.

Instead, open a [GitHub Security Advisory](../../security/advisories/new) or email the maintainers directly via the contact listed on their GitHub profiles.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You can expect an acknowledgment within 48 hours and a resolution timeline within 14 days for confirmed issues.

## Security Best Practices for Users

- Never commit real credentials to this repo — use environment variables or Anypoint Secure Properties
- Rotate your Slack bot token, Azure OpenAI key, and Anypoint credentials before sharing deployments
- Review all `config.properties` files before deploying to ensure no secrets are hardcoded
