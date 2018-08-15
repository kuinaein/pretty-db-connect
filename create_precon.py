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
    security_group = list(vpc.security_groups.limit(count=1))[0]
    security_group.create_tags(Tags=pretty.name_tags)
    list(vpc.network_acls.limit(count=1))[0].create_tags(Tags=pretty.name_tags)
    list(vpc.route_tables.limit(count=1))[0].create_tags(Tags=pretty.name_tags)
    return vpc.id


if '__main__' == __name__:
    pretty = PrettyDBConnect()
    ensure_vpc(pretty)
