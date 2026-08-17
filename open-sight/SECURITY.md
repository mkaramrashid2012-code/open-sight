# OpenSight Private - Enterprise Security Documentation

## Overview

OpenSight Private is designed as a **privacy-first, local-only** video analytics platform comparable to enterprise solutions like BriefCam while maintaining complete data sovereignty. All processing happens locally with no cloud dependencies.

## Security Features

### 1. Authentication & Authorization

- **API Key Authentication**: Secure API access with revocable keys
- **Token-based Sessions**: HMAC-signed tokens with expiration
- **Password Hashing**: bcrypt for secure password storage
- **Rate Limiting**: Protection against brute-force attacks
- **Role-based Access**: User and superuser privilege levels

### 2. Data Protection

- **Local Processing Only**: No data leaves your network
- **Encrypted Storage**: Database connections use PostgreSQL security
- **Audit Logging**: Complete trail of sensitive operations
- **Configurable Retention**: Automatic cleanup of old media

### 3. Network Security

- **CORS Configuration**: Strict origin policies
- **Input Validation**: Pydantic validation on all inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **API Rate Limiting**: Per-endpoint rate limits

### 4. Privacy Controls

- **Face Recognition Disabled by Default**: Opt-in only
- **License Plate Recognition Disabled by Default**: Opt-in only
- **Granular Camera Controls**: Enable/disable per camera
- **Data Minimization**: Only store necessary metadata

## Deployment Security Checklist

### Pre-Deployment

- [ ] Change default database password (`POSTGRES_PASSWORD`)
- [ ] Generate strong `SECRET_KEY` (min 32 random characters)
- [ ] Set `ENVIRONMENT=production`
- [ ] Disable `allow_anonymous` access
- [ ] Configure proper `cors_origins` for your domain
- [ ] Review and adjust `enable_audit_logging`

### Network Configuration

- [ ] Bind to specific interface (not 0.0.0.0 in production)
- [ ] Use reverse proxy (nginx/Apache) with TLS
- [ ] Restrict database access to localhost only
- [ ] Configure firewall rules for RTSP streams
- [ ] Isolate camera network from public internet

### Operational Security

- [ ] Regular security updates (dependencies, OS)
- [ ] Monitor audit logs for suspicious activity
- [ ] Rotate API keys periodically
- [ ] Backup encryption for database dumps
- [ ] Implement log rotation and retention

## Vulnerability Reporting

If you discover a security vulnerability, please report it responsibly:

1. **Do not** create public GitHub issues for security vulnerabilities
2. Email: security@opensight-private.local (configure in production)
3. Include detailed reproduction steps
4. Allow reasonable time for patching before disclosure

## Compliance Considerations

### GDPR
- Data minimization built into design
- Right to erasure supported via API
- Audit trails for data access
- Local processing avoids cross-border transfers

### Privacy by Design
- Default settings favor privacy
- Granular controls for sensitive features
- Transparent logging of all operations
- No hidden telemetry or cloud calls

## Comparison to Commercial Solutions

| Feature | OpenSight Private | BriefCam | Verint |
|---------|-------------------|----------|--------|
| Local Processing | ✅ Yes | ⚠️ Hybrid | ⚠️ Hybrid |
| Cloud Dependencies | ❌ None | ✅ Yes | ✅ Yes |
| Face Recognition | 🔒 Disabled default | ✅ Enabled | ✅ Enabled |
| Audit Logging | ✅ Built-in | ✅ Enterprise | ✅ Enterprise |
| API Access | ✅ RESTful | ✅ RESTful | ✅ SOAP/REST |
| Cost | 💰 Open Source | 💰💰💰 License | 💰💰💰 License |
| Data Sovereignty | ✅ 100% Local | ⚠️ Varies | ⚠️ Varies |

## Hardening Guide

### Production Environment Variables

```bash
# Security
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(48))">
ENVIRONMENT=production
ALLOW_ANONYMOUS=false
DEBUG=false

# Database
POSTGRES_USER=opensight_prod
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=opensight_prod

# Network
HOST=127.0.0.1  # Or specific interface
CORS_ORIGINS=["https://your-domain.com"]

# Logging
LOG_LEVEL=WARNING
ENABLE_AUDIT_LOGGING=true
```

### Docker Security

```yaml
# Use specific versions, not 'latest'
image: pgvector/pgvector:pg16

# Read-only root filesystem where possible
read_only: true

# Drop unnecessary capabilities
cap_drop:
  - ALL
cap_add:
  - CHOWN
  - SETGID
  - SETUID

# Resource limits
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

## Incident Response

### If Compromised

1. **Isolate**: Disconnect affected systems from network
2. **Rotate**: Change all credentials (database, API keys, passwords)
3. **Audit**: Review audit logs for unauthorized access
4. **Patch**: Update to latest version
5. **Restore**: From known-good backup if needed
6. **Document**: Record timeline and actions taken

## Contact

For security questions or concerns:
- Documentation: `/docs/SECURITY.md`
- Configuration: `backend/app/core/config.py`
- Authentication: `backend/app/security/auth.py`
