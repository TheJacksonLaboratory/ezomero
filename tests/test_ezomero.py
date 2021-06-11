import pytest
import numpy as np
import ezomero
import filecmp
import os


def test_omero_connection(conn, omero_params):
    assert conn.getUser().getName() == omero_params[0]


# Test posts
############
def test_post_dataset(conn, project_structure, users_groups, timestamp):

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
    assert did3 == None

    # Dataset in cross-group project, valid permissions
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0]  #test_group_1
    gid = users_groups[0][0][1]
    current_conn = conn.suConn(username, groupname)
    ds_test_name4 = 'test_post_dataset4_' + timestamp
    project_info = project_structure[0]
    pid = project_info[3][1] #proj3 (in test_group_2)
    did4 = ezomero.post_dataset(current_conn, ds_test_name4, project_id=pid)
    current_conn.SERVICE_OPTS.setOmeroGroup('-1')
    ds = current_conn.getObjects("Dataset", opts={'project': pid})
    ds_names = [d.getName() for d in ds]
    current_conn.close()
    assert ds_test_name4 in ds_names

    # Dataset in cross-group project, invalid permissions
    username = users_groups[1][2][0] #test_user3
    groupname = users_groups[0][1][0] #test_group_2
    current_conn = conn.suConn(username, groupname)
    ds_test_name5 = 'test_post_dataset5_' + timestamp
    project_info = project_structure[0]
    pid = project_info[1][1] #proj1 (in test_group_1)
    did5 = ezomero.post_dataset(current_conn, ds_test_name5, project_id=pid)
    current_conn.close()
    assert did5 == None

    # Dataset in cross-group project, valid permissions, across_groups flag unset
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0]  #test_group_1
    gid = users_groups[0][0][1]
    current_conn = conn.suConn(username, groupname)
    ds_test_name6 = 'test_post_dataset6_' + timestamp
    project_info = project_structure[0]
    pid = project_info[3][1] #proj3 (in test_group_2)
    did6 = ezomero.post_dataset(current_conn, ds_test_name6, project_id=pid, across_groups=False)
    current_conn.close()
    assert did6 == None

    conn.deleteObjects("Dataset", [did, did2, did4], deleteAnns=True,
                        deleteChildren=True, wait=True)
    

def test_post_image(conn, project_structure, users_groups, timestamp, image_fixture):
    dataset_info = project_structure[1]
    did = dataset_info[0][1]
    # Post image in dataset
    image_name = 'test_post_image_' + timestamp
    im_id = ezomero.post_image(conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=did)
    assert conn.getObject("Image", im_id).getName() == image_name

    # Post orphaned image
    im_id2 = ezomero.post_image(conn, image_fixture, image_name)
    assert conn.getObject("Image", im_id2).getName() == image_name
    
    # Post image to non-existent dataset
    did3 = 999999999
    im_id3 = ezomero.post_image(conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=did3)
    assert im_id3 == None

    # Post image cross-group, valid permissions
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    dataset_info = project_structure[1]
    did4 = dataset_info[3][1] #ds2 (in test_group_2)
    image_name = 'test_post_image_' + timestamp
    im_id4 = ezomero.post_image(current_conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=did4)
    current_conn.SERVICE_OPTS.setOmeroGroup('-1')
    assert current_conn.getObject("Image", im_id4).getName() == image_name
    current_conn.close()

    # Post image cross-group, ivvalid permissions
    username = users_groups[1][2][0] #test_user3
    groupname = users_groups[0][1][0] #test_group_2
    current_conn = conn.suConn(username, groupname)
    dataset_info = project_structure[1]
    did5 = dataset_info[1][1] #ds1 (in test_group_1)
    image_name = 'test_post_image_' + timestamp
    im_id5 = ezomero.post_image(current_conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=did5)
    current_conn.close()
    assert im_id5 == None

    # Post image cross-group, valid permissions, across_groups unset
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    dataset_info = project_structure[1]
    did6 = dataset_info[3][1] #ds2 (in test_group_2)
    image_name = 'test_post_image_' + timestamp
    im_id6 = ezomero.post_image(current_conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=did6, across_groups=False)
    current_conn.close()
    assert im_id6 == None

    conn.deleteObjects("Image", [im_id, im_id2, im_id4], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_get_map_annotation(conn, project_structure, users_groups):
    image_info = project_structure[2]
    im_id = image_info[0][1]
    # This test both ezomero.post_map_annotation and ezomero.get_map_annotation
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    kv_pairs = ezomero.get_map_annotation(conn, map_ann_id)
    assert kv_pairs["key2"] == "value2"

    # Test posting to non-existing object
    im_id2 = 999999999
    map_ann_id2 = ezomero.post_map_annotation(conn, "Image", im_id2, kv, ns)
    assert map_ann_id2 == None
    
    # Test posting cross-group
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1]  # im2, in test_group_2
    map_ann_id3 = ezomero.post_map_annotation(current_conn, "Image", im_id3, kv, ns)
    kv_pairs3 = ezomero.get_map_annotation(current_conn, map_ann_id3)
    assert kv_pairs3["key2"] == "value2"
    current_conn.close()

    # Test posting to an invalid cross-group 
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1]  # im1(in test_group_1)
    map_ann_id4 = ezomero.post_map_annotation(current_conn, "Image", im_id4, kv, ns)
    assert map_ann_id4 == None
    current_conn.close()

    # Test posting cross-group, across_groups unset
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id6 = image_info[2][1] #im2, in test_group_2
    map_ann_id6 = ezomero.post_map_annotation(current_conn, "Image", im_id6, kv, ns, across_groups=False)
    assert map_ann_id6 == None
    current_conn.close()

    conn.deleteObjects("Annotation", [map_ann_id, map_ann_id3], deleteAnns=True,
                       deleteChildren=True, wait=True)



def test_post_get_file_annotation(conn, project_structure, users_groups, tmp_path):
    
    image_info = project_structure[2]
    im_id = image_info[0][1]
    # This test both ezomero.post_file_annotation and ezomero.get_file_annotation
    
    d = tmp_path / "input"
    d.mkdir()
    file_path = d / "hello.txt"
    file_path.write_text("hello world!")
    file_ann = str(file_path)
    
    ns = "jax.org/omeroutils/tests/v0"
    file_ann_id = ezomero.post_file_annotation(conn, "Image", im_id, file_ann, ns)
    return_ann = ezomero.get_file_annotation(conn, file_ann_id)
    assert filecmp.cmp(return_ann, file_ann)
    os.remove(return_ann)

    # Test posting to non-existing object
    im_id2 = 999999999
    file_ann_id2 = ezomero.post_file_annotation(conn, "Image", im_id2, file_ann, ns)
    assert file_ann_id2 == None
    
    # Test posting cross-group
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1]  # im2, in test_group_2
    file_ann_id3 = ezomero.post_file_annotation(current_conn, "Image", im_id3, file_ann, ns)
    return_ann3 = ezomero.get_file_annotation(current_conn, file_ann_id3)
    assert filecmp.cmp(return_ann3, file_ann)
    os.remove(return_ann3)
    current_conn.close()

    # Test posting to an invalid cross-group 
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1]  # im1(in test_group_1)
    file_ann_id4 = ezomero.post_file_annotation(current_conn, "Image", im_id4, file_ann, ns)
    assert file_ann_id4 == None
    current_conn.close()

    # Test posting cross-group, across_groups unset
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id5 = image_info[2][1] #im2, in test_group_2
    file_ann_id5 = ezomero.post_file_annotation(current_conn, "Image", im_id5, file_ann, ns, across_groups=False)
    assert file_ann_id5 == None
    current_conn.close()

    conn.deleteObjects("Annotation", [file_ann_id, file_ann_id3], deleteAnns=True,
                       deleteChildren=True, wait=True)
    
    


def test_post_roi(conn, project_structure, roi_fixture, users_groups):
    image_info = project_structure[2]
    im_id = image_info[0][1]
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


def test_post_project_type(conn):
    with pytest.raises(TypeError):
        _ = ezomero.post_project(conn, 123)
    with pytest.raises(TypeError):
        _ = ezomero.post_project(conn, '123', description=1245)


# Test gets
###########

def test_get_image(conn, project_structure, users_groups):
    image_info = project_structure[2]
    im_id = image_info[0][1]
    # test default
    im, im_arr = ezomero.get_image(conn, im_id)
    assert im.getId() == im_id
    assert im_arr.shape == (1, 20, 201, 200, 3)
    assert im.getPixelsType() == im_arr.dtype

    # test non-existent id

    im_id2 = 999999999
    im2, im_arr2 = ezomero.get_image(conn, im_id2)
    assert im2 == None
    assert im_arr2 == None

    # test cross-group valid
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1] #im2, in test_group_2
    im3, im_arr3 = ezomero.get_image(current_conn, im_id3)
    assert im3.getId() == im_id3
    assert im_arr3.shape == (1, 20, 201, 200, 3)
    assert im3.getPixelsType() == im_arr3.dtype
    current_conn.close()

    # test cross-group invalid
    username = users_groups[1][2][0] #test_user3
    groupname = users_groups[0][1][0] #test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1] #im1(in test_group_1)
    im4, im_arr4 = ezomero.get_image(current_conn, im_id4)
    assert im4 == None
    assert im_arr4 == None
    current_conn.close()

    # test cross-group valid, across_groups unset
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id5 = image_info[2][1] #im2, in test_group_2
    im5, im_arr5 = ezomero.get_image(current_conn, im_id5, across_groups=False)
    assert im5 == None
    assert im_arr5 == None
    current_conn.close()

    # test xyzct
    im, im_arr = ezomero.get_image(conn, im_id, xyzct=True)
    assert im_arr.shape == (200, 201, 20, 3, 1)

    # test no pixels
    im, im_arr = ezomero.get_image(conn, im_id, no_pixels=True)
    assert im_arr is None

    # test that IndexError comes up when pad=False
    with pytest.raises(IndexError):
        im, im_arr = ezomero.get_image(conn, im_id,
                                       start_coords=(195, 195, 18, 0, 0),
                                       axis_lengths=(10, 10, 3, 4, 3),
                                       pad=False)

    # test crop
    im, im_arr = ezomero.get_image(conn, im_id,
                                   start_coords=(101, 101, 10, 0, 0),
                                   axis_lengths=(10, 10, 3, 3, 1))
    assert im_arr.shape == (1, 3, 10, 10, 3)
    assert np.allclose(im_arr[0, 0, 0, 0, :], [0, 0, 255])

    # test crop with padding
    im, im_arr = ezomero.get_image(conn, im_id,
                                   start_coords=(195, 195, 18, 0, 0),
                                   axis_lengths=(10, 11, 3, 4, 3),
                                   pad=True)
    assert im_arr.shape == (3, 3, 11, 10, 4)




def test_get_image_ids(conn, project_structure, screen_structure, users_groups):
    
    dataset_info = project_structure[1]
    main_ds_id = dataset_info[0][1]
    image_info = project_structure[2]
    im_id = image_info[0][1]
    # Based on dataset ID
    im_ids = ezomero.get_image_ids(conn, dataset=main_ds_id)
    assert im_ids[0] == im_id
    assert len(im_ids) == 1

    # Based on well ID
    well_id = screen_structure[1]
    im_id1 = screen_structure[2]
    im_ids = ezomero.get_image_ids(conn, well=well_id)
    assert im_ids[0] == im_id1
    assert len(im_ids) == 1

    # test cross-group valid
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    main_ds_id2 = dataset_info[4][1]
    im_id2 = image_info[2][1] #im2, in test_group_2
    im_ids2 = ezomero.get_image_ids(current_conn, dataset=main_ds_id2)
    assert im_ids2[0] == im_id2
    assert len(im_ids2) == 2
    current_conn.close()

    # test cross-group invalid
    username = users_groups[1][2][0] #test_user3
    groupname = users_groups[0][1][0] #test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[1][1] #im1(in test_group_1)
    main_ds_id3 = dataset_info[1][1]
    im_ids3 = ezomero.get_image_ids(current_conn, dataset=main_ds_id3)
    assert len(im_ids3) == 0

    # test cross-group valid, across_groups unset
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    main_ds_id4 = dataset_info[4][1]
    im_id4 = image_info[2][1] #im2, in test_group_2
    im_ids4 = ezomero.get_image_ids(current_conn, dataset=main_ds_id4, across_groups=False)
    assert len(im_ids4) == 0
    current_conn.close()

    # Return nothing on bad input
    im_ids5 = ezomero.get_image_ids(conn, dataset=999999)
    assert len(im_ids5) == 0


def test_get_map_annotation_ids(conn, project_structure):
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    image_info = project_structure[2]
    im_id = image_info[0][1]
    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    map_ann_id2 = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    map_ann_id3 = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    ns2 = "different namespace"
    map_ann_id4 = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns2)
    map_ann_ids = ezomero.get_map_annotation_ids(conn, "Image", im_id, ns=ns)

    good_ids = [map_ann_id, map_ann_id2, map_ann_id3]
    assert all([mid in map_ann_ids for mid in good_ids])
    assert map_ann_id4 not in map_ann_ids
    conn.deleteObjects("Annotation",
                       [map_ann_id, map_ann_id2, map_ann_id3, map_ann_id4],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)

def test_get_file_annotation_ids(conn, project_structure, tmp_path):
    image_info = project_structure[2]
    im_id = image_info[0][1]
    
    d = tmp_path / "input"
    d.mkdir()
    file_path = d / "hello.txt"
    file_path.write_text("hello world!")
    file_ann = str(file_path)
    ns = "jax.org/omeroutils/tests/v0"
    file_ann_id = ezomero.post_file_annotation(conn, "Image", im_id, file_ann, ns)
    file_ann_id2 = ezomero.post_file_annotation(conn, "Image", im_id, file_ann, ns)
    file_ann_id3 = ezomero.post_file_annotation(conn, "Image", im_id, file_ann, ns)
    ns2 = "different namespace"
    file_ann_id4 = ezomero.post_file_annotation(conn, "Image", im_id, file_ann, ns2)
    file_ann_ids = ezomero.get_file_annotation_ids(conn, "Image", im_id, ns=ns)

    good_ids = [file_ann_id, file_ann_id2, file_ann_id3]
    assert all([mid in file_ann_ids for mid in good_ids])
    assert file_ann_id4 not in file_ann_ids
    conn.deleteObjects("Annotation",
                       [file_ann_id, file_ann_id2, file_ann_id3, file_ann_id4],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)


def test_get_group_id(conn):
    gid = ezomero.get_group_id(conn, 'system')
    assert gid == 0
    gid = ezomero.get_group_id(conn, 'user')
    assert gid == 1
    gid = ezomero.get_group_id(conn, 'guest')
    assert gid == 2

def test_get_user_id(conn, users_groups):

    # test straight usage
    username = users_groups[1][0][0] #test_user1
    uid = users_groups[1][0][1]
    user = ezomero.get_user_id(conn, username)
    assert user == uid 

    # test invalid input
    user = ezomero.get_user_id(conn, "9999999999")
    assert user == None 

    # test cross-group 
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    target_username = users_groups[1][2][0] #test_user3
    target_uid = users_groups[1][2][1]
    user = ezomero.get_user_id(current_conn, target_username)
    assert user == target_uid
    current_conn.close()





# Test puts
###########

def test_put_map_annotation(conn, project_structure, users_groups):
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    image_info = project_structure[2]
    im_id = image_info[0][1]
    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    kv = {"key1": "changed1",
          "key2": "value2"}
    ezomero.put_map_annotation(conn, map_ann_id, kv)
    kv_pairs = ezomero.get_map_annotation(conn, map_ann_id)
    assert kv_pairs['key1'] == kv['key1']
    

    # test cross-group
    kv = {"key1": "value1",
          "key2": "value2"}
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id2 = image_info[2][1] #im2, in test_group_2
    map_ann_id2 = ezomero.post_map_annotation(current_conn, "Image", im_id2, kv, ns)
    print(map_ann_id2)
    kv = {"key1": "changed1",
          "key2": "value2"}
    ezomero.put_map_annotation(current_conn, map_ann_id2, kv)
    kv_pairs = ezomero.get_map_annotation(current_conn, map_ann_id2)
    assert kv_pairs['key1'] == kv['key1']
    current_conn.close()

    # test cross-group, across_groups unset
    kv = {"key1": "value1",
          "key2": "value2"}
    username = users_groups[1][0][0] #test_user1
    groupname = users_groups[0][0][0] #test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1] #im2, in test_group_2
    map_ann_id3 = ezomero.post_map_annotation(current_conn, "Image", im_id3, kv, ns)
    print(map_ann_id3)
    kv_changed = {"key1": "changed1",
          "key2": "value2"}
    with pytest.raises(ValueError):
        ezomero.put_map_annotation(current_conn, map_ann_id3, kv_changed, across_groups=False)
    kv_pairs = ezomero.get_map_annotation(current_conn, map_ann_id3)
    assert kv_pairs['key1'] == kv['key1']
    current_conn.close()


    # test non-existent ID
    with pytest.raises(ValueError):
        ezomero.put_map_annotation(conn, 9999999, kv)


    conn.deleteObjects("Annotation",
                       [map_ann_id, map_ann_id2],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
