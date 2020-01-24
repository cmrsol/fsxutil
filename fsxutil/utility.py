import logging
import boto3

logger = logging.getLogger(__name__)


def init_boto3_clients(services, **kwargs):
    """
    Creates boto3 clients

    Args:
        profile - CLI profile to use
        region - where do you want the clients

    Returns:
        Good or Bad; True or False
    """
    try:
        profile = kwargs.get('profile', None)
        region = kwargs.get('region', None)
        clients = {}
        session = None
        if profile and region:
            session = boto3.session.Session(profile_name=profile, region_name=region)
        elif profile:
            session = boto3.session.Session(profile_name=profile)
        elif region:
            session = boto3.session.Session(region_name=region)
        else:
            session = boto3.session.Session()

        for svc in services:
            clients[svc] = session.client(svc)

        return clients
    except Exception as wtf:
        logger.error(wtf, exc_info=True)
        return None
