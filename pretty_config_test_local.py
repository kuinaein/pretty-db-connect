#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import path
import logging

PRETTY_CONFIG = {
    'LOG_LEVEL': logging.DEBUG,
    'SSH_PORT': 23432,
    'DB_PORT': 34543,
    'SSH_KEY_PATH': path.join(
        path.dirname(__file__), '.vagrant/machines/default/virtualbox/private_key'),
    # 'RESOURCE_NAME': 'precon',
    'LOCAL': True,
    'SSH_USER': 'vagrant',
    'REMOTE_HOME': '/home/vagrant',
}
