#!/usr/bin/env bash
# ==============================================================================
# Oracle Cloud Infrastructure (OCI) Host Bootstrap Script
#
# Tested on: Ubuntu 22.04 LTS / 24.04 LTS (x86_64 and ARM64 / Ampere A1)
# Purpose:
#   1. Installs Docker Engine & Docker Compose plugin
#   2. Configures user permissions (no-sudo docker)
#   3. Fixes OCI OS-level firewall (iptables) to allow ports 80, 443, 8000, 8501
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo "🚀 Starting OCI Host Bootstrap for Customer Churn Pipeline"
echo "=========================================================="

# 1. Update package database and install prerequisites
echo "📦 Updating system packages..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    make \
    iptables-persistent \
    netfilter-persistent

# 2. Add Docker official GPG key and APT repository
echo "🐳 Setting up Docker official repository..."
sudo install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
fi

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# 3. Add current user to the docker group
CURRENT_USER=$(whoami)
echo "👤 Adding user '$CURRENT_USER' to docker group..."
sudo usermod -aG docker "$CURRENT_USER"

# 4. Configure OCI OS Firewall (iptables)
# CRITICAL: OCI Ubuntu images include default iptables rules that reject
# all incoming traffic except port 22, even if OCI VCN Security Lists allow it!
echo "🛡️ Configuring OS-level iptables firewall for OCI..."

# Define ports needed for the pipeline
PORTS=(80 443 8000 8501 5000 8080)

for PORT in "${PORTS[@]}"; do
    # Check if rule already exists to maintain idempotency
    if ! sudo iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null; then
        echo "   Allowing incoming TCP port $PORT..."
        sudo iptables -I INPUT 6 -p tcp --dport "$PORT" -m state --state NEW,ESTABLISHED -j ACCEPT
    else
        echo "   Port $PORT already allowed in iptables."
    fi
done

# Save rules so they persist across instance reboots
echo "💾 Persisting iptables rules..."
sudo netfilter-persistent save

# 5. Enable and start Docker service
sudo systemctl enable docker
sudo systemctl start docker

echo "=========================================================="
echo "✅ OCI Host Bootstrap Complete!"
echo "=========================================================="
echo "Next steps:"
echo "1. Log out and log back in (or run 'newgrp docker') to activate group permissions:"
echo "   newgrp docker"
echo "2. Clone your repository:"
echo "   git clone https://github.com/Alokkr00/Customer-Churn-Pipeline.git"
echo "   cd Customer-Churn-Pipeline"
echo "3. Run the production stack:"
echo "   docker compose -f docker-compose.prod.yml up -d"
echo "=========================================================="
