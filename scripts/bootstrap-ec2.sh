#!/usr/bin/env bash
# Prepara una EC2 Ubuntu 24.04 recién creada (AWS Academy Learner Lab).
# Uso:  bash scripts/bootstrap-ec2.sh      (luego cerrar sesión SSH y volver a entrar)
set -euo pipefail

# 1) Swap de 2 GB: imprescindible en t3.small (2 GB RAM) para que n8n no muera por OOM
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf && sudo sysctl -p /etc/sysctl.d/99-swap.conf
fi

# 2) Docker Engine + compose plugin (script oficial)
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

# 3) Utilidades
sudo apt-get update -y && sudo apt-get install -y git python3 curl
sudo timedatectl set-timezone America/Bogota

echo "Listo. Sal de la sesión SSH y vuelve a entrar para usar docker sin sudo."
