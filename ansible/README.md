# Ansible Configuration for Education Website

This Ansible configuration has been adapted for the education-website project, supporting automated deployment and management.

## Prerequisites

1. **Ansible installed** on your local machine
2. **SSH access** to your production server
3. **Environment variables** set up (see below)

## Environment Variables

Set these environment variables before running Ansible:

```bash
export VPS_IP="your.server.ip.address"
export VPS_USER="ubuntu"  # or your server username
export VPS_PASSWORD="your_password"  # or use SSH keys
export PROJECT_NAME="education-website"
export DOMAIN_NAME="yourdomain.com"  # optional
export APP_PORT="8000"
export DB_NAME="education_website"
export DB_USER="ubuntu"  # same as VPS_USER usually
export DB_PASSWORD="your_secure_db_password"
export SECRET_KEY="your_django_secret_key"
export DEBUG="False"
export STRIPE_SECRET_KEY="your_stripe_secret"  # optional
export STRIPE_PUBLISHABLE_KEY="your_stripe_publishable"  # optional
# ... other optional variables
```

## Server Inventory

Update the `hosts` file with your server details:

```ini
[production]
192.168.1.100 ansible_user=ubuntu ansible_ssh_pass=your_password
# or use SSH keys:
# 192.168.1.100 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

## Available Playbooks

### 1. Main Deployment (`playbook.yml`)
Full server setup and application deployment:
```bash
./deploy.sh
# or
ansible-playbook -i hosts playbook.yml
```

This playbook:
- Installs system dependencies (Python 3.11, PostgreSQL, Nginx, etc.)
- Sets up firewall and security (UFW, fail2ban)
- Creates PostgreSQL database and user
- Clones the repository and sets up Python virtual environment
- Configures Nginx (HTTP/HTTPS based on settings)
- Sets up systemd service for the application
- Runs Django migrations and collects static files

### 2. Database Migration (`migrate.yml`)
Run database migrations and update code:
```bash
ansible-playbook -i hosts migrate.yml
```

### 3. Database Reset (`fix_db.yml`)
⚠️ **DESTRUCTIVE** - Drops and recreates the database:
```bash
ansible-playbook -i hosts fix_db.yml
```

### 4. Site Testing (`test_site.yml`)
Test website functionality and service status:
```bash
ansible-playbook -i hosts test_site.yml
```

### 5. Simple Test (`simple_test.yml`)
Basic connectivity and Django shell tests:
```bash
ansible-playbook -i hosts simple_test.yml
```

### 6. Server Reboot (`reboot.yml`)
Safely reboot server and verify services:
```bash
ansible-playbook -i hosts reboot.yml
```

## Configuration Templates

### Nginx Configuration
- `nginx.conf.j2` - Full HTTPS configuration with SSL
- `nginx-http.conf.j2` - HTTP-only configuration

### Systemd Service
- `education-website.service.j2` - Gunicorn with Uvicorn workers

### Environment File
- `env.j2` - Django environment configuration

### Git Webhook
- `update.sh.j2` - Automated deployment script

## Key Differences from Original

1. **Project**: gemnar-website → education-website
2. **User**: django → configurable via VPS_USER
3. **Database**: gemnar_db → education_website (configurable)
4. **Repository**: Uses AlphaOneLabs/education-website
5. **Python**: Uses virtual environment instead of Poetry
6. **Service**: Uses Gunicorn with Uvicorn workers instead of direct Uvicorn
7. **Port**: Configurable port (default 8000) instead of Unix socket
8. **Python Version**: 3.11 specifically

## Troubleshooting

### Check service status:
```bash
ansible-playbook -i hosts test_site.yml
```

### View service logs:
```bash
# On the server
sudo journalctl -u education-website -f
```

### Manual service restart:
```bash
# On the server
sudo systemctl restart education-website
```

### Database connection issues:
```bash
ansible-playbook -i hosts fix_db.yml
```

## Security Notes

- Firewall (UFW) is configured to allow only SSH, HTTP, and HTTPS
- fail2ban is set up for intrusion prevention
- PostgreSQL is configured for local connections only
- Environment variables contain sensitive information - keep them secure