import json
from packaging import version

class Request:
    """Creates requests to the ACI API.

    Responsible for building the url and making the HTTP(S) requests to
    ACI's API.

    ## Parameters

    * **base** (str): Base URL passed in api() instantiation.
    * **filters** (dict, optional): Contains key/value pairs that
        correlate to the filters a given endpoint accepts.
        In (e.g. /api/dcim/devices/?name='test') 'name': 'test'
        would be in the filters dict.
    """

    def __init__(
        self,
        base,
        http_session,
        filters=None,
        limit=None,
        offset=None,
        key=None,
        token=None,
        threading=False,
    ):
        """Instantiates a new Request object.

        ## Parameters

        * **base** (string): Base URL passed in api() instantiation.
        * **filters** (dict, optional): Contains key/value pairs that
            correlate to the filters a given endpoint accepts.
            In (e.g. /api/dcim/devices/?name='test') 'name': 'test'
            would be in the filters dict.
        * **key** (int, optional): Database id of the item being queried.
        """
        self.base = self.normalize_url(base)
        self.filters = filters or None
        self.key = key
        self.token = token
        self.http_session = http_session
        self.url = self.base if not key else "{}{}/".format(self.base, key)
        self.threading = threading
        self.limit = limit
        self.offset = offset
    def get_openapi(self):
        """Gets the OpenAPI Spec."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        current_version = version.parse(self.get_version())
        if current_version >= version.parse("3.5"):
            req = self.http_session.get(
                "{}schema/".format(self.normalize_url(self.base)),
                headers=headers,
            )
        else:
            req = self.http_session.get(
                "{}docs/?format=openapi".format(self.normalize_url(self.base)),
                headers=headers,
            )

        if req.ok:
            return req.json()
        else:
            raise Exception(req.text)