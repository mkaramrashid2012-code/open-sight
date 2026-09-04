# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in OpenSight Private, please email **security@opensight.local** or contact the maintainer directly at **mkaramrashid2012@gmail.com**.

**Please do not open a public issue for security vulnerabilities.**

### What to Include

When reporting a security issue, please provide:

1. **Description** - What is the vulnerability?
2. **Location** - Which file(s) and line(s) are affected?
3. **Impact** - What could an attacker do with this?
4. **Reproduction** - Steps to reproduce the vulnerability
5. **Suggested Fix** - How would you fix it? (optional)

## Security Best Practices

### For Users

1. **Keep it Updated** - Always use the latest version
2. **Secure Credentials** - Never hardcode passwords or API keys
3. **Use .env Files** - Store secrets in `.env` (excluded from git)
4. **Network Security** - Don't expose your instance publicly without proper authentication
5. **Regular Backups** - Backup your database and recordings regularly
6. **Audit Logs** - Review audit logs for suspicious activity
7. **Strong Passwords** - Use strong, unique passwords for all accounts

### For Developers

1. **Input Validation** - Always validate user input
2. **SQL Injection** - Use parameterized queries, never raw SQL
3. **Authentication** - Implement proper authentication and authorization
4. **Encryption** - Encrypt sensitive data in transit and at rest
5. **Dependencies** - Keep dependencies updated; check for vulnerabilities
6. **Secrets Management** - Never commit secrets; use environment variables
7. **Code Review** - All PRs should be reviewed before merging
8. **Testing** - Write tests, especially for security-critical code

## Privacy Guarantees

- ✅ **100% Local Processing** - No data leaves your machine
- ✅ **No Telemetry** - We don't collect usage data
- ✅ **No Cloud Dependencies** - Fully air-gap capable
- ✅ **Privacy by Default** - Sensitive features disabled by default

## License

OpenSight Private is licensed under AGPL-3.0. See [LICENSE](LICENSE) for details.

## Security Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities. Acknowledged contributors will be mentioned in our [SECURITY_CREDITS.md](SECURITY_CREDITS.md) (coming soon).
