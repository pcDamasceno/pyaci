import json
from packaging import version

def calc_pages(limit, count):
    """Calculate number of pages required for full results set."""
    return int(count / limit) + (limit % count > 0)

class RequestError(Exception):
    """Basic Request Exception.

    More detailed exception that returns the original requests object
    for inspection. Along with some attributes with specific details
    from the requests object. If return is json we decode and add it
    to the message.

    ## Examples

    ```python
    try:
        nb.dcim.devices.create(name="destined-for-failure")
    except pynetbox.RequestError as e:
        print(e.error)
    ```
    """

    def __init__(self, req):
        if req.status_code == 404:
            self.message = "The requested url: {} could not be found.".format(req.url)
        else:
            try:
                self.message = "The request failed with code {} {}: {}".format(
                    req.status_code, req.reason, req.json()
                )
            except ValueError:
                self.message = (
                    f"The request failed with code {req.status_code} {req.reason} but more specific "
                    "details were not returned in json. Check the ACI Logs "
                    "or investigate this exception's error attribute."
                )

        super().__init__(self.message)
        self.req = req
        self.request_body = req.request.body
        self.base = req.url
        self.error = req.text

    def __str__(self):
        return self.message

class ParameterValidationError(Exception):
    """API parameter validation Exception.

    Raised when filter parameters do not match Netbox OpenAPI specification.

    ## Examples

    ```python
    try:
        nb.dcim.devices.filter(field_which_does_not_exist="destined-for-failure")
    except pynetbox.ParameterValidationError as e:
        print(e.error)
    ```
    """

    def __init__(self, errors):
        super().__init__(errors)
        self.error = f"The request parameter validation returned an error: {errors}"

    def __str__(self):
        return self.error

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
        self.url = self.base if not key else f"{self.base}{key}/"
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
            raise RequestError(req)
        
    
    def get_version(self):
        """Gets the API version of ACI.

        Issues a GET request to the base URL to read the API version from the
        response headers.

        ## Returns
        Version number as a string. Empty string if version is not
        present in the headers.

        ## Raises
        RequestError if req.ok returns false.
        """
        headers = {
            "Content-Type": "application/json",
        }
        req = self.http_session.get(
            self.normalize_url(self.base),
            headers=headers,
        )
        if req.ok or req.status_code == 403:
            return req.headers.get("API-Version", "")
        else:
            raise RequestError(req)
        
    def normalize_url(self, url):
        """Builds a url for POST actions."""
        if url[-1] != "/":
            return f"{url}/"

        return url
    
    def _make_call(self, verb="get", url_override=None, add_params=None, data=None):
        if verb in ("post", "put") or verb == "delete" and data:
            headers = {"Content-Type": "application/json"}
        else:
            headers = {"accept": "application/json"}

        if self.token:
            headers["authorization"] = "Token {}".format(self.token)

        params = {}
        if not url_override:
            if self.filters:
                params.update(self.filters)
            if add_params:
                params.update(add_params)

        req = getattr(self.http_session, verb)(
            url_override or self.url, headers=headers, params=params, json=data
        )

        if req.status_code == 409 and verb == "post":
            raise AllocationError(req)
        if verb == "delete":
            if req.ok:
                return True
            else:
                raise RequestError(req)
        elif req.ok:
            try:
                return req.json()
            except json.JSONDecodeError:
                raise ContentError(req)
        else:
            raise RequestError(req)
        
    def get(self, add_params=None):
        """Makes a GET request.

        Makes a GET request to NetBox's API, and automatically recurses
        any paginated results.

        ## Returns
        List of `Response` objects returned from the endpoint.

        ## Raises
        * RequestError if req.ok returns false.
        * ContentError if response is not json.
        """

        if not add_params and self.limit is not None:
            add_params = {"limit": self.limit}
            if self.limit and self.offset is not None:
                # if non-zero limit and some offset -> add offset
                add_params["offset"] = self.offset
        req = self._make_call(add_params=add_params)
        if isinstance(req, dict) and req.get("results") is not None:
            self.count = req["count"]
            if self.offset is not None:
                # only yield requested page results if paginating
                for i in req["results"]:
                    yield i
            elif self.threading:
                ret = req["results"]
                if req.get("next"):
                    page_size = len(req["results"])
                    pages = calc_pages(page_size, req["count"])
                    page_offsets = [
                        increment * page_size for increment in range(1, pages)
                    ]
                    if pages == 1:
                        req = self._make_call(url_override=req.get("next"))
                        ret.extend(req["results"])
                    else:
                        self.concurrent_get(ret, page_size, page_offsets)
                for i in ret:
                    yield i
            else:
                first_run = True
                for i in req["results"]:
                    yield i
                while req["next"]:
                    # Not worrying about making sure add_params kwargs is
                    # passed in here because results from detail routes aren't
                    # paginated, thus far.
                    if first_run:
                        req = self._make_call(
                            add_params={
                                "limit": self.limit or req["count"],
                                "offset": len(req["results"]),
                            }
                        )
                    else:
                        req = self._make_call(url_override=req["next"])
                    first_run = False
                    for i in req["results"]:
                        yield i
        elif isinstance(req, list):
            self.count = len(req)
            for i in req:
                yield i
        else:
            self.count = len(req)
            yield req

    def put(self, data):
        """Makes PUT request.

        Makes a PUT request to NetBox's API.

        ## Parameters
        * **data** (dict): Contains a dict that will be turned into a
            json object and sent to the API.

        ## Returns
        Dict containing the response from NetBox's API.

        ## Raises
        * RequestError if req.ok returns false.
        * ContentError if response is not json.
        """
        return self._make_call(verb="put", data=data)

    def post(self, data):
        """Makes POST request.

        Makes a POST request to NetBox's API.

        ## Parameters
        * **data** (dict): Contains a dict that will be turned into a
            json object and sent to the API.

        ## Returns
        Dict containing the response from NetBox's API.

        ## Raises
        * RequestError if req.ok returns false.
        * AllocationError if req.status_code is 409 (Conflict)
            as with available-ips and available-prefixes when there is
            no room for the requested allocation.
        * ContentError if response is not json.
        """
        return self._make_call(verb="post", data=data)

    def delete(self, data=None):
        """Makes DELETE request.

        Makes a DELETE request to NetBox's API.

        ## Parameters
        * **data** (list): Contains a dict that will be turned into a
            json object and sent to the API.

        ## Returns
        True if successful.

        ## Raises
        RequestError if req.ok doesn't return True.
        """
        return self._make_call(verb="delete", data=data)

    def patch(self, data):
        """Makes PATCH request.

        Makes a PATCH request to NetBox's API.

        ## Parameters
        * **data** (dict): Contains a dict that will be turned into a
            json object and sent to the API.

        ## Returns
        Dict containing the response from NetBox's API.

        ## Raises
        * RequestError if req.ok returns false.
        * ContentError if response is not json.
        """
        return self._make_call(verb="patch", data=data)