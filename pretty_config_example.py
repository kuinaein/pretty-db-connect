#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# config.pyにコピーしてご利用ください。

import logging

PRETTY_CONFIG = {
    'LOG_LEVEL': logging.INFO,
    'KEY_NAME': '',
    'RESOURCE_NAME_BASE': 'precon',
    'AMI_OWNER': '099720109477',
    'AMI_NAME': 'ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*',
    'VOLUME_SIZE': 20,
    'VPC_CIDR_BLOCK': '192.168.128.0/24',
}
