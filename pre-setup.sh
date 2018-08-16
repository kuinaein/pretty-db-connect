#!/usr/bin/env bash
set -eu

export DEBIAN_FRONTEND=noninteractive
apt-add-repository ppa:ansible/ansible
# aptコマンドのCLIインターフェイスは不安定らしい
apt-get update
apt-get install -y ansible git
apt-get full-upgrade -y
