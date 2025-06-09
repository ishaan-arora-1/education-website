#!/bin/bash

# Local setup script for Education Website
# This script handles local development setup and updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${GREEN}$1${NC}"
}

error() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${RED}ERROR: $1${NC}" >&2
}

warn() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING: $1${NC}"
}

info() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${BLUE}INFO: $1${NC}"
}

# Default values
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="$PROJECT_DIR/venv"
PYTHON_VERSION="3.11"

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Local setup and update script for Education Website

OPTIONS:
    -r, --reset             Reset git to HEAD before pulling
    -f, --force-requirements Force reinstall requirements even if not modified
    -h, --help              Show this help message

EXAMPLES:
    $0                      # Standard local update
    $0 -r                   # Reset and update
    $0 -f                   # Force requirements reinstall

EOF
}

# Parse command line arguments
RESET_GIT=false
FORCE_REQUIREMENTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--reset)
            RESET_GIT=true
            shift
            ;;
        -f|--force-requirements)
            FORCE_REQUIREMENTS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Change to project directory
cd "$PROJECT_DIR"

log "Starting local setup in: $PROJECT_DIR"

# Reset git if requested
if [ "$RESET_GIT" = true ]; then
    log "Resetting git to HEAD..."
    git reset --hard HEAD
fi

# Pull latest changes
log "Pulling latest changes from git..."
git pull

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    log "Creating Python virtual environment..."
    python$PYTHON_VERSION -m venv "$VENV_PATH"
fi

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Check if requirements need to be installed
INSTALL_REQUIREMENTS=false

if [ "$FORCE_REQUIREMENTS" = true ]; then
    INSTALL_REQUIREMENTS=true
    log "Force installing requirements..."
elif [ ! -f "$VENV_PATH/.requirements_installed" ]; then
    INSTALL_REQUIREMENTS=true
    log "Requirements not previously installed, installing..."
elif [ requirements.txt -nt "$VENV_PATH/.requirements_installed" ]; then
    INSTALL_REQUIREMENTS=true
    log "Requirements.txt has been modified, reinstalling..."
fi

# Install/update requirements if needed
if [ "$INSTALL_REQUIREMENTS" = true ]; then
    log "Installing Python requirements..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install uvicorn gunicorn psycopg2-binary
    touch "$VENV_PATH/.requirements_installed"
else
    log "Requirements are up to date, skipping installation"
fi

# Run Django migrations
log "Running Django migrations..."
python manage.py migrate

# Collect static files
log "Collecting static files..."
python manage.py collectstatic --noinput

log "Local setup completed successfully!"

# Show helpful information
info "Virtual environment: $VENV_PATH"
info "To activate: source $VENV_PATH/bin/activate"
info "To run server: python manage.py runserver"
info "To run with Gunicorn: gunicorn web.asgi:application -w 4 -k uvicorn.workers.UvicornWorker" 