#!/bin/bash

# Ansible deployment script for Education Website
# This script replaces the old bash-based deployment

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
ENVIRONMENT="production"
TAGS=""
LIMIT=""
VAULT_PASSWORD_FILE=""
DRY_RUN=false
UPDATE_ONLY=false

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Education Website using Ansible

OPTIONS:
    -e, --environment ENV    Target environment (production, staging, development) [default: production]
    -t, --tags TAGS         Run only tasks with specific tags (comma-separated)
    -l, --limit HOSTS       Limit deployment to specific hosts
    -v, --vault-password    Path to vault password file
    -c, --check             Run in check mode (dry run)
    -u, --update-only       Run update playbook instead of full deployment
    -h, --help              Show this help message

EXAMPLES:
    $0                                          # Deploy to production
    $0 -e staging                              # Deploy to staging
    $0 -e production -t django,nginx           # Deploy only Django and Nginx components
    $0 -l primary                              # Deploy only to primary server
    $0 -c                                      # Dry run
    $0 -u                                      # Quick update only

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tags)
            TAGS="$2"
            shift 2
            ;;
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -v|--vault-password)
            VAULT_PASSWORD_FILE="$2"
            shift 2
            ;;
        -c|--check)
            DRY_RUN=true
            shift
            ;;
        -u|--update-only)
            UPDATE_ONLY=true
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

# Check if ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    error "Ansible is not installed. Please install Ansible first."
    exit 1
fi

# Change to ansible directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ANSIBLE_DIR"

# Check if vault file exists
if [ ! -f "group_vars/all/vault.yml" ]; then
    error "Vault file not found. Please create and encrypt group_vars/all/vault.yml"
    exit 1
fi

# Build ansible-playbook command
ANSIBLE_CMD="ansible-playbook"

# Add vault password file if provided
if [ -n "$VAULT_PASSWORD_FILE" ]; then
    ANSIBLE_CMD="$ANSIBLE_CMD --vault-password-file $VAULT_PASSWORD_FILE"
else
    ANSIBLE_CMD="$ANSIBLE_CMD --ask-vault-pass"
fi

# Add environment limit
if [ -n "$ENVIRONMENT" ]; then
    ANSIBLE_CMD="$ANSIBLE_CMD --limit $ENVIRONMENT"
fi

# Add specific host limit
if [ -n "$LIMIT" ]; then
    ANSIBLE_CMD="$ANSIBLE_CMD --limit $LIMIT"
fi

# Add tags
if [ -n "$TAGS" ]; then
    ANSIBLE_CMD="$ANSIBLE_CMD --tags $TAGS"
fi

# Add check mode
if [ "$DRY_RUN" = true ]; then
    ANSIBLE_CMD="$ANSIBLE_CMD --check --diff"
fi

# Choose playbook
if [ "$UPDATE_ONLY" = true ]; then
    PLAYBOOK="update.yml"
    log "Running update playbook..."
else
    PLAYBOOK="deploy.yml"
    log "Running full deployment playbook..."
fi

# Add playbook to command
ANSIBLE_CMD="$ANSIBLE_CMD $PLAYBOOK"

# Show command that will be executed
info "Executing: $ANSIBLE_CMD"

# Execute the command
if eval "$ANSIBLE_CMD"; then
    log "Deployment completed successfully!"
else
    error "Deployment failed!"
    exit 1
fi 