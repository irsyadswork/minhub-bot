#!/usr/bin/env bash
# Pasang Minhub di server Ubuntu: bash deploy/setup.sh
# Aman dijalankan ulang (misal setelah update kode).
set -e
cd "$(dirname "$0")/.."

sudo timedatectl set-timezone Asia/Jakarta || true
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip fonts-dejavu-core fonts-montserrat

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

sed "s#__DIR__#$(pwd)#g; s#__USER__#$(whoami)#g" deploy/minhub.service | sudo tee /etc/systemd/system/minhub.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable minhub
sudo systemctl restart minhub
sleep 5
sudo systemctl status minhub --no-pager -l | head -n 20
