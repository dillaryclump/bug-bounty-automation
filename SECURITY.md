# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please send an email with details to the maintainers. You can also open a private security advisory on GitHub.

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond as quickly as possible and keep you updated on the progress.

## Security Best Practices

When deploying AutoBug:

1. **Never commit `.env` files** with real credentials
2. **Use strong passwords** for database and API authentication
3. **Rotate API tokens** regularly
4. **Enable HTTPS** in production environments
5. **Keep dependencies updated** - run `pip install -U -r requirements.txt` regularly
6. **Restrict database access** to trusted IPs only
7. **Use environment variables** for all sensitive configuration
8. **Enable rate limiting** on API endpoints
9. **Audit scan results** before reporting to bug bounty platforms
10. **Run with minimal privileges** - don't use root/admin unless necessary

## Known Security Considerations

- This tool performs active reconnaissance and vulnerability scanning. Ensure you have proper authorization before scanning any targets.
- API tokens and webhook URLs are sensitive. Store them securely in environment variables.
- The database may contain sensitive information about discovered vulnerabilities. Secure it appropriately.
- Scanning tools like Nuclei can trigger security systems. Use responsibly and within scope.

## Responsible Disclosure

We follow responsible disclosure practices:

- Report vulnerabilities privately first
- Allow reasonable time for fixes before public disclosure
- Credit security researchers who report issues responsibly
