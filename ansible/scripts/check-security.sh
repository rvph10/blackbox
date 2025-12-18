#!/usr/bin/env bash

# Security Check Script for Ansible Configuration
# Ensures no sensitive data is exposed before committing

set -u  # Exit on undefined variables, but not on command failures

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$ANSIBLE_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
ERRORS=0
WARNINGS=0
PASSED=0

echo "================================================"
echo "Security Check for Ansible Configuration"
echo "================================================"
echo ""

# Function to print status
print_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

# Check 1: Vault file is encrypted
echo "Checking vault encryption..."
if [ -f "$ANSIBLE_DIR/inventory/group_vars/all/vault.yml" ]; then
    if grep -q "^\$ANSIBLE_VAULT" "$ANSIBLE_DIR/inventory/group_vars/all/vault.yml"; then
        print_pass "Vault file is encrypted"
    else
        print_error "Vault file is NOT encrypted! Run: make vault-encrypt"
    fi
else
    print_warning "Vault file not found at inventory/group_vars/all/vault.yml"
fi

# Check 2: Vault password file is not tracked by git
echo "Checking vault password file..."
cd "$REPO_ROOT"
if [ -f "$ANSIBLE_DIR/.vault_pass" ]; then
    if git check-ignore -q "$ANSIBLE_DIR/.vault_pass" 2>/dev/null || true; then
        if git check-ignore -q "$ANSIBLE_DIR/.vault_pass" 2>/dev/null; then
            print_pass "Vault password file is properly ignored by git"
        else
            print_error "Vault password file is NOT ignored by git!"
        fi
    fi
else
    print_warning "Vault password file not found (this is OK if using alternative auth)"
fi

# Check 3: No hardcoded SSH keys in playbooks
echo "Checking for hardcoded SSH keys..."
SSH_KEYS=$(grep -r "ssh-\(rsa\|ed25519\|ecdsa\|dss\)" "$ANSIBLE_DIR/playbooks" \
    "$ANSIBLE_DIR/inventory/hosts.ini" \
    "$ANSIBLE_DIR/inventory/group_vars" 2>/dev/null | grep -v "vault.yml" | grep -v "{{ vault" || true)
if [ -n "$SSH_KEYS" ]; then
    print_error "Found hardcoded SSH keys! Move them to vault.yml"
    echo "$SSH_KEYS"
else
    print_pass "No hardcoded SSH keys found"
fi

# Check 4: No hardcoded private IPs in playbooks and inventory
echo "Checking for hardcoded private IPs..."
PRIVATE_IPS=$(grep -rE '(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)' \
    "$ANSIBLE_DIR/playbooks" \
    "$ANSIBLE_DIR/inventory/hosts.ini" \
    "$ANSIBLE_DIR/inventory/group_vars" 2>/dev/null | \
    grep -v "vault.yml" | \
    grep -v "{{ vault" | \
    grep -v "^Binary" | \
    grep -v "#" || true)
if [ -n "$PRIVATE_IPS" ]; then
    print_warning "Found hardcoded private IPs (consider moving to vault)"
else
    print_pass "No hardcoded private IPs found in config files"
fi

# Check 5: No passwords in plain text
echo "Checking for plain text passwords..."
PASSWORDS=$(grep -ri "password:\s*['\"]" "$ANSIBLE_DIR" 2>/dev/null | \
    grep -v "vault.yml" | \
    grep -v "PasswordAuthentication" | \
    grep -v "vault_password_file" | \
    grep -v "check-security.sh" | \
    grep -v "{{ vault" | \
    grep -v "^Binary" || true)
if [ -n "$PASSWORDS" ]; then
    print_error "Found plain text passwords!"
    echo "$PASSWORDS"
else
    print_pass "No plain text passwords found"
fi

# Check 6: Sensitive files are in .gitignore
echo "Checking .gitignore configuration..."
GITIGNORE="$REPO_ROOT/.gitignore"
if [ -f "$GITIGNORE" ]; then
    MISSING_ENTRIES=()
    
    grep -q "\.vault_pass" "$GITIGNORE" || MISSING_ENTRIES+=(".vault_pass")
    grep -q "vault_pass" "$GITIGNORE" || MISSING_ENTRIES+=("vault_pass")
    grep -q "\.env" "$GITIGNORE" || MISSING_ENTRIES+=(".env")
    
    if [ ${#MISSING_ENTRIES[@]} -eq 0 ]; then
        print_pass ".gitignore is properly configured"
    else
        print_warning ".gitignore missing entries: ${MISSING_ENTRIES[*]}"
    fi
else
    print_error ".gitignore file not found!"
fi

# Check 7: Vault password file has correct permissions
echo "Checking file permissions..."
if [ -f "$ANSIBLE_DIR/.vault_pass" ]; then
    PERMS=$(stat -c "%a" "$ANSIBLE_DIR/.vault_pass" 2>/dev/null || stat -f "%OLp" "$ANSIBLE_DIR/.vault_pass" 2>/dev/null)
    if [ "$PERMS" = "600" ] || [ "$PERMS" = "400" ]; then
        print_pass "Vault password file has secure permissions ($PERMS)"
    else
        print_warning "Vault password file permissions are $PERMS (recommended: 600)"
    fi
fi

# Check 8: Check if vault password is default/weak
echo "Checking vault password strength..."
if [ -f "$ANSIBLE_DIR/.vault_pass" ]; then
    VAULT_PASS=$(cat "$ANSIBLE_DIR/.vault_pass")
    if [ "$VAULT_PASS" = "change_me_please" ]; then
        print_error "Using default vault password! Change it with: make vault-rekey"
    elif [ ${#VAULT_PASS} -lt 12 ]; then
        print_warning "Vault password is short (${#VAULT_PASS} chars). Consider using 12+ characters"
    else
        print_pass "Vault password appears to be set"
    fi
fi

# Check 9: Verify ansible.cfg points to correct vault password file
echo "Checking ansible.cfg configuration..."
ANSIBLE_CFG="$ANSIBLE_DIR/ansible.cfg"
if [ -f "$ANSIBLE_CFG" ]; then
    if grep -q "vault_password_file.*vault_pass" "$ANSIBLE_CFG"; then
        print_pass "ansible.cfg vault configuration is correct"
    else
        print_warning "ansible.cfg may not have vault_password_file configured"
    fi
else
    print_warning "ansible.cfg not found"
fi

# Summary
echo ""
echo "================================================"
echo "Summary"
echo "================================================"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Errors:${NC} $ERRORS"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Security check FAILED!${NC}"
    echo "Please fix the errors above before committing."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Security check passed with warnings${NC}"
    echo "Consider addressing the warnings above."
    exit 0
else
    echo -e "${GREEN}✅ All security checks passed!${NC}"
    echo "Safe to commit."
    exit 0
fi

