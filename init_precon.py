#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logging import getLogger, basicConfig as loggingBasicConfig
import boto3
from paramiko import SSHClient, AutoAddPolicy
from importlib import import_module
from sys import exit
import os
from os import path
import errno
from argparse import ArgumentParser
import urllib.request

from pretty_common import ssh_exec


logger = getLogger(__name__)
PRETTY_CONFIG = None


def init_arg_parser():
    arg_parser = ArgumentParser(
        usage='python {} [-c <config_name>] [-h]'.format(path.basename(__file__)))
    arg_parser.add_argument('-c', '--config', type=str,
                            dest='config_name', default='pretty_config',
                            help='default: pretty_config')
    return arg_parser


def get_instance(ec2_client, ec2):
    inst_res = ec2_client.describe_instances(
        Filters=[{'Name': 'tag:Name', 'Values': [PRETTY_CONFIG['RESOURCE_NAME']]}])
    if ('Reservations' not in inst_res) or (0 == len(inst_res['Reservations'])):
        raise Exception('EC2インスタンスが見つかりません')
    if 1 < len(inst_res['Reservations']):
        raise Exception('同名のEC2インスタンスが2つ以上あります: ' +
                        PRETTY_CONFIG['RESOURCE_NAME'])
    return ec2.Instance(
        inst_res['Reservations'][0]['Instances'][0]['InstanceId'])


def ensure_security_group(ec2_client, ec2, instance, my_ip: str):
    security_group = None
    for sg_desc in instance.security_groups:
        sg = ec2.SecurityGroup(sg_desc['GroupId'])
        matched = False
        for tag in sg.tags:
            if 'Name' == tag['Key'] and PRETTY_CONFIG['RESOURCE_NAME'] == tag['Value']:
                matched = True
                break
        if matched:
            security_group = sg
            break
    if security_group is None:
        raise Exception('セキュリティグループ {} が見つかりません'.format(
            PRETTY_CONFIG['RESOURCE_NAME']))

    my_cidr = my_ip + '/32'

    for perm in security_group.ip_permissions:
        if PRETTY_CONFIG['SSH_PORT'] != perm['FromPort'] and PRETTY_CONFIG['DB_PORT'] != perm['FromPort']:
            continue
        cur_cidr = perm['IpRanges'][0]['CidrIp']
        if my_cidr != cur_cidr:
            security_group.revoke_ingress(IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': perm['FromPort'], 'ToPort': perm['ToPort'],
                'IpRanges': [{'CidrIp': cur_cidr}]
            }])
            security_group.authorize_ingress(IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': perm['FromPort'], 'ToPort': perm['ToPort'],
                'IpRanges': [{
                    'CidrIp': my_cidr,
                    'Description': perm['IpRanges'][0]['Description'],
                }]
            }])

    logger.info('SSHポート22番を「{}」に開放します'.format(my_cidr))
    security_group.authorize_ingress(IpPermissions=[{
        'IpProtocol': 'tcp',
        'FromPort': 22, 'ToPort': 22,
        'IpRanges': [{'CidrIp': my_cidr, 'Description': 'myIP-SSH'}]
    }])


def clean_security_group(ec2_client, ec2, instance, my_ip: str):
    security_group = ec2.SecurityGroup(instance.security_groups[0]['GroupId'])
    security_group.revoke_ingress(IpPermissions=[{
        'IpProtocol': 'tcp',
        'FromPort': 22, 'ToPort': 22,
        'IpRanges': [{'CidrIp': my_ip + '/32', 'Description': 'myIP-SSH'}]
    }])
    logger.info('SSHポート22番を封鎖しました')


def init_instance(ip: str):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    try:
        ssh.connect(ip, 22, PRETTY_CONFIG['SSH_USER'],
                    timeout=10,
                    key_filename=PRETTY_CONFIG['SSH_KEY_PATH'])
    except Exception as ex:
        logger.error(ex)
        logger.error('ポート{}番に再接続します'.format(PRETTY_CONFIG['SSH_PORT']))
        ssh.connect(ip, PRETTY_CONFIG['SSH_PORT'], PRETTY_CONFIG['SSH_USER'],
                    timeout=10,
                    key_filename=PRETTY_CONFIG['SSH_KEY_PATH'])
    try:
        ensure_ansible(ssh)
        do_ansible(ssh)
    finally:
        ssh.close()


def ensure_ansible(ssh: SSHClient):
    stdout = ssh.exec_command('which ansible')[1]
    ansible_path = stdout.read().decode('utf-8')
    if '' != ansible_path:
        logger.info('Ansibleのパス: ' + ansible_path)
        return

    logger.info('Ansibleセットアップ中...')
    script_dir = path.dirname(path.abspath(__file__))
    sftp = ssh.open_sftp()
    try:
        remote_sh = PRETTY_CONFIG['REMOTE_HOME'] + '/pre-setup.sh'
        sftp.put(path.join(script_dir, 'pre-setup.sh'), remote_sh)
    finally:
        sftp.close()
    ssh_exec(ssh, 'sudo bash ' + remote_sh)


def do_ansible(ssh: SSHClient):
    script_dir = path.dirname(path.abspath(__file__))
    ansible_dir = path.join(script_dir, 'ansible')
    remote_ansible_dir = PRETTY_CONFIG['REMOTE_HOME'] + '/ansible'

    sftp = ssh.open_sftp()
    try:
        try:
            sftp.stat(remote_ansible_dir)
            ssh_exec(ssh, 'rm -rf ' + remote_ansible_dir)
        except IOError as ex:
            if errno.ENOENT != ex.errno:
                raise ex
            logger.debug(ex)
        sftp.mkdir(remote_ansible_dir, 0o755)
        # どうやら paramiko には再帰コピー機能がないようなので地道にコピー
        for fname in os.listdir(ansible_dir):
            sftp.put(path.join(ansible_dir, fname),
                     remote_ansible_dir + '/' + fname)
    finally:
        sftp.close()

    logger.info('リモートサーバ上でAnsibleを実行します')
    ssh_exec(ssh, 'ansible-playbook -i {inv} -e ssh_port={ssh} -e db_port={db} {book}'.format(
        inv=remote_ansible_dir + '/hosts.yml',
        book=remote_ansible_dir + '/db.yml',
        ssh=PRETTY_CONFIG['SSH_PORT'],
        db=PRETTY_CONFIG['DB_PORT'],
    ))


if '__main__' == __name__:
    arg_parser = init_arg_parser()
    args = arg_parser.parse_args()
    PRETTY_CONFIG = import_module(args.config_name).PRETTY_CONFIG
    loggingBasicConfig(level=PRETTY_CONFIG['LOG_LEVEL'])

    if PRETTY_CONFIG.get('LOCAL', False):
        init_instance('127.0.0.1')
        exit(0)

    my_ip = ''
    with urllib.request.urlopen('https://api.ipify.org') as response:
        my_ip = response.read().decode('ascii')
    logger.info('接続元IPアドレス: ' + my_ip)

    ec2_client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')
    instance = get_instance(ec2_client, ec2)
    ensure_security_group(ec2_client, ec2, instance, my_ip)
    try:
        logger.info('接続先IPアドレス: ' + instance.public_ip_address)
        init_instance(instance.public_ip_address)
    finally:
        clean_security_group(ec2_client, ec2, instance, my_ip)
