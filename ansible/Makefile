.PHONY: help vault-edit vault-view vault-decrypt vault-encrypt vault-rekey ping check bootstrap-pve

# Variables
VAULT_FILE = inventory/group_vars/all/vault.yml
VAULT_PASS = ./.vault_pass
PLAYBOOK_DIR = playbooks

# Default target
help:
	@echo "Ansible Vault & Playbook Management"
	@echo "===================================="
	@echo ""
	@echo "Vault Operations:"
	@echo "  make vault-edit      - Edit encrypted vault file"
	@echo "  make vault-view      - View decrypted vault content"
	@echo "  make vault-decrypt   - Decrypt vault file (temporary)"
	@echo "  make vault-encrypt   - Encrypt vault file"
	@echo "  make vault-rekey     - Change vault password"
	@echo ""
	@echo "Ansible Operations:"
	@echo "  make ping            - Test connectivity to all hosts"
	@echo "  make check           - Check playbook syntax"
	@echo ""
	@echo "Playbooks:"
	@echo "  make bootstrap-pve   - Run bootstrap_pve.yml playbook"
	@echo ""

# Vault operations
vault-edit:
	@echo "Editing vault file..."
	@ansible-vault edit $(VAULT_FILE) --vault-password-file $(VAULT_PASS)

vault-view:
	@echo "Viewing vault file..."
	@ansible-vault view $(VAULT_FILE) --vault-password-file $(VAULT_PASS)

vault-decrypt:
	@echo "Decrypting vault file (remember to re-encrypt after editing!)..."
	@ansible-vault decrypt $(VAULT_FILE) --vault-password-file $(VAULT_PASS)
	@echo "⚠️  Don't forget to run 'make vault-encrypt' after editing!"

vault-encrypt:
	@echo "Encrypting vault file..."
	@ansible-vault encrypt $(VAULT_FILE) --vault-password-file $(VAULT_PASS)

vault-rekey:
	@echo "Changing vault password..."
	@ansible-vault rekey $(VAULT_FILE) --vault-password-file $(VAULT_PASS)

# Ansible operations
ping:
	@echo "Testing connectivity..."
	@ansible all -m ping

check:
	@echo "Checking playbook syntax..."
	@ansible-playbook --syntax-check $(PLAYBOOK_DIR)/*.yml

# Playbooks
bootstrap-pve:
	@echo "Running bootstrap_pve.yml playbook..."
	@ansible-playbook $(PLAYBOOK_DIR)/bootstrap_pve.yml

