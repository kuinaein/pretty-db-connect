#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pretty_config.pyにコピーしてご利用ください。

import os
import logging

PRETTY_CONFIG = {
    'LOG_LEVEL': logging.INFO,
    'SSH_PORT': 23432,
    'DB_PORT': 34543,
    'SSH_KEY_PATH': os.path.expanduser('~/.ssh/id_rsa'),
    'RESOURCE_NAME': 'precon',
    'REMOTE_HOME': '/home/ubuntu',
}
