#!/bin/bash
set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Default values with environment variable support
VPS_IP="${VPS_IP:-""}"
VPS_USER="${VPS_USER:-""}"
VPS_PASSWORD="${VPS_PASSWORD:-""}"
PROJECT_NAME="${PROJECT_NAME:-"education-website"}"
DOMAIN_NAME="${DOMAIN_NAME:-""}"
APP_PORT="${APP_PORT:-8000}"
PYTHON_VERSION="${PYTHON_VERSION:-"3.10"}"
DB_NAME="${DB_NAME:-${PROJECT_NAME//-/_}}"
DB_USER="${DB_USER:-${VPS_USER}}"
DB_PASSWORD="${DB_PASSWORD:-"$(openssl rand -base64 12)"}"
STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY:-""}"
STRIPE_PUBLISHABLE_KEY="${STRIPE_PUBLISHABLE_KEY:-""}"
STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-""}"
STRIPE_CONNECT_WEBHOOK_SECRET="${STRIPE_CONNECT_WEBHOOK_SECRET:-""}"
SENDGRID_PASSWORD="${SENDGRID_PASSWORD:-""}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-""}"
SECRET_KEY="${SECRET_KEY:-"$(openssl rand -base64 32)"}"
DEBUG="${DEBUG:-False}"
ENABLE_HTTPS_REDIRECT="${ENABLE_HTTPS_REDIRECT:-True}"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to ensure sshpass is installed
ensure_sshpass() {
    if ! command_exists sshpass; then
        log "sshpass is not installed. Installing it now..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y sshpass
        elif command_exists yum; then
            sudo yum install -y sshpass
        elif command_exists brew; then
            brew install hudochenkov/sshpass/sshpass
        else
            log "Error: Could not install sshpass. Please install it manually."
            exit 1
        fi
    fi
}

# Function to check if required variables are set
check_required_vars() {
    if [ -z "$VPS_IP" ] || [ -z "$VPS_USER" ] || [ -z "$VPS_PASSWORD" ]; then
        log "Error: The following environment variables must be set:"
        [ -z "$VPS_IP" ] && echo "- VPS_IP"
        [ -z "$VPS_USER" ] && echo "- VPS_USER"
        [ -z "$VPS_PASSWORD" ] && echo "- VPS_PASSWORD"
        exit 1
    fi
}

# Function to install system dependencies
install_system_dependencies() {
    echo "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3-pip python3-full nginx git certbot python3-certbot-nginx ufw fail2ban \
        postgresql postgresql-contrib python3-dev libpq-dev build-essential sshpass
}

# Function to setup PostgreSQL
setup_postgresql() {
    echo "Setting up PostgreSQL..."
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true
}

# Function to setup firewall
setup_firewall() {
    echo "Setting up firewall..."
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80
    sudo ufw allow 443
    sudo ufw --force enable
}

# Function to setup fail2ban
setup_fail2ban() {
    echo "Setting up fail2ban..."
    sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
}

# Function to setup Python environment
setup_python_env() {
    echo "Setting up Python environment..."
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --break-system-packages --upgrade pip
    pip install --break-system-packages -r requirements.txt
    pip install --break-system-packages uvicorn gunicorn psycopg2-binary
}

# Function to setup Nginx
setup_nginx() {
    echo "Setting up Nginx..."
    sudo rm -f /etc/nginx/sites-enabled/default

    # Create Nginx configuration with conditional HTTPS redirect
    if [ "$ENABLE_HTTPS_REDIRECT" = "True" ]; then
        sudo tee /etc/nginx/sites-available/$PROJECT_NAME << EEOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${DOMAIN_NAME};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

    location /static/ {
        alias /home/${VPS_USER}/${PROJECT_NAME}/staticfiles/;
    }

    location /media/ {
        alias /home/${VPS_USER}/${PROJECT_NAME}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EEOF
    else
        sudo tee /etc/nginx/sites-available/$PROJECT_NAME << EEOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location /static/ {
        alias /home/${VPS_USER}/${PROJECT_NAME}/staticfiles/;
    }

    location /media/ {
        alias /home/${VPS_USER}/${PROJECT_NAME}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EEOF
    fi

    sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
}

# Function to setup SSL
setup_ssl() {
    if [ ! -z "$DOMAIN_NAME" ]; then
        echo "Setting up SSL for $DOMAIN_NAME..."
        sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@${DOMAIN_NAME}
    fi
}

# Function to setup systemd service
setup_systemd_service() {
    echo "Setting up systemd service..."
    sudo tee /etc/systemd/system/$PROJECT_NAME.service << EEOF
[Unit]
Description=$PROJECT_NAME website
After=network.target

[Service]
User=${VPS_USER}
Group=${VPS_USER}
WorkingDirectory=/home/${VPS_USER}/${PROJECT_NAME}
Environment="PATH=/home/${VPS_USER}/${PROJECT_NAME}/venv/bin"
ExecStart=/home/${VPS_USER}/${PROJECT_NAME}/venv/bin/gunicorn web.asgi:application -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:${APP_PORT}
Restart=always

[Install]
WantedBy=multi-user.target
EEOF

    sudo systemctl daemon-reload
    sudo systemctl enable $PROJECT_NAME
    sudo systemctl start $PROJECT_NAME
}

# Function to setup Git webhook
setup_git_webhook() {
    echo "Setting up Git webhook..."
    mkdir -p /home/${VPS_USER}/webhooks

    tee /home/${VPS_USER}/webhooks/update.sh << EEOF
#!/bin/bash
cd /home/${VPS_USER}/${PROJECT_NAME}
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart $PROJECT_NAME
EEOF

    chmod +x /home/${VPS_USER}/webhooks/update.sh
}

# Function to run a command on the server
run_command_on_server() {
    check_required_vars
    ensure_sshpass

    log "Running command on server: $1"
    sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "$1"
}

# Main setup function for VPS
setup_vps() {
    check_required_vars

    log "Starting VPS setup..."

    # Create a temporary script with all functions and environment variables
    TMP_SCRIPT=$(mktemp)

    # First export all environment variables
    cat << EOF > "$TMP_SCRIPT"
export PROJECT_NAME="$PROJECT_NAME"
export DOMAIN_NAME="$DOMAIN_NAME"
export APP_PORT="$APP_PORT"
export DB_NAME="$DB_NAME"
export DB_USER="$DB_USER"
export DB_PASSWORD="$DB_PASSWORD"
export VPS_USER="$VPS_USER"

EOF

    # Then append the functions
    cat << 'EOF' >> "$TMP_SCRIPT"
# Function to install system dependencies
install_system_dependencies() {
    echo "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3-pip python3-full nginx git certbot python3-certbot-nginx ufw fail2ban \
        postgresql postgresql-contrib python3-dev libpq-dev build-essential sshpass
}

# Function to setup PostgreSQL
setup_postgresql() {
    echo "Setting up PostgreSQL..."
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" || true
}

# Function to setup firewall
setup_firewall() {
    echo "Setting up firewall..."
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80
    sudo ufw allow 443
    sudo ufw --force enable
}

# Function to setup fail2ban
setup_fail2ban() {
    echo "Setting up fail2ban..."
    sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
}

# Function to setup Python environment
setup_python_env() {
    echo "Setting up Python environment..."
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --break-system-packages --upgrade pip
    pip install --break-system-packages -r requirements.txt
    pip install --break-system-packages uvicorn gunicorn psycopg2-binary
}

# Function to setup Nginx
setup_nginx() {
    echo "Setting up Nginx..."
    sudo rm -f /etc/nginx/sites-enabled/default

    sudo tee /etc/nginx/sites-available/$PROJECT_NAME << EEOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location /static/ {
        alias /home/${VPS_USER}/${PROJECT_NAME}/staticfiles/;
    }

    location /media/ {
        alias /home/${VPS_USER}/${PROJECT_NAME}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EEOF

    sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
}

# Function to setup SSL
setup_ssl() {
    if [ ! -z "$DOMAIN_NAME" ]; then
        echo "Setting up SSL for $DOMAIN_NAME..."
        sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@${DOMAIN_NAME}
    fi
}

# Function to setup systemd service
setup_systemd_service() {
    echo "Setting up systemd service..."
    sudo tee /etc/systemd/system/$PROJECT_NAME.service << EEOF
[Unit]
Description=$PROJECT_NAME website
After=network.target

[Service]
User=${VPS_USER}
Group=${VPS_USER}
WorkingDirectory=/home/${VPS_USER}/${PROJECT_NAME}
Environment="PATH=/home/${VPS_USER}/${PROJECT_NAME}/venv/bin"
ExecStart=/home/${VPS_USER}/${PROJECT_NAME}/venv/bin/gunicorn web.asgi:application -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:${APP_PORT}
Restart=always

[Install]
WantedBy=multi-user.target
EEOF

    sudo systemctl daemon-reload
    sudo systemctl enable $PROJECT_NAME
    sudo systemctl start $PROJECT_NAME
}

# Function to setup Git webhook
setup_git_webhook() {
    echo "Setting up Git webhook..."
    mkdir -p /home/${VPS_USER}/webhooks

    tee /home/${VPS_USER}/webhooks/update.sh << EEOF
#!/bin/bash
cd /home/${VPS_USER}/${PROJECT_NAME}
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart $PROJECT_NAME
EEOF

    chmod +x /home/${VPS_USER}/webhooks/update.sh
}

# Main execution
install_system_dependencies
setup_firewall
setup_fail2ban

# Clone repository if it doesn't exist
if [ ! -d "/home/${VPS_USER}/${PROJECT_NAME}" ]; then
    git clone https://github.com/AlphaOneLabs/education-website.git /home/${VPS_USER}/${PROJECT_NAME}
fi

cd /home/${VPS_USER}/${PROJECT_NAME}
setup_postgresql
setup_python_env
python manage.py migrate
python manage.py collectstatic --noinput

setup_nginx
setup_ssl
setup_systemd_service
setup_git_webhook
EOF

    # Copy the script to the remote server and execute it
    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no "$TMP_SCRIPT" $VPS_USER@$VPS_IP:/tmp/setup.sh
    sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "bash /tmp/setup.sh"

    # Clean up
    rm "$TMP_SCRIPT"

    # Wait a bit for services to fully start
    log "Waiting for services to start..."
    sleep 10

    # Always open IP address
    IP_URL="http://${VPS_IP}"
    log "Opening IP address: $IP_URL"
    if command_exists xdg-open; then
        xdg-open "$IP_URL"
    elif command_exists open; then
        open "$IP_URL"
    else
        log "Could not automatically open browser. Please visit: $IP_URL"
    fi

    # If domain name is set, open that too
    if [ ! -z "$DOMAIN_NAME" ]; then
        DOMAIN_URL="https://${DOMAIN_NAME}"
        log "Opening domain: $DOMAIN_URL"
        if command_exists xdg-open; then
            xdg-open "$DOMAIN_URL"
        elif command_exists open; then
            open "$DOMAIN_URL"
        else
            log "Could not automatically open browser. Please visit: $DOMAIN_URL"
        fi
    fi
}

# Main execution
if [ "$1" == "vps" ]; then
    ensure_sshpass
    setup_vps
elif [ "$1" == "run" ]; then
    if [ -z "$2" ]; then
        log "Error: No command specified. Usage: ./setup.sh run 'command_to_run'"
        exit 1
    fi
    run_command_on_server "$2"
else
    log "Starting local setup..."
    cd /home/alphaonelabs99282llkb/web/
    git reset --hard HEAD
    git pull

    if find /home/alphaonelabs99282llkb/web/requirements.txt -mmin -1 | grep -q .; then
        pip install -r requirements.txt
    fi
    python manage.py migrate
    python manage.py collectstatic --noinput
    log "Local setup completed!"
fi
