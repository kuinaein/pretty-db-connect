#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logging import getLogger, basicConfig as loggingBasicConfig
import boto3
from os import path
import sys
from time import sleep
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


def ensure_vpc(pretty: PrettyDBConnect):
    vpc_res = pretty.ec2_client.describe_vpcs(
        Filters=[{'Name': 'tag:Name', 'Values': [pretty.name_base]}])
    if 1 == len(vpc_res['Vpcs']):
        return vpc_res['Vpcs'][0]['VpcId']
    elif 1 < len(vpc_res['Vpcs']):
        raise Exception('同名のVPCが2つ以上あります: ' + pretty.name_base)

    logger.info('VPCの作成中...')
    vpc_res = pretty.ec2_client.create_vpc(
        CidrBlock=PRETTY_CONFIG['VPC_CIDR_BLOCK'])
    vpc = pretty.ec2.Vpc(vpc_res['Vpc']['VpcId'])
    while 'available' != vpc.state:
        sleep(1)
        vpc.load()
    vpc.create_tags(Tags=pretty.name_tags)
    boto_first(vpc.network_acls).create_tags(Tags=pretty.name_tags)
    boto_first(vpc.route_tables).create_tags(Tags=pretty.name_tags)

    security_group = boto_first(vpc.security_groups)
    security_group.create_tags(Tags=pretty.name_tags)

    return vpc.id


def ensure_subnet(pretty: PrettyDBConnect, vpc_id: str):
    vpc = pretty.ec2.Vpc(vpc_id)
    if (0 < len(list(vpc.subnets.limit(count=1)))):
        return boto_first(vpc.subnets).id

    logger.info('サブネットの作成中...')
    subnet = vpc.create_subnet(CidrBlock=PRETTY_CONFIG['VPC_CIDR_BLOCK'])
    while 'available' != subnet.state:
        sleep(1)
        subnet.load()
    subnet.create_tags(Tags=pretty.name_tags)
    boto_first(vpc.route_tables).associate_with_subnet(SubnetId=subnet.id)
    return subnet.id


def ensure_internet_gateway(pretty: PrettyDBConnect, vpc_id: str):
    vpc = pretty.ec2.Vpc(vpc_id)
    if (0 < len(list(vpc.internet_gateways.limit(count=1)))):
        return

    logger.info('インターネットゲートウェイの作成中...')
    gateway_res = pretty.ec2_client.create_internet_gateway()
    gateway = pretty.ec2.InternetGateway(
        gateway_res['InternetGateway']['InternetGatewayId'])
    gateway.create_tags(Tags=pretty.name_tags)
    vpc.attach_internet_gateway(InternetGatewayId=gateway.id)
    gateway.load()
    while 'available' != gateway.attachments[0]['State']:
        sleep(1)
        gateway.load()
    boto_first(vpc.route_tables).create_route(
        DestinationCidrBlock='0.0.0.0/0', GatewayId=gateway.id)
    return gateway.id


def ensure_instance(pretty: PrettyDBConnect, subnet_id: str):
    inst_res = pretty.ec2_client.describe_instances(
        Filters=[{'Name': 'tag:Name', 'Values': [pretty.name_base]}])
    if 1 == len(inst_res['Reservations']):
        return inst_res['Reservations'][0]['Instances'][0]['InstanceId']
    if 1 < len(inst_res['Reservations']):
        raise Exception('同名のEC2インスタンスが2つ以上あります: ' + pretty.name_base)

    logger.info('EC2インスタンスの作成中...')
    ami_id = find_latest_ubuntu_ami(pretty)
    inst_res = pretty.ec2_client.run_instances(InstanceType='t2.micro', ImageId=ami_id, BlockDeviceMappings=[{
        'DeviceName': '/dev/sda1',
        'Ebs': {
            'DeleteOnTermination': True,
            'VolumeSize': PRETTY_CONFIG['VOLUME_SIZE'],
            'VolumeType': 'gp2',
        },
    }], NetworkInterfaces=[{
        'DeviceIndex': 0,
        'SubnetId': subnet_id,
        'AssociatePublicIpAddress': True,
    }], TagSpecifications=[
        {'ResourceType': 'instance', 'Tags': pretty.name_tags},
        {'ResourceType': 'volume', 'Tags': pretty.name_tags},
    ], KeyName=PRETTY_CONFIG['KEY_NAME'], MaxCount=1, MinCount=1, Monitoring={'Enabled': False})
    inst = pretty.ec2.Instance(inst_res['Instances'][0]['InstanceId'])
    while 16 > inst.state['Code']:  # 16 : running
        sleep(5)
        inst.load()
    inst.network_interfaces[0].create_tags(Tags=pretty.name_tags)
    return inst.id


def find_latest_ubuntu_ami(pretty: PrettyDBConnect):
    ami_res = pretty.ec2_client.describe_images(Owners=[PRETTY_CONFIG['AMI_OWNER']], Filters=[{
        'Name': 'name', 'Values': [PRETTY_CONFIG['AMI_NAME']]}])
    amis = ami_res['Images']
    amis = sorted(amis, key=lambda im: im['Name'])
    return amis[len(amis) - 1]['ImageId']


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
    pretty = PrettyDBConnect()
    vpc_id = ensure_vpc(pretty)
    subnet_id = ensure_subnet(pretty, vpc_id)
    ensure_internet_gateway(pretty, vpc_id)
    instance_id = ensure_instance(pretty, subnet_id)
    ssh_port = ensure_security_group(pretty, instance_id)

    ip = pretty.ec2.Instance(instance_id).public_ip_address
    ensure_ansible(ip, ssh_port)
