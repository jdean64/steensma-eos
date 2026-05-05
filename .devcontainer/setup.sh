#!/bin/bash
# Codespace setup: install deps + configure SSH for production deployment

set -e

echo ">>> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Configuring SSH for production deployment..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

if [ -n "$SSH_PRIVATE_KEY" ]; then
    echo "$SSH_PRIVATE_KEY" | base64 -d > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    echo "    SSH key installed."
else
    echo "    WARNING: SSH_PRIVATE_KEY secret not set. Run: gh secret set SSH_PRIVATE_KEY"
    echo "    To encode your key: cat ~/.ssh/id_ed25519 | base64 -w 0"
fi

# Pre-trust the production server so deploy won't prompt
ssh-keyscan -H coresteensma.com >> ~/.ssh/known_hosts 2>/dev/null
echo "    Known hosts updated for coresteensma.com"

echo ""
echo ">>> Setup complete."
echo "    To start app locally:  python app.py"
echo "    To deploy to prod:     bash .devcontainer/deploy-prod.sh"
