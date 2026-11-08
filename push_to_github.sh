#!/usr/bin/env bash
# Helper script to connect and push FRED Chat to GitHub
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Ensure git is available in PATH
if ! command -v git &> /dev/null; then
    if [ -f "/tmp/bin/git" ]; then
        export PATH="/tmp/bin:$PATH"
    else
        echo "❌ Git binary not found in PATH or /tmp/bin."
        exit 1
    fi
fi

echo "========================================================"
echo " 🚀 Push FRED Chat to GitHub"
echo "========================================================"

# Check if origin is already set
CURRENT_ORIGIN=$(git remote get-url origin 2>/dev/null || true)

if [ -n "$CURRENT_ORIGIN" ]; then
    echo "Current remote origin: $CURRENT_ORIGIN"
    read -p "Do you want to use this remote? (y/n): " USE_EXISTING
    if [ "$USE_EXISTING" != "y" ] && [ "$USE_EXISTING" != "Y" ]; then
        read -p "Enter your GitHub repository URL (e.g. https://github.com/username/repo.git): " REPO_URL
        git remote set-url origin "$REPO_URL"
    fi
else
    read -p "Enter your GitHub username: " GH_USER
    read -p "Enter your GitHub repository name: " GH_REPO
    git remote add origin "https://github.com/${GH_USER}/${GH_REPO}.git"
fi

echo ""
echo "Pushing branch 'main' to GitHub..."
echo "When prompted for password, paste your GitHub Personal Access Token (starts with ghp_)."
echo ""

git push -u origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
