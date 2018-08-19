#!/usr/bin/env bash
set -eu

export DEBIAN_FRONTEND=noninteractive
apt-add-repository -y ppa:ansible/ansible
# aptコマンドのCLIインターフェイスは不安定らしい
apt-get update -y
apt-get install -y ansible
apt-get full-upgrade -y
