#!/usr/bin/env bash
# Install Docker and Docker Compose from Docker's official repository.
# Run on a fresh Ubuntu instance (e.g. Lightsail).
# Based on https://docs.docker.com/engine/install/ubuntu/
set -euo pipefail

# Remove any old/conflicting Docker packages
sudo apt-get remove -y \
    $(dpkg --get-selections docker.io docker-compose docker-compose-v2 \
        docker-doc podman-docker containerd runc 2>/dev/null | cut -f1) \
    2>/dev/null || true

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update

# Install Docker Engine and Compose plugin
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow current user to run Docker without sudo
sudo usermod -aG docker "$USER"

# Start Docker and enable on boot
sudo systemctl enable --now docker

echo ""
echo "Done. Log out and back in for the docker group to take effect."
echo "Then verify with: docker compose version"
