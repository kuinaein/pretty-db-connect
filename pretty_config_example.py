#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pretty_config.pyにコピーしてご利用ください。

from os import path
import logging

PRETTY_CONFIG = {
    'LOG_LEVEL': logging.INFO,
    'SSH_PORT': 23432,
    'DB_PORT': 34543,
    'DB_USER': 'postgres',
    # 要設定
    'DB_PASSWORD': None,
    'SSH_KEY_PATH': path.expanduser('~/.ssh/id_rsa'),
    'RESOURCE_NAME': 'precon',
    'SSH_USER': 'ubuntu',
    'REMOTE_HOME': '/home/ubuntu',
}
