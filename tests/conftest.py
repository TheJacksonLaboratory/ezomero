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
from omero.model import ScreenPlateLinkI, PlateAcquisitionI
from omero.plugins.sessions import SessionsControl
from omero.plugins.user import UserControl
from omero.plugins.group import GroupControl
from omero.rtypes import rint
import importlib.util
# try importing pandas
if (importlib.util.find_spec('pandas')):
    import pandas as pd
    has_pandas = True
else:
    has_pandas = False


# Settings for OMERO
DEFAULT_OMERO_USER = "root"
DEFAULT_OMERO_PASS = "omero"
DEFAULT_OMERO_HOST = "localhost"
DEFAULT_OMERO_WEB_HOST = "http://localhost:5080"
DEFAULT_OMERO_PORT = "6064"
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
                     default=os.environ.get("OMERO_PORT",
                                            DEFAULT_OMERO_PORT))
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
    return (user, password, host, web_host, port, secure)


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
    point = rois.Point(x=100.0, y=100.0, z=0, c=0, t=0, label='test_point',
                       fill_color=(0, 1, 2, 3), stroke_color=(4, 5, 6, 100),
                       stroke_width=1.0)
    line = rois.Line(x1=100.0, y1=100.0, x2=150.0, y2=150.0, z=0, c=0, t=0,
                     label='test_line', fill_color=(7, 8, 9, 10),
                     stroke_color=(11, 12, 13, 106), stroke_width=2.0)
    arrow = rois.Line(x1=100.0, y1=100.0, x2=150.0, y2=150.0, z=0, c=0, t=0,
                      label='test_arrow', markerEnd="Arrow",
                      markerStart="Arrow")
    rectangle = rois.Rectangle(x=100.0, y=100.0, width=50.0, height=40.0, z=0,
                               c=0, t=0, label='test_rectangle',
                               fill_color=(14, 15, 16, 17),
                               stroke_color=(18, 19, 20, 101),
                               stroke_width=3.0)
    ellipse = rois.Ellipse(x=80, y=60, x_rad=20.0, y_rad=40.0, z=0, c=0, t=0,
                           label='test_ellipse',
                           fill_color=(21, 22, 23, 24),
                           stroke_color=(25, 26, 27, 102),
                           stroke_width=4.0)
    polygon = rois.Polygon(points=[(100.0, 100.0),
                                   (110.0, 150.0),
                                   (100.0, 150.0)],
                           z=0, c=0, t=0, label='test_polygon',
                           fill_color=(28, 29, 30, 31),
                           stroke_color=(32, 33, 34, 103),
                           stroke_width=5.0)
    polyline = rois.Polyline(points=[(100.0, 100.0),
                                     (110.0, 150.0),
                                     (100.0, 150.0)],
                             z=0, c=0, t=0, label='test_polyline',
                             fill_color=(35, 36, 37, 38),
                             stroke_color=(39, 40, 41, 104),
                             stroke_width=6.0)
    label = rois.Label(x=100.0, y=100.0, z=0, c=0, t=0,
                       label='test_label', fontSize=60,
                       fill_color=(42, 43, 44, 45),
                       stroke_color=(46, 47, 48, 105),
                       stroke_width=7.0)

    return {'shapes': [point, line, rectangle, ellipse,
                       polygon, polyline, arrow, label],
            'name': 'ROI_name',
            'desc': 'A description for the ROI'
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
                                    ],
                                    'datasets': []
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
                                    ],
                                    'datasets': []
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
                                    ],
                                    'datasets': []
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
                                    ],
                                    'datasets': []
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
                                    ],
                                    'datasets': [
                                        {
                                            'name': f'ds7_{timestamp}'
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
            for dataset in group['datasets']:
                dsname = dataset['name']
                ds_id = ezomero.post_dataset(current_conn,
                                             dsname,
                                             description='test dataset')
                dataset_info.append([dsname, ds_id])

            # Close temporary connection if it was created
            if username != 'default_user':
                current_conn.close()

    yield [project_info, dataset_info, image_info]
    current_group = conn.getGroupFromContext().getId()
    conn.SERVICE_OPTS.setOmeroGroup(-1)
    for dname, did in dataset_info:
        conn.deleteObjects("Dataset", [did], deleteAnns=True,
                           deleteChildren=True, wait=True)
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
    plate_name = "plate1_" + timestamp
    plate = PlateWrapper(conn, PlateI())
    plate.setName(plate_name)
    plate.save()
    plate_id = plate.getId()
    link = ScreenPlateLinkI()
    link.setParent(ScreenI(screen_id, False))
    link.setChild(PlateI(plate_id, False))
    update_service.saveObject(link)

    # Create second Plate
    plate2_name = "plate2_" + timestamp
    plate2 = PlateWrapper(conn, PlateI())
    plate2.setName(plate2_name)
    plate2.save()
    plate2_id = plate2.getId()
    link = ScreenPlateLinkI()
    link.setParent(ScreenI(screen_id, False))
    link.setChild(PlateI(plate2_id, False))
    update_service.saveObject(link)

    # Create Well (row 1, col 1)
    well1 = WellI()
    well1.setPlate(PlateI(plate_id, False))
    well1.setColumn(rint(1))
    well1.setRow(rint(1))

    # Create another Well (row 2, col 2)
    well2 = WellI()
    well2.setPlate(PlateI(plate_id, False))
    well2.setColumn(rint(2))
    well2.setRow(rint(2))

    # Create Well for second plate
    well3 = WellI()
    well3.setPlate(PlateI(plate2_id, False))
    well3.setColumn(rint(2))
    well3.setRow(rint(2))

    # Create PlateAcquisition/Run for plate 1
    run1 = PlateAcquisitionI()
    run1.setPlate(PlateI(plate_id, False))
    run2 = PlateAcquisitionI()
    run2.setPlate(PlateI(plate_id, False))

    # Create PlateAcquisition/Run for plate 2
    run3 = PlateAcquisitionI()
    run3.setPlate(PlateI(plate2_id, False))

    well1 = update_service.saveAndReturnObject(well1)
    well2 = update_service.saveAndReturnObject(well2)
    well3 = update_service.saveAndReturnObject(well3)
    well1_id = well1.getId().getValue()
    well2_id = well2.getId().getValue()
    well3_id = well3.getId().getValue()

    run1 = update_service.saveAndReturnObject(run1)
    run2 = update_service.saveAndReturnObject(run2)
    run3 = update_service.saveAndReturnObject(run3)
    run1_id = run1.getId().getValue()
    run2_id = run2.getId().getValue()
    run3_id = run3.getId().getValue()

    # Create Well Sample with Image for both wells
    ws = WellSampleI()
    im_id1 = ezomero.post_image(conn, image_fixture, "well image")
    ws.setImage(ImageI(im_id1, False))
    well1.addWellSample(ws)
    run1.addWellSample(ws)

    ws2 = WellSampleI()
    im_id2 = ezomero.post_image(conn, image_fixture, "well image2")
    ws2.setImage(ImageI(im_id2, False))
    well2.addWellSample(ws2)
    run1.addWellSample(ws2)

    ws3 = WellSampleI()
    im_id3 = ezomero.post_image(conn, image_fixture, "well image3")
    ws3.setImage(ImageI(im_id3, False))
    well1.addWellSample(ws3)
    run2.addWellSample(ws3)

    ws4 = WellSampleI()
    im_id4 = ezomero.post_image(conn, image_fixture, "well image4")
    ws4.setImage(ImageI(im_id4, False))
    well2.addWellSample(ws4)
    run2.addWellSample(ws4)

    ws5 = WellSampleI()
    im_id5 = ezomero.post_image(conn, image_fixture, "well image5")
    ws5.setImage(ImageI(im_id5, False))
    well3.addWellSample(ws5)
    run3.addWellSample(ws5)

    # One call for each plate is enough to update
    well1 = update_service.saveAndReturnObject(well1)
    well3 = update_service.saveAndReturnObject(well3)

    # Create OrphanPlate
    plate3_name = "plate3_" + timestamp
    plate3 = PlateWrapper(conn, PlateI())
    plate3.setName(plate3_name)
    plate3.save()
    plate3_id = plate3.getId()

    # Create Well fr orphan plate
    well4 = WellI()
    well4.setPlate(PlateI(plate3_id, False))
    well4.setColumn(rint(1))
    well4.setRow(rint(1))

    # Create Well Sample with Image
    ws6 = WellSampleI()
    im_id6 = ezomero.post_image(conn, image_fixture, "well image6")
    ws6.setImage(ImageI(im_id6, False))
    well4.addWellSample(ws6)

    well4 = update_service.saveAndReturnObject(well4)
    well4_id = well4.getId().getValue()

    yield [screen_id, plate_id, plate2_id, plate3_id,
           run1_id, run2_id, run3_id,
           well1_id, im_id1, im_id3,
           well2_id, im_id2, im_id4,
           well3_id, im_id5,
           well4_id, im_id6]
    current_group = conn.getGroupFromContext().getId()
    conn.SERVICE_OPTS.setOmeroGroup(-1)
    conn.deleteObjects("Screen", [screen_id], deleteAnns=True,
                       deleteChildren=True, wait=True)
    conn.deleteObjects("Plate", [plate3_id], deleteAnns=True,
                       deleteChildren=True, wait=True)
    conn.SERVICE_OPTS.setOmeroGroup(current_group)


@pytest.fixture(scope='session')
def tables():
    table = [
        ['intcol', 'floatcol', 'stringcol', 'boolcol', 'mixed'],
        [1, 1.2, 'string1', True, 'mixedstr'],
        [2, 2.3, 'string2', False, 1],
        [3, 3.4, 'string3', False, 2.4],
        [4, 4.5, 'string4', True, True],
    ]
    result_table = [
        ['intcol', 'floatcol', 'stringcol', 'boolcol'],
        [1, 1.2, 'string1', True],
        [2, 2.3, 'string2', False],
        [3, 3.4, 'string3', False],
        [4, 4.5, 'string4', True],
    ]
    return [table, result_table]


@pytest.fixture(scope='session')
def table_dfs():
    table = [
        ['intcol', 'floatcol', 'stringcol', 'boolcol', 'mixed'],
        [1, 1.2, 'string1', True, 'mixedstr'],
        [2, 2.3, 'string2', False, 1],
        [3, 3.4, 'string3', False, 2.4],
        [4, 4.5, 'string4', True, True],
    ]
    result_table = [
        ['intcol', 'floatcol', 'stringcol', 'boolcol'],
        [1, 1.2, 'string1', True],
        [2, 2.3, 'string2', False],
        [3, 3.4, 'string3', False],
        [4, 4.5, 'string4', True],
    ]
    headers = table.pop(0)
    df = pd.DataFrame(table, columns=headers)
    headers = result_table.pop(0)
    result_df = pd.DataFrame(result_table, columns=headers)
    return [df, result_df]
