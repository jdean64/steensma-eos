#!/bin/bash
# Deploy EOS Platform to production: coresteensma.com
# Usage: bash .devcontainer/deploy-prod.sh

set -e

PROD_HOST="coresteensma.com"
PROD_USER="ubuntu"
PROD_DIR="/home/ubuntu/eosplatform"
PROD_SERVICE="eosplatform.service"

echo "============================================"
echo "  EOS Platform -> Production Deploy"
echo "  $PROD_USER@$PROD_HOST:$PROD_DIR"
echo "============================================"

# Make sure local changes are pushed to GitHub first
echo ""
echo ">>> Checking local git status..."
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "    You have uncommitted changes. Commit and push first:"
    echo "    git add -A && git commit -m 'your message' && git push"
    exit 1
fi

LOCAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
LOCAL_COMMIT=$(git rev-parse --short HEAD)
echo "    Branch: $LOCAL_BRANCH  Commit: $LOCAL_COMMIT"

# Verify SSH key exists
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo ""
    echo "    ERROR: ~/.ssh/id_ed25519 not found."
    echo "    Set the SSH_PRIVATE_KEY Codespace secret and rebuild the container."
    exit 1
fi

echo ""
echo ">>> Connecting to $PROD_HOST and deploying..."

ssh -o StrictHostKeyChecking=no "$PROD_USER@$PROD_HOST" bash << EOF
    set -e
    echo "  [server] Pulling latest code..."
    cd $PROD_DIR
    git pull origin main

    echo "  [server] Installing/updating dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt --quiet

    echo "  [server] Restarting service..."
    sudo systemctl restart $PROD_SERVICE

    echo "  [server] Service status:"
    systemctl is-active $PROD_SERVICE && echo "  ✓ $PROD_SERVICE is RUNNING" || echo "  ✗ $PROD_SERVICE FAILED"
EOF

echo ""
echo ">>> Deploy complete!"
echo "    Live at: https://eos.coresteensma.com"
echo "    Logs:    ssh $PROD_USER@$PROD_HOST 'journalctl -u $PROD_SERVICE -n 50'"
