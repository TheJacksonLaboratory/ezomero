import requests
import os
import configparser
import numpy as np
from numbers import Number
from getpass import getpass
from pathlib import Path
from PIL import Image
from io import BytesIO


def create_json_session(user=None, password=None, web_host=None,
                        verify=True, server_name='omero',
                        config_path=None):
    """Create an OMERO connection using the JSON API

    This function will create an OMERO connection by populating certain
    parameters for a request using the ``requests`` library by the
    procedure described in the notes below. Note that this function may
    ask for user input, so be cautious if using in the context of a script.

    Parameters
    ----------
    user : str, optional
        OMERO username.

    password : str, optional
        OMERO password.

    web_host : str, optional
        OMERO.web host.

    verify : boolean, optional
        Whether to verify SSL certificates when making requests.

    server_name : str, optional
        OMERO server name as configured in your OMERO.web installation. For
        a "default" OMERO.web installation, it will normally be 'omero'.

    config_path : str, optional
        Path to directory containing '.ezomero' file that stores connection
        information. If left as ``None``, defaults to the home directory as
        determined by Python's ``pathlib``.

    Returns
    -------
    login_rsp : JSON object
        JSON containing the response to the ``POST`` request sent for log in.

    session : ``requests`` Session object or None
        The effective ``requests`` session that will be used for further
        requests to the JSON API.

    base_url : str or None
        Base URL for further requests, retrieved via JSON API request

    Notes
    -----
    The procedure for choosing parameters for initializing a JSON API session
    is as follows:

    1) Any parameters given to `create_json_connection` will be used to
       initialize a JSON session

    2) If a parameter is not given to this function, populate from variables
       in ``os.environ``:
        * OMERO_USER
        * OMERO_PASS
        * OMERO_WEB_HOST

    3) If environment variables are not set, try to load from a config file.
       This file should be called '.ezomero'. By default, this function will
       look in the home directory, but ``config_path`` can be used to specify
       a directory in which to look for '.ezomero'.

       The function ``ezomero.store_connection_params`` can be used to create
       the '.ezomero' file.

       Note that passwords can not be loaded from the '.ezomero' file. This is
       to discourage storing credentials in a file as cleartext.

    4) If any remaining parameters have not been set by the above steps, the
       user is prompted to enter a value for each unset parameter.

    Note that, by default, this function will use the latest API version
    available, in case multiple versions are offered by the OMERO.web server.
    """
    # load from .ezomero config file if it exists
    if config_path is None:
        config_fp = Path.home() / '.ezomero'
    elif type(config_path) is str:
        config_fp = Path(config_path) / '.ezomero'
    else:
        raise TypeError('config_path must be a string')

    config_dict = {}
    if config_fp.exists():
        config = configparser.ConfigParser()
        with config_fp.open() as fp:
            config.read_file(fp)
        try:
            config_dict = config["JSON"]
        except KeyError:
            raise KeyError('.ezomero does not contain JSON information.')

    # set user
    if user is None:
        user = config_dict.get("OMERO_USER", user)
        user = os.environ.get("OMERO_USER", user)
    if user is None:
        user = input('Enter username: ')

    # set password
    if password is None:
        password = os.environ.get("OMERO_PASS", password)
    if password is None:
        password = getpass('Enter password: ')

    # set web host
    if web_host is None:
        web_host = config_dict.get("OMERO_WEB_HOST", web_host)
        web_host = os.environ.get("OMERO_WEB_HOST", web_host)
    if web_host is None:
        web_host = input('Enter host: ')

    session = requests.Session()
    # Start by getting supported versions from the base url...
    api_url = '%s/api/' % web_host
    r = session.get(api_url, verify=verify)
    # we get a list of versions
    versions = r.json()['data']
    # use most recent version...
    version = versions[-1]
    # get the 'base' url
    base_url = version['url:base']
    r = session.get(base_url)
    # which lists a bunch of urls as starting points
    urls = r.json()
    servers_url = urls['url:servers']
    login_url = urls['url:login']

    # To login we need to get CSRF token
    token_url = urls['url:token']
    token = session.get(token_url).json()['data']
    # We add this to our session header
    # Needed for all POST, PUT, DELETE requests
    session.headers.update({'X-CSRFToken': token,
                            'Referer': login_url})

    # List the servers available to connect to
    servers = session.get(servers_url).json()['data']
    servers = [s for s in servers if s['server'] == server_name]
    if len(servers) < 1:
        raise Exception("Found no server called '%s'" % server_name)
    server = servers[0]

    # Login with username, password and token
    payload = {'username': user,
               'password': password,
               # Using CSRFToken in header
               'server': server['id']}

    r = session.post(login_url, data=payload)
    login_rsp = r.json()
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Whoops it wasn't a 200
        print("Error {}".format(e))
        raise
    assert login_rsp['success']

    # Can get our 'default' group

    return login_rsp, session, base_url


def get_rendered_jpeg(session, base_url, img_id, scale):
    """Get a numpy array from a rendered JPEG at given scale factor
    of an image.

    Parameters
    ----------
    session : ``requests`` Session object
        ``requests`` session that has been initialized with login parameters.
    base_url : str
        Base URL for further requests, retrieved via JSON API request
    img_id : int
        ID of ``Image``.
    scale : float or int
        Scaling factor for the returned JPEG. ``1`` returns original size,
        ``2`` scales each dimension down by half, and so on.

    Returns
    -------
    pixels : ndarray
        Array containing pixel values from rendered JPEG of the OMERO image.

    Examples
    --------
    # Get a JPEG of an entire image as a numpy array:

    >>> jpeg_array = get_rendered_jpeg(session, base_url, 314, 1)

    """
    if not isinstance(session, requests.sessions.Session):
        raise TypeError('session must is a Requests session object')
    if type(base_url) is not str:
        raise TypeError('base_url must be a string')
    if type(img_id) is not int:
        raise TypeError('img_id must be an int')
    if not isinstance(scale, Number):
        raise TypeError('scale must be a number')
    # magical code for correct address from the json api session and image id
    r = session.get(base_url)
    try:
        r.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        # Whoops it wasn't a 200
        print("Error {}: received response {} with content: \
                         {}".format(e, r.status_code, r.content))
        raise
    host = base_url.split("/api")[0]
    # which lists a bunch of urls as starting points
    urls = r.json()
    images_url = urls['url:images']
    single_image_url = images_url+str(img_id)+"/"
    surl = session.get(single_image_url)
    try:
        surl.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Whoops it wasn't a 200
        print("Error {}: received response {} \
                         ".format(e, surl.status_code))
        raise
    # calculate width to be requested
    thisjson = surl.json()
    width = int(thisjson['data']['Pixels']['SizeX'])
    scaled = round(width/scale)
    img_address = host + "/webgateway/render_birds_eye_view/" + \
        str(img_id)+"/"+str(scaled)+"/"
    jpeg = session.get(img_address, stream=True)
    try:
        jpeg.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Whoops it wasn't a 200
        print("Error {}: received response {} with content: \
                         {}".format(e, jpeg.status_code, jpeg.content))
        raise

    # using PIL and BytesIO to open the request content as an image
    i = Image.open(BytesIO(jpeg.content))
    jpeg.close()
    return np.array(i)
