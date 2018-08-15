#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logging import getLogger, basicConfig as loggingBasicConfig
import boto3
import sys
from time import sleep

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
    boto_first(vpc.security_groups).create_tags(Tags=pretty.name_tags)
    boto_first(vpc.network_acls).create_tags(Tags=pretty.name_tags)
    boto_first(vpc.route_tables).create_tags(Tags=pretty.name_tags)
    return vpc.id


def ensure_subnet(pretty: PrettyDBConnect, vpc_id: str):
    vpc = pretty.ec2.Vpc(vpc_id)
    if (0 < len(list(vpc.subnets.limit(count=1)))):
        return

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


if '__main__' == __name__:
    pretty = PrettyDBConnect()
    vpc_id = ensure_vpc(pretty)
    ensure_subnet(pretty, vpc_id)
    ensure_internet_gateway(pretty, vpc_id)
