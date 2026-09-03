#!/usr/bin/env bash
# ==============================================================================
# ShreeNexa Terminal — AWS Lightsail Mumbai (ap-south-1) Provisioning Script
# Feature: F13.2
# ==============================================================================
# Provisions Ubuntu 24.04 LTS host in Mumbai region:
# - System users, permissions, limits
# - Docker Engine & Compose plugin
# - Caddy Web Server (TLS & reverse proxy)
# - Host network policy & firewall rules (Strict Port Allowlist: 22, 80, 443)
# ==============================================================================

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "=== [1/6] Initializing Host System Tuning ==="
# Kernel & network tuning for persistent real-time streaming
cat << 'EOF' > /etc/sysctl.d/99-shreenexa.conf
# Max open connections and backlog
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
# Buffer sizes
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
# File descriptors
fs.file-max = 2097152
EOF
sysctl --system > /dev/null

echo "=== [2/6] Configuring System User & Directories ==="
if ! id -u shreenexa > /dev/null 2>&1; then
    groupadd -g 10001 shreenexa
    useradd -u 10001 -g shreenexa -d /opt/shreenexa -s /usr/sbin/nologin -c "ShreeNexa Production User" shreenexa
fi

mkdir -p /opt/shreenexa/{backend,config,data/services/{postgres,redis},infra/{caddy,lightsail},logs/caddy}
chown -R shreenexa:shreenexa /opt/shreenexa

echo "=== [3/6] Installing Prerequisites & Docker ==="
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    jq \
    python3 \
    python3-pip

# Install Docker
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
fi

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== [4/6] Installing Caddy Web Server ==="
if ! command -v caddy > /dev/null 2>&1; then
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -y
    apt-get install -y caddy
fi

echo "=== [5/6] Enforcing Strict Network Policy & Firewall ==="
# Default: Deny all incoming, allow outgoing
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Public Allowed Ports
ufw allow 22/tcp comment 'SSH - Admin access'
ufw allow 80/tcp comment 'HTTP - Let us Encrypt / Caddy HTTP redirect'
ufw allow 443/tcp comment 'HTTPS - Public TLS reverse proxy'

# Explicitly ensure internal ports are denied on public interfaces
# (Postgres 5432, Valkey 6379, Blue/Green API 8000/8001, Sandbox 8080/8081/8082)
for port in 5432 6379 8000 8001 8080 8081 8082; do
    ufw deny "${port}/tcp" comment "Blocked internal port ${port}"
done

# Enable firewall
ufw --force enable

echo "=== [6/6] Provisioning Complete ==="
echo "Host successfully provisioned for ShreeNexa Terminal in Mumbai (ap-south-1)."
echo "Firewall active. Only ports 22, 80, 443 are reachable externally."
