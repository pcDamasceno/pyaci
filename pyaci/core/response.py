import copy
from collections import OrderedDict

from pyaci.core.query import Request

class JsonField:
    """Explicit field type for values that are not to be converted
    to a Record object."""

    _json_field = True

class Record:
    """Create Python objects from ACI API responses.

    Creates an object from a ACI response passed as `values`.
    Nested dicts that represent other endpoints are also turned
    into Record objects. All fields are then assigned to the
    object's attributes. If a missing attr is requested
    (e.g. requesting a field that's only present on a full response on
    a Record made from a nested response) then pyACI will make a
    request for the full object and return the requested value.

    ## Examples

    Default representation of the object is usually its name:

    ```python
    x = aci.dcim.devices.get(1)
    x
    # test1-switch1
    ```

    Querying a string field:

    ```python
    x = aci.dcim.devices.get(1)
    x.serial
    # 'ABC123'
    ```

    Querying a field on a nested object:

    ```python
    x = aci.dcim.devices.get(1)
    x.device_type.model
    # 'QFX5100-24Q'
    ```

    Casting the object as a dictionary:

    ```python
    from pprint import pprint
    pprint(dict(x))
    {
        'asset_tag': None,
        'cluster': None,
        'comments': '',
        'config_context': {},
        'created': '2018-04-01',
        'custom_fields': {},
        'role': {
            'id': 1,
            'name': 'Test Switch',
            'slug': 'test-switch',
            'url': 'http://localhost:8000/api/dcim/device-roles/1/'
        },
        'device_type': {...},
        'display_name': 'test1-switch1',
        'face': {'label': 'Rear', 'value': 1},
        'id': 1,
        'name': 'test1-switch1',
        'parent_device': None,
        'platform': {...},
        'position': 1,
        'primary_ip': {
            'address': '192.0.2.1/24',
            'family': 4,
            'id': 1,
            'url': 'http://localhost:8000/api/ipam/ip-addresses/1/'
        },
        'primary_ip4': {...},
        'primary_ip6': None,
        'rack': {
            'display_name': 'Test Rack',
            'id': 1,
            'name': 'Test Rack',
            'url': 'http://localhost:8000/api/dcim/racks/1/'
        },
        'site': {
            'id': 1,
            'name': 'TEST',
            'slug': 'TEST',
            'url': 'http://localhost:8000/api/dcim/sites/1/'
        },
        'status': {'label': 'Active', 'value': 1},
        'tags': [],
        'tenant': None,
        'vc_position': None,
        'vc_priority': None,
        'virtual_chassis': None
    }
    ```

    Iterating over a Record object:

    ```python
    for i in x:
        print(i)

    # ('id', 1)
    # ('name', 'test1-switch1')
    # ('display_name', 'test1-switch1')
    ```
    """

    url = None

    def __init__(self, values, api, endpoint):
        self.has_details = False
        self._full_cache = []
        self._init_cache = []
        self.api = api
        self.default_ret = Record
        self.endpoint = (
            self._endpoint_from_url(values["url"])
            if values and "url" in values and values["url"]
            else endpoint
        )
        if values:
            self._parse_values(values)