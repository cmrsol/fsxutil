"""
The command line interface to stackility.

Major help from: https://www.youtube.com/watch?v=kNke39OZ2k0
"""
import json    # noqa
import time    # noqa
import logging # noqa
import sys     # noqa
import os      # noqa
import boto3   # noqa
import click
from fsxutil.utility import init_boto3_clients
from fsxutil.fsxsz import calc_size

MAX_FSX_SIZE = 16

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s (%(module)s) %(message)s',
    datefmt='%Y/%m/%d-%H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
nap_time = 60
subnets_key = '/ngsa/fsx/private-subnet-csv'
security_group_key = '/ngsa/fsx/security-group'

services = [
    'fsx',
    'ssm',
    'ec2'
]

COMPLETED_STATES = [
    'AVAILABLE',
    'FAILED',
    'MISCONFIGURED'
]


@click.group()
@click.version_option(version='0.0.1')
def cli():
    """
    A utility for creating and deleting FSx things.
    """
    pass


@cli.command()
@click.option('--name', '-n', help='file system name', required=True)
@click.option('--size', '-s', help='file system size in TB', required=True, type=int)
@click.option('--input', '-i', help='S3 input data path', required=True)
@click.option('--output', '-o', help='S3 output data path', required=True)
@click.option('--profile', '-p', help='AWS security profile')
@click.option('--region', '-r', help='AWS region')
def create(name, size, input, output, profile, region):
    """
    Create an FSx
    """
    if size > MAX_FSX_SIZE:
        logger.error('can not create FXx larger than %s TB', MAX_FSX_SIZE)
        sys.exit(1)

    clients = init_boto3_clients(services, profile=profile, region=region)
    try:
        create_file_system(name, size, input, output, clients)
    except Exception as wtf:
        logger.error(wtf, exc_info=True)


@cli.command()
@click.option('--id', '-i', help='ID of the file system to be deleted', required=True)
@click.option('--profile', '-p', help='AWS security profile')
@click.option('--region', '-r', help='AWS region')
def delete(id, profile, region):
    """
    Delete an FSx
    """
    try:
        logger.info('delete called() id=%s', id)
        delete_file_system(id, profile, region)
    except Exception as wtf:
        logger.error(wtf, exc_info=True)


@cli.command()
@click.option('--id', '-i', help='ID of the file system to be deleted', required=True)
def list_addresses(id):
    """
    Describe an FSx
    """
    try:
        logger.info('list_addresses called() id=%s', id)
        list_addresses_worker(id)
    except Exception as wtf:
        logger.error(wtf, exc_info=True)


def delete_file_system(fs_id, profile, region):
    clients = init_boto3_clients(services, profile=profile, region=region)
    try:
        fsx_client = clients.get('fsx', None)
        response = fsx_client.delete_file_system(FileSystemId=fs_id)

        while True:
            try:
                time.sleep(nap_time)
                response = fsx_client.describe_file_systems(
                    FileSystemIds=[fs_id],
                    MaxResults=1
                )
            except Exception as no_panic:
                logger.info(no_panic, exc_info=False)
                logger.info('%s is probably gone', fs_id)
                break

            if len(response.get('FileSystems', [])) == 0:
                logger.info('%s is gone', fs_id)
                break
            else:
                status = response.get('FileSystems')[0].get('Lifecycle')
                logger.info('%s in state %s', fs_id, status)
    except Exception as wtf:
        logger.error(wtf, exc_info=False)


def list_addresses_worker(fs_id):
    clients = init_boto3_clients(services)
    try:
        fsx_client = clients.get('fsx', None)
        ec2_client = clients.get('ec2', None)
        response = fsx_client.describe_file_systems(
            FileSystemIds=[fs_id],
            MaxResults=1
        )
        dns_name = response.get('FileSystems')[0].get('DNSName')
        logger.info('DNS Name: %s', dns_name)
        enis = response.get('FileSystems')[0].get('NetworkInterfaceIds')
        response = ec2_client.describe_network_interfaces(NetworkInterfaceIds=enis)
        for eni in response.get('NetworkInterfaces', []):
            logger.info('addr: %s', eni.get('PrivateIpAddress'))
            print(eni.get('PrivateIpAddress'))
    except Exception as wtf:
        logger.error(wtf, exc_info=True)


def create_file_system(name, size, input, output, clients):
    try:
        ssm_client = clients.get('ssm', None)
        fsx_client = clients.get('fsx', None)

        response = ssm_client.get_parameter(Name=subnets_key, WithDecryption=True)
        wrk = response.get('Parameter', {}).get('Value', None)
        subnets = wrk.split(',')
        logger.info(subnets)

        response = ssm_client.get_parameter(Name=security_group_key, WithDecryption=True)
        wrk = response.get('Parameter', {}).get('Value', None)
        security_groups = wrk.split(',')
        logger.info(security_groups)

        logger.info('starting FSx with size %s GB', calc_size(size))
        response = fsx_client.create_file_system(
            FileSystemType='LUSTRE',
            SubnetIds=[subnets[0]],
            StorageCapacity=calc_size(size),
            SecurityGroupIds=security_groups,
            Tags=[{
                'Key': 'Name',
                'Value': name
            }],
            LustreConfiguration={
                'WeeklyMaintenanceStartTime': '2:20:30',
                'ImportPath': input,
                'ExportPath': output
            }
        )

        fs_id = response.get('FileSystem', {}).get('FileSystemId')
        status = response.get('FileSystem', {}).get('Lifecycle')
        logger.info('%s in state %s', fs_id, status)

        start = int(time.time())
        while status and status not in COMPLETED_STATES:
            time.sleep(nap_time)
            response = fsx_client.describe_file_systems(
                FileSystemIds=[fs_id],
                MaxResults=1
            )
            status = response.get('FileSystems')[0].get('Lifecycle')
            dns_name = response.get('FileSystems')[0].get('DNSName')
            logger.info('%s in state %s', fs_id, status)

        finish = int(time.time())
        logger.info('%s finished in state %s in %s seconds', fs_id, status, (finish-start))
        logger.info('DNS Name: %s', dns_name)
        logger.info('mount command:')
        print(f'sudo mount -t lustre -o noatime,flock {dns_name}@tcp:/fsx /fsx')
    except Exception as wtf:
        logger.error(wtf, exc_info=True)


def find_myself():
    """
    Find myself

    Args:
        None

    Returns:
       An Amazon region
    """
    s = boto3.session.Session()
    return s.region_name
