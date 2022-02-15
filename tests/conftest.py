import os
import pytest
import subprocess
import numpy as np
from datetime import datetime
import ezomero
from ezomero import rois
from omero.cli import CLI
from omero.gateway import BlitzGateway
from omero.gateway import ScreenWrapper, PlateWrapper
from omero.model import ScreenI, PlateI, WellI, WellSampleI, ImageI
from omero.model import ScreenPlateLinkI
from omero.plugins.sessions import SessionsControl
from omero.plugins.user import UserControl
from omero.plugins.group import GroupControl
from omero.rtypes import rint


# Settings for OMERO
DEFAULT_OMERO_USER = "root"
DEFAULT_OMERO_PASS = "omero"
DEFAULT_OMERO_HOST = "localhost"
DEFAULT_OMERO_WEB_HOST = "http://localhost:5080"
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
    parser.addoption("--omero-web-host",
                     action="store",
                     default=os.environ.get("OMERO_WEB_HOST",
                                            DEFAULT_OMERO_WEB_HOST))
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
    web_host = request.config.getoption("--omero-web-host")
    port = request.config.getoption("--omero-port")
    secure = request.config.getoption("--omero-secure")
    return(user, password, host, web_host, port, secure)


@pytest.fixture(scope='session')
def users_groups(conn, omero_params):
    session_uuid = conn.getSession().getUuid().val
    user = omero_params[0]
    host = omero_params[2]
    port = str(omero_params[4])
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
    user, password, host, web_host, port, secure = omero_params
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
def pyramid_fixture(conn, omero_params):
    session_uuid = conn.getSession().getUuid().val
    user = omero_params[0]
    host = omero_params[2]
    port = str(omero_params[4])
    imp_cmd = ['omero', 'import', 'tests/data/test_pyramid.ome.tif',
               '-k', session_uuid,
               '-u', user,
               '-s', host,
               '-p', port]
    process = subprocess.Popen(imp_cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdoutval, stderrval = process.communicate()


@pytest.fixture(scope='session')
def roi_fixture():
    point = rois.Point(x=100.0, y=100.0, z=0, c=0, t=0, label='test_point')
    line = rois.Line(x1=100.0, y1=100.0, x2=150.0, y2=150.0, z=0, c=0, t=0,
                     label='test_line')
    arrow = rois.Line(x1=100.0, y1=100.0, x2=150.0, y2=150.0, z=0, c=0, t=0,
                      label='test_arrow', markerEnd="Arrow",
                      markerStart="Arrow")
    rectangle = rois.Rectangle(x=100.0, y=100.0, width=50.0, height=40.0, z=0,
                               c=0, t=0, label='test_rectangle')
    ellipse = rois.Ellipse(x=80, y=60, x_rad=20.0, y_rad=40.0, z=0, c=0, t=0,
                           label='test_ellipse')
    polygon = rois.Polygon(points=[(100.0, 100.0),
                                   (110.0, 150.0),
                                   (100.0, 150.0)],
                           z=0, c=0, t=0, label='test_polygon')
    polyline = rois.Polyline(points=[(100.0, 100.0),
                                     (110.0, 150.0),
                                     (100.0, 150.0)],
                             z=0, c=0, t=0, label='test_polyline')
    label = rois.Label(x=100.0, y=100.0, z=0, c=0, t=0,
                       label='test_label', fontSize=60)

    return {'shapes': [point, line, rectangle, ellipse,
                       polygon, polyline, arrow, label],
            'name': 'ROI_name',
            'desc': 'A description for the ROI',
            'fill_color': (255, 0, 0, 200),
            'stroke_color': (255, 0, 0, 0),
            'stroke_width': 2
            }


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
                                            'datasets': []
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
                                                        f'im2_{timestamp}'

                                                    ]
                                                },
                                                {
                                                    'name': f'ds3_{timestamp}',
                                                    'images': [
                                                        f'im3_{timestamp}',
                                                        f'im4_{timestamp}'
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
                                                        f'im5_{timestamp}'
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
                                                        f'im6_{timestamp}',
                                                        f'im7_{timestamp}'
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

    # Create Well (row 1, col 1)
    well = WellI()
    well.setPlate(PlateI(plate_id, False))
    well.setColumn(rint(1))
    well.setRow(rint(1))
    well.setPlate(PlateI(plate_id, False))

    # Create another Well (row 2, col 2)
    well2 = WellI()
    well2.setPlate(PlateI(plate_id, False))
    well2.setColumn(rint(2))
    well2.setRow(rint(2))
    well2.setPlate(PlateI(plate_id, False))

    # Create Well Sample with Image for both wells
    ws = WellSampleI()
    im_id1 = ezomero.post_image(conn, image_fixture, "well image")
    ws.setImage(ImageI(im_id1, False))
    well.addWellSample(ws)

    ws2 = WellSampleI()
    im_id2 = ezomero.post_image(conn, image_fixture, "well image2")
    ws2.setImage(ImageI(im_id2, False))
    well2.addWellSample(ws2)

    well_obj = update_service.saveAndReturnObject(well)
    well2_obj = update_service.saveAndReturnObject(well2)

    well_id = well_obj.getId().getValue()
    well2_id = well2_obj.getId().getValue()

    yield [plate_id, well_id, im_id1, screen_id, well2_id, im_id2]
    current_group = conn.getGroupFromContext().getId()
    conn.SERVICE_OPTS.setOmeroGroup(-1)
    conn.deleteObjects("Screen", [screen_id], deleteAnns=True,
                       deleteChildren=True, wait=True)
    conn.SERVICE_OPTS.setOmeroGroup(current_group)
