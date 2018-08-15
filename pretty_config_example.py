#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pretty_config.pyにコピーしてご利用ください。

import os
import logging

PRETTY_CONFIG = {
    'LOG_LEVEL': logging.INFO,
    'KEY_NAME': '',
    'SSH_PORT': 23432,
    'DB_PORT': 34543,
    'SSH_KEY_PATH': os.path.expanduser('~/.ssh/id_rsa'),
    'RESOURCE_NAME_BASE': 'precon',
    'AMI_OWNER': '099720109477',
    'AMI_NAME': 'ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*',
    'VOLUME_SIZE': 20,
    'VPC_CIDR_BLOCK': '192.168.128.0/24',
}
