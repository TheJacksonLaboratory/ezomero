import os
import pytest
import numpy as np
from datetime import datetime
import ezomero
from omero.cli import CLI
from omero.gateway import BlitzGateway
from omero.gateway import ScreenWrapper, PlateWrapper
from omero.model import ScreenI, PlateI, WellI, WellSampleI, ImageI
from omero.model import ScreenPlateLinkI
from omero.plugins.sessions import SessionsControl
from omero.plugins.user import UserControl
from omero.plugins.group import GroupControl
from omero.rtypes import rint, rstring

# Settings for OMERO
DEFAULT_OMERO_USER = "root"
DEFAULT_OMERO_PASS = "omero"
DEFAULT_OMERO_HOST = "localhost"
DEFAULT_OMERO_PORT = 6064
DEFAULT_OMERO_SECURE = 1

# [[group, permissions], ...]
GROUPS_TO_CREATE = [['test_group_1', 'read-only'],
                    ['test_group_2', 'read-only']]

# [[user, [groups to be added to], [groups to own]], ...]
USERS_TO_CREATE = [
                   [
                    'test_user1',
                    ['test_group_1', 'test_group_2'],
                    ['test_group_1']
                   ],
                   [
                    'test_user2',
                    ['test_group_1', 'test_group_2'],
                    ['test_group_2']
                   ],
                   [
                    'test_user3',
                    ['test_group_2'],
                    []
                   ]
                  ]



def pytest_addoption(parser):
    parser.addoption("--omero-user",
                     action="store",
                     default=os.environ.get("OMERO_USER",
                                            DEFAULT_OMERO_USER))
    parser.addoption("--omero-pass",
                     action="store",
                     default=os.environ.get("OMERO_PASS",
                                            DEFAULT_OMERO_PASS))
    parser.addoption("--omero-host",
                     action="store",
                     default=os.environ.get("OMERO_HOST",
                                            DEFAULT_OMERO_HOST))
    parser.addoption("--omero-port",
                     action="store",
                     type=int,
                     default=int(os.environ.get("OMERO_PORT",
                                                DEFAULT_OMERO_PORT)))
    parser.addoption("--omero-secure",
                     action="store",
                     default=bool(os.environ.get("OMERO_SECURE",
                                                 DEFAULT_OMERO_SECURE)))


# we can change this later
@pytest.fixture(scope="session")
def omero_params(request):
    user = request.config.getoption("--omero-user")
    password = request.config.getoption("--omero-pass")
    host = request.config.getoption("--omero-host")
    port = request.config.getoption("--omero-port")
    secure = request.config.getoption("--omero-secure")
    return(user, password, host, port, secure)


@pytest.fixture(scope='session')
def users_groups(conn, omero_params):
    session_uuid = conn.getSession().getUuid().val
    user = omero_params[0]
    host = omero_params[2]
    port = str(omero_params[3])
    cli = CLI()
    cli.register('sessions', SessionsControl, 'test')
    cli.register('user', UserControl, 'test')
    cli.register('group', GroupControl, 'test')

    group_info = []
    for gname, gperms in GROUPS_TO_CREATE:
        cli.invoke(['group', 'add',
                    gname,
                    '--type', gperms,
                    '-k', session_uuid,
                    '-u', user,
                    '-s', host,
                    '-p', port])
        gid = ezomero.get_group_id(conn, gname)
        group_info.append([gname, gid])

    user_info = []
    for user, groups_add, groups_own in USERS_TO_CREATE:
        # make user while adding to first group
        cli.invoke(['user', 'add',
                    user,
                    'test',
                    'tester',
                    '--group-name', groups_add[0],
                    '-e', 'useremail@jax.org',
                    '-P', 'abc123',
                    '-k', session_uuid,
                    '-u', user,
                    '-s', host,
                    '-p', port])

        # add user to rest of groups
        if len(groups_add) > 1:
            for group in groups_add[1:]:
                cli.invoke(['group', 'adduser',
                            '--user-name', user,
                            '--name', group,
                            '-k', session_uuid,
                            '-u', user,
                            '-s', host,
                            '-p', port])

        # make user owner of listed groups
        if len(groups_own) > 0:
            for group in groups_own:
                cli.invoke(['group', 'adduser',
                            '--user-name', user,
                            '--name', group,
                            '--as-owner',
                            '-k', session_uuid,
                            '-u', user,
                            '-s', host,
                            '-p', port])
        uid = ezomero.get_user_id(conn, user)
        user_info.append([user, uid])

    return (group_info, user_info)


@pytest.fixture(scope='session')
def conn(omero_params):
    user, password, host, port, secure = omero_params
    conn = BlitzGateway(user, password, host=host, port=port, secure=secure)
    conn.connect()
    yield conn
    conn.close()


@pytest.fixture(scope='session')
def image_fixture():
    test_image = np.zeros((200, 201, 20, 3, 1), dtype=np.uint8)
    test_image[0:100, 0:100, 0:10, 0, :] = 255
    test_image[0:100, 0:100, 11:20, 1, :] = 255
    test_image[101:200, 101:201, :, 2, :] = 255
    return test_image


@pytest.fixture(scope='session')
def timestamp():
    return f'{datetime.now():%Y%m%d%H%M%S}'


@pytest.fixture(scope='session')
def project_structure(conn, timestamp, image_fixture, users_groups,
                      omero_params):
    group_info, user_info = users_groups
    # Don't change anything for default_user!
    # If you change anything about users/groups, make sure they exist
    # [[group, [projects]], ...] per user
    project_str = {
                    'users': [
                        {
                            'name': 'default_user',
                            'groups': [
                                {
                                    'name': 'default_group',
                                    'projects': [
                                        {
                                            'name': f'proj0_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': f'ds0_{timestamp}',
                                                    'images': [
                                                        f'im0_{timestamp}'
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            'name': 'test_user1',
                            'groups': [
                                {
                                    'name': 'test_group_1',
                                    'projects': [
                                        {
                                            'name': f'proj1_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': f'ds1_{timestamp}',
                                                    'images': [
                                                        f'im1_{timestamp}'
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'name': f'proj2_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': '',
                                                    'images': [

                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    'name': 'test_group_2',
                                    'projects': [
                                        {
                                            'name': f'proj3_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': f'ds2_{timestamp}',
                                                    'images': [

                                                    ]
                                                },
                                                {
                                                    'name': f'ds3_{timestamp}',
                                                    'images': [
                                                        f'im2_{timestamp}',
                                                        f'im3_{timestamp}'
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            'name': 'test_user2',
                            'groups': [
                                {
                                    'name': 'test_group_1',
                                    'projects': [
                                        {
                                            'name': f'proj4_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': f'ds4_{timestamp}',
                                                    'images': [
                                                        f'im4_{timestamp}'
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            'name': f'proj5_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': f'ds5_{timestamp}',
                                                    'images': [

                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    'name': 'test_group_2',
                                    'projects': [
                                        {
                                            'name': f'proj6_{timestamp}',
                                            'datasets': [
                                                {
                                                    'name': f'ds6_{timestamp}',
                                                    'images': [
                                                        f'im5_{timestamp}',
                                                        f'im6_{timestamp}'
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                  }
    project_info = []
    dataset_info = []
    image_info = []
    for user in project_str['users']:
        username = user['name']
        for group in user['groups']:
            groupname = group['name']
            current_conn = conn

            # New connection if user and group need to be specified
            if username != 'default_user':
                current_conn = conn.suConn(username, groupname)

            # Loop to post projects, datasets, and images
            for project in group['projects']:
                projname = project['name']
                proj_id = ezomero.post_project(current_conn,
                                               projname,
                                               'test project')
                project_info.append([projname, proj_id])

                for dataset in project['datasets']:
                    dsname = dataset['name']
                    ds_id = ezomero.post_dataset(current_conn,
                                                 dsname,
                                                 proj_id,
                                                 'test dataset')
                    dataset_info.append([dsname, ds_id])

                    for imname in dataset['images']:
                        im_id = ezomero.post_image(current_conn,
                                                   image_fixture,
                                                   imname,
                                                   dataset_id=ds_id)
                        image_info.append([imname, im_id])

            # Close temporary connection if it was created
            if username != 'default_user':
                current_conn.close()

    yield [project_info, dataset_info, image_info]
    current_group = conn.getGroupFromContext().getId()
    conn.SERVICE_OPTS.setOmeroGroup(-1)
    for pname, pid in project_info:
        conn.deleteObjects("Project", [pid], deleteAnns=True,
                           deleteChildren=True, wait=True)
    conn.SERVICE_OPTS.setOmeroGroup(current_group)


@pytest.fixture(scope='session')
def screen_structure(conn, timestamp, image_fixture):
    # screen info
    update_service = conn.getUpdateService()
    # Create Screen
    screen_name = "screen_" + timestamp
    screen = ScreenWrapper(conn, ScreenI())
    screen.setName(screen_name)
    screen.save()
    screen_id = screen.getId()
    # Create Plate
    plate_name = "plate_" + timestamp
    plate = PlateWrapper(conn, PlateI())
    plate.setName(plate_name)
    plate.save()
    plate_id = plate.getId()
    link = ScreenPlateLinkI()
    link.setParent(ScreenI(screen_id, False))
    link.setChild(PlateI(plate_id, False))
    update_service.saveObject(link)

    # Create Well
    well = WellI()
    well.setPlate(PlateI(plate_id, False))
    well.setColumn(rint(1))
    well.setRow(rint(1))
    well.setPlate(PlateI(plate_id, False))

    # Create Well Sample with Image
    ws = WellSampleI()
    im_id1 = ezomero.post_image(conn, image_fixture, "well image")
    ws.setImage(ImageI(im_id1, False))
    well.addWellSample(ws)
    well_obj = update_service.saveAndReturnObject(well)
    well_id = well_obj.getId().getValue()

    yield [plate_id, well_id, im_id1, screen_id]
    current_group = conn.getGroupFromContext().getId()
    conn.SERVICE_OPTS.setOmeroGroup(-1)
    conn.deleteObjects("Screen", [screen_id], deleteAnns=True,
                       deleteChildren=True, wait=True)
    conn.SERVICE_OPTS.setOmeroGroup(current_group)