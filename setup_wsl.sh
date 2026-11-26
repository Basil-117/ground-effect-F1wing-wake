#!/bin/bash
# One-time setup inside Ubuntu (WSL2 on Windows, or native Ubuntu).
# Installs mesh/plot libraries and a Python environment. OpenFOAM: uses your Docker image if
# Docker Desktop's WSL integration is on; otherwise INSTALL_NATIVE=1 installs openfoam.com v2606.
# Usage:  bash setup_wsl.sh            (asks for your Ubuntu password once)
# Options: INSTALL_NATIVE=1  OF_VERSION=2606  SKIP_OPENFOAM=1 (Python part only)
set -e
OF=${OF_VERSION:-2606}
echo "== 1/4  system packages"
sudo apt-get update
sudo apt-get install -y curl unzip python3-venv python3-pip \
     libglu1-mesa libgomp1 libgl1 libx11-6 libxext6 libfontconfig1 libxcursor1 libxinerama1 libxft2 libxrender1 libxfixes3
echo "== 2/4  OpenFOAM"
if [ -n "$SKIP_OPENFOAM" ]; then echo "   skipped (SKIP_OPENFOAM set)"
elif command -v docker >/dev/null 2>&1 && docker images --format '{{.Repository}}' 2>/dev/null | grep -qi openfoam; then
  echo "   using your OpenFOAM Docker image: $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -i openfoam | head -1)"
  echo "   (nothing to install; the run scripts call it through foam.sh)"
  SKIP_OPENFOAM=1
elif [ -f /usr/lib/openfoam/openfoam$OF/etc/bashrc ]; then echo "   v$OF already installed natively"
elif [ -n "$INSTALL_NATIVE" ]; then
  curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
  sudo apt-get update && sudo apt-get install -y openfoam$OF-default
else
  echo "   No OpenFOAM found from inside Ubuntu."
  echo "   If you use Docker Desktop: open Docker Desktop > Settings > Resources > WSL integration,"
  echo "   switch on 'Ubuntu', click Apply & restart, then run this script again."
  echo "   (Or install OpenFOAM natively instead:  INSTALL_NATIVE=1 bash setup_wsl.sh)"
  SKIP_OPENFOAM=1
fi
echo "== 3/4  Python environment (~/f1env)"
python3 -m venv ~/f1env
~/f1env/bin/pip install --quiet --upgrade pip
~/f1env/bin/pip install gmsh numpy scipy pandas matplotlib scikit-learn SALib statsmodels
echo "== 4/4  auto-load both in every new Ubuntu window"
if ! grep -q "dirty-air project" ~/.bashrc; then
  {
    echo "# dirty-air project"
    echo "source ~/f1env/bin/activate"
    [ -f /usr/lib/openfoam/openfoam$OF/etc/bashrc ] && echo "source /usr/lib/openfoam/openfoam$OF/etc/bashrc"
  } >> ~/.bashrc
fi
echo
bash "$(dirname "$0")/foam.sh" --info || true
echo "Setup finished. Close this Ubuntu window, open a new one, then run:"
echo "   cd ~/dirty_air && bash smoke_test.sh"
