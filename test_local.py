#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Callable
from logging import getLogger, basicConfig as loggingBasicConfig, DEBUG
import subprocess
import os
from copy import deepcopy
from time import sleep
import csv
from paramiko import SSHClient, AutoAddPolicy
import psycopg2

from pretty_config_test_local import PRETTY_CONFIG
from pretty_common import ssh_exec


logger = getLogger(__name__)
loggingBasicConfig(level=DEBUG)


def test_connect():
    ssh_do(PRETTY_CONFIG['SSH_PORT'],
           lambda ssh: ssh_exec(ssh, 'echo hello, world!'))
    logger.info('SSH接続テスト: OK')
    db_conn = psycopg2.connect(
        host='127.0.0.1', port=PRETTY_CONFIG['DB_PORT'],
        user=PRETTY_CONFIG['DB_USER'], password=PRETTY_CONFIG['DB_PASSWORD'])
    try:
        cur = db_conn.cursor()
        try:
            cur.execute('SELECT 1')
            (res,) = cur.fetchone()
            logger.debug('実際の値: ' + str(res))
            assert 1 == res
        finally:
            cur.close()
    finally:
        db_conn.close()
    logger.info('DB接続テスト: OK')


def ssh_do(port: int, block: Callable[[SSHClient], None]):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect('127.0.0.1', port, PRETTY_CONFIG['SSH_USER'],
                key_filename=PRETTY_CONFIG['SSH_KEY_PATH'])
    try:
        block(ssh)
    finally:
        ssh.close()


def shutdown_by_ssh():
    ssh_do(3432, lambda ssh: ssh_exec(ssh, 'sudo shutdown now'))
    sleep(10)
    while True:
        res = subprocess.run(('vagrant', 'status', '--machine-readable'),
                             check=True, stdout=subprocess.PIPE)
        csv_data = res.stdout.decode('utf-8').strip().splitlines()
        status_row = next(filter(lambda row: 'state' == row[2],
                                 csv.reader(csv_data)))
        if 'poweroff' == status_row[3]:
            break
        sleep(1)


if '__main__' == __name__:
    old_cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(__file__))
        os.environ['GUEST_SSH_PORT'] = '22'
        subprocess.run(('vagrant', 'up'), check=True)
        try:
            subprocess.run(('python', './init_precon.py', '-c',
                            'pretty_config_test_local'), check=True)

            # SSHのポートが変わっているはずなので、vagrantからはコントロール効かないはず
            # subprocess.run(('vagrant', 'halt'), check=True)
            shutdown_by_ssh()

            os.environ.pop('GUEST_SSH_PORT')
            subprocess.run(('vagrant', 'up'), check=True)

            test_connect()
        finally:
            subprocess.run(('vagrant', 'destroy'), check=True)
    finally:
        os.chdir(old_cwd)
