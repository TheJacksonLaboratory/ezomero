import configparser
import logging
import os
import functools
import inspect
from getpass import getpass
from omero.gateway import BlitzGateway
from pathlib import Path


def get_default_args(func):
    """Retrieves the default arguments of a function.

    Parameters
    ----------
    func : function
        Function whose signature we want to inspect

    Returns
    -------
    _ : dict
        Key-value pairs of argument name and value.
    """
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


def do_across_groups(f):
    """Decorator functional for making functions work across
    OMERO groups.

    Parameters
    ----------
    f : function
        Function that will be decorated

    Returns
    -------
    wrapper : Object
        Return value of the decorated function.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        defaults = get_default_args(f)
        do_across_groups = False
        # test if user is overriding default
        if 'across_groups' in kwargs:
            # if they are, respect user settings
            if kwargs['across_groups']:
                do_across_groups = True
        else:
            # else, respect default
            if defaults['across_groups']:
                do_across_groups = True
        if do_across_groups:
            current_group = args[0].getGroupFromContext().getId()
            args[0].SERVICE_OPTS.setOmeroGroup('-1')
            res = f(*args, **kwargs)
            set_group(args[0], current_group)
        else:
            res = f(*args, **kwargs)
        return res
    return wrapper


# puts
@do_across_groups
def put_map_annotation(conn, map_ann_id, kv_dict, ns=None, across_groups=True):
    """Update an existing map annotation with new values (kv pairs)

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    map_ann_id : int
        ID of map annotation whose values (kv pairs) will be replaced.
    kv_dict : dict
        New values (kv pairs) for the MapAnnotation.
    ns : str
        New namespace for the MapAnnotation. If left as None, the old
        namespace will be used.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Notes
    -----
    All keys and values are converted to strings before saving in OMERO.

    Returns
    -------
    Returns None.

    Examples
    --------
    # Change only the values of an existing map annotation:

    >>> new_values = {'testkey': 'testvalue', 'testkey2': 'testvalue2'}
    >>> put_map_annotation(conn, 15, new_values)

    # Change both the values and namespace of an existing map annotation:

    >>> put_map_annotation(conn, 16, new_values, 'test_v2')
    """
    if type(map_ann_id) is not int:
        raise TypeError('Map annotation ID must be an integer')

    map_ann = conn.getObject('MapAnnotation', map_ann_id)
    if map_ann is None:
        raise ValueError("MapAnnotation is non-existent or you do not have "
                         "permissions to change it.")

    if ns is None:
        ns = map_ann.getNs()
    map_ann.setNs(ns)

    kv_pairs = []
    for k, v in kv_dict.items():
        k = str(k)
        v = str(v)
        kv_pairs.append([k, v])
    map_ann.setValue(kv_pairs)
    map_ann.save()
    return None


# functions for managing connection context and service options.

def connect(user=None, password=None, group=None, host=None, port=None,
            secure=None, config_path=None):
    """Create an OMERO connection

    This function will create an OMERO connection by populating certain
    parameters for ``omero.gateway.BlitzGateway`` initialization by the
    procedure described in the notes below. Note that this function may
    ask for user input, so be cautious if using in the context of a script.

    Finally, don't forget to close the connection ``conn.close()`` when it
    is no longer needed!

    Parameters
    ----------
    user : str, optional
        OMERO username.

    password : str, optional
        OMERO password.

    group : str, optional
        OMERO group.

    host : str, optional
        OMERO.server host.

    port : int, optional
        OMERO port.

    secure : boolean, optional
        Whether to create a secure session.

    config_path : str, optional
        Path to directory containing '.ezomero' file that stores connection
        information. If left as ``None``, defaults to the home directory as
        determined by Python's ``pathlib``.

    Returns
    -------
    conn : ``omero.gateway.BlitzGateway`` object or None
        OMERO connection, if successful. Otherwise an error is logged and
        returns None.

    Notes
    -----
    The procedure for choosing parameters for ``omero.gateway.BlitzGateway``
    initialization is as follows:

    1) Any parameters given to `ezomero.connect` will be used to initialize
       ``omero.gateway.BlitzGateway``

    2) If a parameter is not given to `ezomero.connect`, populate from
       variables in ``os.environ``:
        * OMERO_USER
        * OMERO_PASS
        * OMERO_GROUP
        * OMERO_HOST
        * OMERO_PORT
        * OMERO_SECURE

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
        config_dict = config["DEFAULT"]

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

    # set group
    if group is None:
        group = config_dict.get("OMERO_GROUP", group)
        group = os.environ.get("OMERO_GROUP", group)
    if group is None:
        group = input('Enter group name (or leave blank for default group): ')
    if group == "":
        group = None

    # set host
    if host is None:
        host = config_dict.get("OMERO_HOST", host)
        host = os.environ.get("OMERO_HOST", host)
    if host is None:
        host = input('Enter host: ')

    # set port
    if port is None:
        port = config_dict.get("OMERO_PORT", port)
        port = os.environ.get("OMERO_PORT", port)
    if port is None:
        port = input('Enter port: ')
    port = int(port)

    # set session security
    if secure is None:
        secure = config_dict.get("OMERO_SECURE", secure)
        secure = os.environ.get("OMERO_SECURE", secure)
    if secure is None:
        secure = input('Secure session (True or False): ')
    if type(secure) is str:
        if secure.lower() in ["true", "t"]:
            secure = True
        elif secure.lower() in ["false", "f"]:
            secure = False
        else:
            raise ValueError('secure must be set to either True or False')

    # create connection
    conn = BlitzGateway(user, password, group=group, host=host, port=port,
                        secure=secure)
    if conn.connect():
        return conn
    else:
        logging.error('Could not connect, check your settings')
        return None


def store_connection_params(user=None, group=None, host=None, port=None,
                            secure=None, web_host=False, config_path=None):
    """Save OMERO connection parameters in a file.

    This function creates a config file ('.ezomero') in which
    certain OMERO parameters are stored, to make it easier to create
    ``omero.gateway.BlitzGateway`` objects.

    Parameters
    ----------
    user : str, optional
        OMERO username.

    group : str, optional
        OMERO group.

    host : str, optional
        OMERO.server host.

    port : int, optional
        OMERO port.

    secure : boolean, optional
        Whether to create a secure session.

    web_host : boolean/str, optional
        Whether to save a web host address got JSON connections as well. If
        `False`, will skip it; it `True`, will prompt user for it; if it is
        a `str`, will save that value to `OMERO_WEB_HOST`.

    config_path : str, optional
        Path to directory that will contain the '.ezomero' file. If left as
        ``None``, defaults to the home directory as determined by Python's
        ``pathlib``.
    """
    if config_path is None:
        config_path = Path.home()
    elif type(config_path) is str:
        config_path = Path(config_path)
    else:
        raise ValueError('config_path must be a string')

    if not config_path.is_dir():
        raise ValueError('config_path must point to a valid directory')
    ezo_file = config_path / '.ezomero'
    if ezo_file.exists():
        resp = input(f'{ezo_file} already exists. Overwrite? (Y/N)')
        if resp.lower() not in ['yes', 'y']:
            return

    # get parameters
    if user is None:
        user = input('Enter username: ')
    if group is None:
        group = input('Enter group name (or leave blank for default group): ')
    if host is None:
        host = input('Enter host: ')
    if port is None:
        port = input('Enter port: ')
    if secure is None:
        secure_str = input('Secure session (True or False): ')
        if secure_str.lower() in ["true", "t"]:
            secure = "True"
        elif secure_str.lower() in ["false", "f"]:
            secure = "False"
        else:
            raise ValueError('secure must be set to either True or False')
    if web_host is True:
        web_host = input('Enter web host: ')
    # make parameter dictionary and save as configfile
    # just use 'DEFAULT' for right now, we can possibly add alt configs later
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'OMERO_USER': user,
                         'OMERO_GROUP': group,
                         'OMERO_HOST': host,
                         'OMERO_PORT': port,
                         'OMERO_SECURE': secure}
    if web_host is not False:
        config['JSON'] = {'OMERO_USER': user,
                          'OMERO_WEB_HOST': web_host,
                          }
    with ezo_file.open('w') as configfile:
        config.write(configfile)
        print(f'Connection settings saved to {ezo_file}')


def set_group(conn, group_id):
    """Safely switch OMERO group.

    This function will change the user's current group to that specified by
    `group_id`, but only if the user is a member of that group. This is a
    "safer" way to do this than ``conn.SERVICE_OPTS.setOmeroGroup``, which will
    allow switching to a group that a user does not have permissions, which can
    lead to server-side errors.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    group_id : int
        The id of the group to switch to.

    Returns
    -------
    change_status : bool
        Returns `True` if group is changed, otherwise returns `False`.
    """
    if type(group_id) is not int:
        raise TypeError('Group ID must be an integer')

    user_id = conn.getUser().getId()
    g = conn.getObject("ExperimenterGroup", group_id)
    owners, members = g.groupSummary()
    owner_ids = [e.getId() for e in owners]
    member_ids = [e.getId() for e in members]
    if (user_id in owner_ids) or (user_id in member_ids):
        conn.SERVICE_OPTS.setOmeroGroup(group_id)
        return True
    else:
        logging.warning(f'User {user_id} is not a member of Group {group_id}')
        return False
