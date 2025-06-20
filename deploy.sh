#!/bin/bash
set -e

# Check if .env file exists and source it
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "Error: .env file not found!"
    exit 1
fi

# Check required environment variables for VPS connection
required_vars=("VPS_IP" "VPS_USER" "VPS_PASSWORD")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "Error: The following environment variables must be set for VPS connection:"
    printf '%s\n' "${missing_vars[@]}"
    echo "Please add them to your .env file or export them in your environment"
    exit 1
fi

# Install Ansible if not installed
if ! command -v ansible &> /dev/null; then
    echo "Installing Ansible..."
    python3 -m pip install --user ansible
fi

# Run Ansible playbook
echo "Starting deployment..."
ansible-playbook site.yml -i inventory.yml

echo "Deployment completed successfully!" 