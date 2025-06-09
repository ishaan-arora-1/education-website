# Education Website - Ansible Deployment

This directory contains the complete Ansible-based deployment system for the Education Website, replacing the original `setup.sh` script with a more robust, maintainable, and scalable infrastructure-as-code approach.

## 🚀 Quick Start

### Prerequisites
- Ansible 2.9+ installed on your local machine
- SSH access to your target servers
- Python 3.11+ on target servers

### Basic Deployment
```bash
# Full production deployment
./scripts/deploy.sh

# Quick update only
./scripts/deploy.sh -u

# Deploy to staging environment
./scripts/deploy.sh -e staging

# Dry run to see what would change
./scripts/deploy.sh -c
```

## 📁 Directory Structure

```
ansible/
├── deploy.yml              # Main deployment playbook
├── update.yml              # Quick update playbook
├── ansible.cfg             # Ansible configuration
├── inventory/
│   └── hosts.yml          # Server inventory (all environments)
├── group_vars/
│   └── all/
│       ├── main.yml       # Main configuration variables
│       └── vault.yml      # Encrypted secrets (create this)
├── roles/                 # Ansible roles
│   ├── common/           # System setup, users, directories
│   ├── security/         # Firewall, fail2ban, SSH hardening
│   ├── postgresql/       # Database setup and backups
│   ├── python/           # Python environment setup
│   ├── django/           # Django application deployment
│   ├── nginx/            # Web server configuration
│   ├── ssl/              # SSL certificate management
│   └── systemd/          # Service management
└── scripts/
    ├── deploy.sh         # Main deployment script
    └── local_setup.sh    # Local development setup
```

## 🔧 Configuration

### 1. Server Inventory
Edit `inventory/hosts.yml` to define your servers:

```yaml
all:
  children:
    production:
      hosts:
        prod-server:
          ansible_host: your-server-ip
          ansible_user: your-username
    staging:
      hosts:
        staging-server:
          ansible_host: staging-ip
          ansible_user: your-username
```

### 2. Encrypted Secrets
Create and encrypt `group_vars/all/vault.yml`:

```bash
ansible-vault create group_vars/all/vault.yml
```

Add your secrets:
```yaml
# Database
vault_db_password: "your-secure-db-password"

# Django
vault_secret_key: "your-django-secret-key"
vault_debug: false

# Domain and SSL
vault_domain_name: "yourdomain.com"

# API Keys
vault_stripe_secret_key: "sk_live_..."
vault_stripe_publishable_key: "pk_live_..."
vault_stripe_webhook_secret: "whsec_..."
vault_sendgrid_password: "your-sendgrid-password"

# Notifications
vault_slack_webhook_url: "https://hooks.slack.com/..."
```

### 3. Environment Variables
Customize `group_vars/all/main.yml` for your needs:

```yaml
# Project settings
project_name: "education-website"
domain_name: "{{ vault_domain_name }}"
app_port: 8000

# Python settings
python_version: "3.11"
gunicorn_workers: 4

# Security
enable_https_redirect: true
```

## 🎯 Deployment Options

### Full Deployment
Deploys everything from scratch:
```bash
./scripts/deploy.sh -e production
```

### Quick Updates
For code updates without full infrastructure changes:
```bash
./scripts/deploy.sh -u
```

### Targeted Deployment
Deploy specific components:
```bash
./scripts/deploy.sh -t django,nginx    # Only Django and Nginx
./scripts/deploy.sh -t ssl             # Only SSL certificates
```

### Environment-Specific
```bash
./scripts/deploy.sh -e staging         # Deploy to staging
./scripts/deploy.sh -e development     # Deploy to development
```

### Dry Run
See what would change without making changes:
```bash
./scripts/deploy.sh -c
```

## 🔄 Migration from setup.sh

This Ansible system replaces all functionality from the original `setup.sh`:

| setup.sh Feature | Ansible Equivalent |
|------------------|-------------------|
| System package installation | `common` role |
| PostgreSQL setup | `postgresql` role |
| Python environment | `python` role |
| Django deployment | `django` role |
| Nginx configuration | `nginx` role |
| SSL certificates | `ssl` role |
| Systemd service | `systemd` role |
| Firewall (UFW) | `security` role |
| Fail2ban | `security` role |
| Git webhooks | `django` role |
| Local development | `scripts/local_setup.sh` |

### Key Improvements
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Multi-environment**: Production, staging, development
- ✅ **Encrypted secrets**: Ansible Vault for sensitive data
- ✅ **Modular**: Separate roles for different components
- ✅ **Rollback capable**: Easy to revert changes
- ✅ **Dry run support**: Test before applying
- ✅ **Comprehensive logging**: Better error tracking

## 🛠️ Local Development

For local development setup (replaces `./setup.sh` without arguments):

```bash
./scripts/local_setup.sh              # Standard local setup
./scripts/local_setup.sh -r           # Reset git and update
./scripts/local_setup.sh -f           # Force requirements reinstall
```

## 🔐 Security Features

- **Firewall Configuration**: UFW with minimal required ports
- **Fail2ban**: Protection against brute force attacks
- **SSL/TLS**: Automatic Let's Encrypt certificates
- **Security Headers**: HSTS, XSS protection, etc.
- **Service Isolation**: Proper user permissions and systemd security
- **Encrypted Secrets**: All sensitive data encrypted with Ansible Vault

## 📊 Monitoring & Maintenance

### Database Backups
Automatic PostgreSQL backups are configured:
- Daily backups with 7-day retention
- Stored in `/home/user/backups/`
- Automated cleanup of old backups

### Log Management
- Application logs in `/var/log/education-website/`
- Nginx logs with logrotate
- Systemd service logs via journalctl

### Service Management
```bash
# Check service status
sudo systemctl status education-website

# View logs
sudo journalctl -u education-website -f

# Restart service
sudo systemctl restart education-website
```

## 🚨 Troubleshooting

### Common Issues

1. **Vault Password**: If you get vault errors, ensure you have the correct vault password
2. **SSH Access**: Verify SSH key authentication is working
3. **Domain DNS**: Ensure your domain points to the server before SSL setup
4. **Firewall**: Check UFW status if having connectivity issues

### Debug Mode
Run with verbose output:
```bash
ansible-playbook deploy.yml -vvv
```

### Check Syntax
Validate playbooks before running:
```bash
ansible-playbook deploy.yml --syntax-check
```

## 📚 Additional Resources

- [Ansible Documentation](https://docs.ansible.com/)
- [Django Deployment Best Practices](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

## 🤝 Contributing

When adding new features:
1. Create appropriate Ansible roles
2. Update this README
3. Test in staging environment first
4. Use Ansible best practices (idempotency, proper error handling)

---

**Note**: This system completely replaces the original `setup.sh` script. The old script is kept for reference but should not be used for new deployments. 