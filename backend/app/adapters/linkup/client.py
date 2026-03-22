from linkup import LinkupClient

from config import settings


def get_client() -> LinkupClient:
    return LinkupClient(api_key=settings.linkup_api_key)
