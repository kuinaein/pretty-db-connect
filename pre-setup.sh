#!/usr/bin/env bash
set -eu

apt-add-repository ppa:ansible/ansible
# aptコマンドのCLIインターフェイスは不安定らしい
apt-get update
sudo apt-get install -y ansible
apt-get full-upgrade -y
