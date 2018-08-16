#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logging import getLogger, basicConfig as loggingBasicConfig
import boto3
from os import path
import urllib.request
from paramiko import SSHClient, AutoAddPolicy

from pretty_config import PRETTY_CONFIG

loggingBasicConfig(level=PRETTY_CONFIG['LOG_LEVEL'])
logger = getLogger(__name__)


class PrettyDBConnect:
    def __init__(self):
        self.name_base = PRETTY_CONFIG['RESOURCE_NAME_BASE']
        self.ec2_client = boto3.client('ec2')
        self.ec2 = boto3.resource('ec2')
        self.name_tags = [{'Key': 'Name', 'Value': self.name_base}]


def boto_first(collection):
    return list(collection.limit(count=1))[0]


def ensure_security_group(pretty: PrettyDBConnect, instance_id: str):
    my_ip = ''
    with urllib.request.urlopen('https://api.ipify.org') as response:
        my_ip = response.read().decode('ascii')

    ssh_opened = False
    another_ssh_opened = False

    inst = pretty.ec2.Instance(instance_id)
    security_group = pretty.ec2.SecurityGroup(
        inst.security_groups[0]['GroupId'])
    for perm in security_group.ip_permissions:
        if 'FromPort' in perm and perm['FromPort'] <= 22 and 22 <= perm['ToPort']:
            ssh_opened = True
            continue
        if 'FromPort' in perm and perm['FromPort'] <= PRETTY_CONFIG['SSH_PORT'] \
                and PRETTY_CONFIG['SSH_PORT'] <= perm['ToPort']:
            another_ssh_opened = True
            continue

    if another_ssh_opened:
        return PRETTY_CONFIG['SSH_PORT']
    if not ssh_opened:
        logger.info('SSHポート22番を「' + my_ip + '/32」に開放します')
        security_group.authorize_ingress(IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 22, 'ToPort': 22,
            'IpRanges': [{'CidrIp': my_ip + '/32', 'Description': 'myIP-SSH'}]
        }])
    return 22


def ensure_ansible(ip: str, ssh_port: int):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(ip, ssh_port, 'ubuntu',
                key_filename=PRETTY_CONFIG['SSH_KEY_PATH'])
    try:
        stdout = ssh.exec_command('which ansible')[1]
        ansible_path = stdout.read().decode('utf-8')
        if '' != ansible_path:
            logger.info('Ansibleのパス: ' + ansible_path)
            return

        logger.info('Ansibleセットアップ中...')
        script_dir = path.dirname(path.abspath(__file__))
        sftp = ssh.open_sftp()
        try:
            sftp.put(path.join(script_dir, 'pre-setup.sh'),
                     '/home/ubuntu/pre-setup.sh')
            ssh_exec(ssh, 'sudo bash /home/ubuntu/pre-setup.sh')
        finally:
            sftp.close()
    finally:
        ssh.close()


def ssh_exec(ssh: SSHClient, cmd: str):
    stdout, stderr = ssh.exec_command(cmd)[1:3]
    buf = stdout.read().decode('utf-8')
    logger.debug(buf)
    print(buf)
    err_msg = stderr.read().decode('utf-8')
    if '' != err_msg:
        raise Exception('サーバ上でエラー発生: ' + err_msg)
    return buf


if '__main__' == __name__:
    # FIXME
    pretty = PrettyDBConnect()
    ssh_port = ensure_security_group(pretty, instance_id)

    ip = pretty.ec2.Instance(instance_id).public_ip_address
    ensure_ansible(ip, ssh_port)
