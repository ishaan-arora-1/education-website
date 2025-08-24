#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper around ansible-playbook using inventory.yml.
#
# Usage examples:
#   ./deploy.sh                   # run playbook with defaults
#   ./deploy.sh -l production     # limit to host 'production'
#   ./deploy.sh --tags app        # run only tasks tagged 'app'
#   ./deploy.sh --check           # dry-run
#
# inventory.yml example (already created):
# all:
#   hosts:
#     production:
#       ansible_host: 203.0.113.10
#       ansible_user: root
#       ansible_password: "CHANGE_ME"  # Use ansible-vault in real deployments
#
# To secure the password with Ansible Vault instead of plain text:
#   mkdir -p group_vars/all
#   ansible-vault create group_vars/all/vault.yml   # add: vault_ansible_password: YOUR_PASS
#   Then in host vars (inventory or group_vars) reference:
#     ansible_password: "{{ vault_ansible_password }}"
#   Run with:
#     ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass

cd "$(dirname "$0")"

EXTRA_ARGS=("$@")

# ── Ensure SSH host key is trusted (needed when using password + Host Key checking) ──
# Parse first ansible_host and optional ansible_port from inventory.yml (simple YAML assumptions)
HOST_IP=$(awk '/ansible_host:/ {print $2; exit}' inventory.yml || true)
HOST_PORT=$(awk '/ansible_port:/ {print $2; exit}' inventory.yml || true)

if [[ -n "${HOST_IP}" ]]; then
	mkdir -p ~/.ssh
	chmod 700 ~/.ssh
	if ! ssh-keygen -F "${HOST_IP}" >/dev/null 2>&1; then
		echo "→ Adding SSH host key for ${HOST_IP} to known_hosts" >&2
		if [[ -n "${HOST_PORT}" ]]; then
			ssh-keyscan -p "${HOST_PORT}" -H "${HOST_IP}" >> ~/.ssh/known_hosts 2>/dev/null || echo "⚠️ Warning: Could not retrieve host key for ${HOST_IP}:${HOST_PORT}" >&2
		else
			ssh-keyscan -H "${HOST_IP}" >> ~/.ssh/known_hosts 2>/dev/null || echo "⚠️ Warning: Could not retrieve host key for ${HOST_IP}" >&2
		fi
	fi
fi

ansible-playbook -i inventory.yml playbook.yml "${EXTRA_ARGS[@]}"
