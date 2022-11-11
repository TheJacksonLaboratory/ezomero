from attr import dataclass
import pytest
import numpy as np
import ezomero
import filecmp
import os
import sys
from unittest import mock


# Test posts
############
def test_post_dataset(conn, project_structure, users_groups, timestamp):

    # testing sanitized inputs
    with pytest.raises(TypeError):
        _ = ezomero.post_dataset(conn, 10)
    with pytest.raises(TypeError):
        _ = ezomero.post_dataset(conn, "testds", description=10)
    with pytest.raises(TypeError):
        _ = ezomero.post_dataset(conn, "testds", project_id='10')

    # Orphaned dataset, with descripion
    ds_test_name = 'test_post_dataset_' + timestamp
    did = ezomero.post_dataset(conn, ds_test_name, description='New test')
    assert conn.getObject("Dataset", did).getName() == ds_test_name
    assert conn.getObject("Dataset", did).getDescription() == "New test"

    # Dataset in default project, no description
    ds_test_name2 = 'test_post_dataset2_' + timestamp
    project_info = project_structure[0]
    pid = project_info[0][1]
    did2 = ezomero.post_dataset(conn, ds_test_name2, project_id=pid)
    ds = conn.getObjects("Dataset", opts={'project': pid})
    ds_names = [d.getName() for d in ds]
    assert ds_test_name2 in ds_names

    # Dataset in non-existing project ID
    ds_test_name3 = 'test_post_dataset3_' + timestamp
    pid = 99999999
    did3 = ezomero.post_dataset(conn, ds_test_name3, project_id=pid)
    assert did3 is None

    # Dataset in cross-group project, valid permissions
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]   # test_group_1
    current_conn = conn.suConn(username, groupname)
    ds_test_name4 = 'test_post_dataset4_' + timestamp
    project_info = project_structure[0]
    pid = project_info[3][1]  # proj3 (in test_group_2)
    did4 = ezomero.post_dataset(current_conn, ds_test_name4, project_id=pid)
    current_conn.SERVICE_OPTS.setOmeroGroup('-1')
    ds = current_conn.getObjects("Dataset", opts={'project': pid})
    ds_names = [d.getName() for d in ds]
    current_conn.close()
    assert ds_test_name4 in ds_names

    # Dataset in cross-group project, invalid permissions
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    ds_test_name5 = 'test_post_dataset5_' + timestamp
    project_info = project_structure[0]
    pid = project_info[1][1]  # proj1 (in test_group_1)
    did5 = ezomero.post_dataset(current_conn, ds_test_name5, project_id=pid)
    current_conn.close()
    assert did5 is None

    # Dataset in cross-group project, valid permissions
    # across_groups flag unset
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]   # test_group_1
    current_conn = conn.suConn(username, groupname)
    ds_test_name6 = 'test_post_dataset6_' + timestamp
    project_info = project_structure[0]
    pid = project_info[3][1]  # proj3 (in test_group_2)
    did6 = ezomero.post_dataset(current_conn, ds_test_name6, project_id=pid,
                                across_groups=False)
    current_conn.close()
    assert did6 is None

    conn.deleteObjects("Dataset", [did, did2, did4], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_image(conn, project_structure, users_groups, timestamp,
                    image_fixture):
    dataset_info = project_structure[1]
    did = dataset_info[0][1]

    # testing sanitized inputs
    with pytest.raises(TypeError):
        _ = ezomero.post_image(conn, 'image', 'test')
    fake_input = np.zeros((200, 200), dtype=np.uint8)
    with pytest.raises(ValueError):
        _ = ezomero.post_image(conn, fake_input, 'test')
    with pytest.raises(TypeError):
        _ = ezomero.post_image(conn, image_fixture, 10)
    with pytest.raises(TypeError):
        _ = ezomero.post_image(conn, image_fixture, 'test', dataset_id='10')
    with pytest.raises(TypeError):
        _ = ezomero.post_image(conn, image_fixture, 'test', dim_order=10)
    with pytest.raises(ValueError):
        _ = ezomero.post_image(conn, image_fixture, 'test', dim_order='hyzcb')

    # Post image in dataset
    image_name = 'test_post_image_' + timestamp
    im_id = ezomero.post_image(conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=did)
    assert conn.getObject("Image", im_id).getName() == image_name

    image_name = 'test_post_image_' + timestamp
    im_id_scr = ezomero.post_image(conn, image_fixture, image_name,
                                   description='This is an image',
                                   dataset_id=did, dim_order='czyxt')
    im = conn.getObject("Image", im_id_scr)
    assert im.getSizeX() == 3
    assert im.getSizeY() == 20
    assert im.getSizeC() == 200

    # Post orphaned image
    im_id2 = ezomero.post_image(conn, image_fixture, image_name)
    assert conn.getObject("Image", im_id2).getName() == image_name

    # Post image to non-existent dataset
    did3 = 999999999
    im_id3 = ezomero.post_image(conn, image_fixture, image_name,
                                description='This is an image',
                                dataset_id=did3)
    assert im_id3 is None

    # Post image cross-group, valid permissions
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    dataset_info = project_structure[1]
    did4 = dataset_info[3][1]  # ds2 (in test_group_2)
    image_name = 'test_post_image_' + timestamp
    im_id4 = ezomero.post_image(current_conn, image_fixture, image_name,
                                description='This is an image',
                                dataset_id=did4)
    current_conn.SERVICE_OPTS.setOmeroGroup('-1')
    assert current_conn.getObject("Image", im_id4).getName() == image_name
    current_conn.close()

    # Post image cross-group, ivvalid permissions
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    dataset_info = project_structure[1]
    did5 = dataset_info[1][1]  # ds1 (in test_group_1)
    image_name = 'test_post_image_' + timestamp
    im_id5 = ezomero.post_image(current_conn, image_fixture, image_name,
                                description='This is an image',
                                dataset_id=did5)
    current_conn.close()
    assert im_id5 is None

    # Post image cross-group, valid permissions, across_groups unset
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    dataset_info = project_structure[1]
    did6 = dataset_info[3][1]  # ds2 (in test_group_2)
    image_name = 'test_post_image_' + timestamp
    im_id6 = ezomero.post_image(current_conn, image_fixture, image_name,
                                description='This is an image',
                                dataset_id=did6, across_groups=False)
    current_conn.close()
    assert im_id6 is None

    conn.deleteObjects("Image", [im_id, im_id2, im_id4, im_id_scr],
                       deleteAnns=True, deleteChildren=True,
                       wait=True)


def test_post_get_map_annotation(conn, project_structure, users_groups):
    image_info = project_structure[2]
    im_id = image_info[0][1]
    # This test both ezomero.post_map_annotation and ezomero.get_map_annotation
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"

    # test sanitized input on post
    with pytest.raises(TypeError):
        _ = ezomero.post_map_annotation(conn, "Image", im_id, 'test', ns)
    with pytest.raises(TypeError):
        _ = ezomero.post_map_annotation(conn, "Image", '10', kv, ns)
    with pytest.raises(TypeError):
        _ = ezomero.post_map_annotation(conn, "Image", None, kv, ns)

    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    kv_pairs = ezomero.get_map_annotation(conn, map_ann_id)
    assert kv_pairs["key2"] == "value2"

    # Test posting to non-existing object
    im_id2 = 999999999
    map_ann_id2 = ezomero.post_map_annotation(conn, "Image", im_id2, kv, ns)
    assert map_ann_id2 is None

    # Test posting cross-group
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1]  # im2, in test_group_2
    map_ann_id3 = ezomero.post_map_annotation(current_conn, "Image", im_id3,
                                              kv, ns)
    kv_pairs3 = ezomero.get_map_annotation(current_conn, map_ann_id3)
    assert kv_pairs3["key2"] == "value2"
    current_conn.close()

    # Test posting to an invalid cross-group
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1]  # im1(in test_group_1)
    map_ann_id4 = ezomero.post_map_annotation(current_conn, "Image", im_id4,
                                              kv, ns)
    assert map_ann_id4 is None
    current_conn.close()

    # Test posting cross-group, across_groups unset
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id6 = image_info[2][1]  # im2, in test_group_2
    map_ann_id6 = ezomero.post_map_annotation(current_conn, "Image", im_id6,
                                              kv, ns, across_groups=False)
    assert map_ann_id6 is None
    current_conn.close()

    conn.deleteObjects("Annotation", [map_ann_id, map_ann_id3],
                       deleteAnns=True, deleteChildren=True, wait=True)


def test_post_get_file_annotation(conn, project_structure, users_groups,
                                  tmp_path):

    image_info = project_structure[2]
    im_id = image_info[0][1]

    # This test both ezomero.post_file_annotation and
    # ezomero.get_file_annotation
    d = tmp_path / "input"
    d.mkdir()
    file_path = d / "hello.txt"
    file_path.write_text("hello world!")
    file_ann = str(file_path)

    ns = "jax.org/omeroutils/tests/v0"
    # test sanitized input on post
    with pytest.raises(TypeError):
        _ = ezomero.post_file_annotation(conn, "Image", im_id, 10, ns)
    with pytest.raises(TypeError):
        _ = ezomero.post_file_annotation(conn, "Image", '10', file_ann, ns)
    with pytest.raises(TypeError):
        _ = ezomero.post_file_annotation(conn, "Image", None, file_ann, ns)

    file_ann_id = ezomero.post_file_annotation(conn, "Image", im_id, file_ann,
                                               ns)
    return_ann = ezomero.get_file_annotation(conn, file_ann_id)
    assert filecmp.cmp(return_ann, file_ann)
    os.remove(return_ann)

    # Test posting to non-existing object
    im_id2 = 999999999
    file_ann_id2 = ezomero.post_file_annotation(conn, "Image", im_id2,
                                                file_ann, ns)
    assert file_ann_id2 is None

    # Test posting cross-group
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1]  # im2, in test_group_2
    file_ann_id3 = ezomero.post_file_annotation(current_conn, "Image", im_id3,
                                                file_ann, ns)
    return_ann3 = ezomero.get_file_annotation(current_conn, file_ann_id3)
    assert filecmp.cmp(return_ann3, file_ann)
    os.remove(return_ann3)
    current_conn.close()

    # Test posting to an invalid cross-group
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1]  # im1(in test_group_1)
    file_ann_id4 = ezomero.post_file_annotation(current_conn, "Image", im_id4,
                                                file_ann, ns)
    assert file_ann_id4 is None
    current_conn.close()

    # Test posting cross-group, across_groups unset
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id5 = image_info[2][1]  # im2, in test_group_2
    file_ann_id5 = ezomero.post_file_annotation(current_conn, "Image", im_id5,
                                                file_ann, ns,
                                                across_groups=False)
    assert file_ann_id5 is None
    current_conn.close()

    conn.deleteObjects("Annotation", [file_ann_id, file_ann_id3],
                       deleteAnns=True, deleteChildren=True, wait=True)


def test_post_roi(conn, project_structure, roi_fixture, users_groups):
    image_info = project_structure[2]
    im_id = image_info[0][1]

    # test sanitized input on post
    with pytest.raises(TypeError):
        _ = ezomero.post_roi(conn, '10',
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(TypeError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes='10',
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(TypeError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes=['10'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(TypeError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=[10, 10, 10, 10],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(ValueError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=(10, 10, 10),
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(TypeError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=[10, 10, 10, 10],
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(ValueError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=(10, 10, 10),
                             stroke_width=roi_fixture['stroke_width'])
    with pytest.raises(TypeError):
        _ = ezomero.post_roi(conn, im_id,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width='width')
# "regular" test
    roi_id = ezomero.post_roi(conn, im_id,
                              shapes=roi_fixture['shapes'],
                              name=roi_fixture['name'],
                              description=roi_fixture['desc'],
                              fill_color=roi_fixture['fill_color'],
                              stroke_color=roi_fixture['stroke_color'],
                              stroke_width=roi_fixture['stroke_width'])
    roi_in_omero = conn.getObject('Roi', roi_id)
    assert roi_in_omero.getName() == roi_fixture['name']
    assert roi_in_omero.getDescription() == roi_fixture['desc']

    # Test posting to a non-existing image
    im_id2 = 999999999
    with pytest.raises(Exception):  # TODO: verify which exception type
        _ = ezomero.post_roi(conn, im_id2,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])

    # Test posting to an invalid cross-group
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1]  # im1(in test_group_1)
    with pytest.raises(Exception):  # TODO: verify which exception type
        _ = ezomero.post_roi(current_conn, im_id4,
                             shapes=roi_fixture['shapes'],
                             name=roi_fixture['name'],
                             description=roi_fixture['desc'],
                             fill_color=roi_fixture['fill_color'],
                             stroke_color=roi_fixture['stroke_color'],
                             stroke_width=roi_fixture['stroke_width'])
    current_conn.close()

    conn.deleteObjects("Roi", [roi_id], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_project(conn, timestamp):
    # No description
    new_proj = "test_post_project_" + timestamp
    pid = ezomero.post_project(conn, new_proj)
    assert conn.getObject("Project", pid).getName() == new_proj

    # With description
    new_proj2 = "test_post_project2_" + timestamp
    desc = "Now with a description"
    pid2 = ezomero.post_project(conn, new_proj2, description=desc)
    assert conn.getObject("Project", pid2).getDescription() == desc
    conn.deleteObjects("Project", [pid, pid2], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_screen(conn, timestamp):
    # No description
    new_screen = "test_post_screen_" + timestamp
    sid = ezomero.post_screen(conn, new_screen)
    assert conn.getObject("Screen", sid).getName() == new_screen

    # With description
    new_screen2 = "test_post_screen2_" + timestamp
    desc = "Now with a description"
    sid2 = ezomero.post_screen(conn, new_screen2, description=desc)
    assert conn.getObject("Screen", sid2).getDescription() == desc
    conn.deleteObjects("Screen", [sid, sid2], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_project_type(conn):
    with pytest.raises(TypeError):
        _ = ezomero.post_project(conn, 123)
    with pytest.raises(TypeError):
        _ = ezomero.post_project(conn, '123', description=1245)


def test_post_screen_type(conn):
    with pytest.raises(TypeError):
        _ = ezomero.post_screen(conn, 123)
    with pytest.raises(TypeError):
        _ = ezomero.post_screen(conn, '123', description=1245)


def test_post_get_table_pandas(conn, project_structure, table_dfs):

    image_info = project_structure[2]
    im_id = image_info[0][1]

    # This test both ezomero.post_table and ezomero.get_table, using pandas

    table_id = ezomero.post_table(conn, table_dfs[0], "Image", im_id)
    print(table_id)
    return_ann = ezomero.get_table(conn, table_id)
    print(return_ann, table_dfs[1])
    assert return_ann.equals(table_dfs[1])
    conn.deleteObjects("Annotation", [table_id],
                       deleteAnns=True, deleteChildren=True, wait=True)


def test_post_get_table_nopandas(conn, project_structure, users_groups,
                                 tables):

    # This test both ezomero.post_table and ezomero.get_table, not using pandas
    image_info = project_structure[2]
    im_id = image_info[0][1]
    # test sanitized input on post
    with pytest.raises(TypeError):
        _ = ezomero.post_table(conn, 10, "Image", im_id)
    with pytest.raises(TypeError):
        _ = ezomero.post_table(conn, tables[0], "Image", '10')
    with pytest.raises(TypeError):
        _ = ezomero.post_table(conn, tables[0], "Image", None)

    with mock.patch.dict(sys.modules):
        sys.modules["pandas"] = None
        table_id = ezomero.post_table(conn, tables[0], "Image", im_id,
                                      title="test table", headers=True)
        print(table_id)
        return_ann = ezomero.get_table(conn, table_id)
        print(return_ann, tables[1])
        assert return_ann == tables[1]

        # Test posting to non-existing object
        im_id2 = 999999999
        table_id2 = ezomero.post_table(conn, tables[0], "Image", im_id2)
        assert table_id2 is None

        conn.deleteObjects("Annotation", [table_id],
                           deleteAnns=True, deleteChildren=True, wait=True)
