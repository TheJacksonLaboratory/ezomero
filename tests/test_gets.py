from attr import dataclass
import pytest
import numpy as np
import ezomero
from omero.gateway import TagAnnotationWrapper

# Test gets
###########


def test_get_image(conn, project_structure, users_groups, pyramid_fixture):
    image_info = project_structure[2]
    im_id = image_info[0][1]
    pyr_id = ezomero.get_image_ids(conn)[-1]
    # test input sanitizing
    with pytest.raises(TypeError):
        _, _ = ezomero.get_image(conn, im_id, start_coords=1)
    with pytest.raises(ValueError):
        _, _ = ezomero.get_image(conn, im_id,
                                 start_coords=[0, 0, 0])
    with pytest.raises(TypeError):
        _, _ = ezomero.get_image(conn, im_id, axis_lengths=1)
    with pytest.raises(ValueError):
        _, _ = ezomero.get_image(conn, im_id,
                                 axis_lengths=[0, 0, 0])
    with pytest.raises(TypeError):
        _, _ = ezomero.get_image(conn, None)
    with pytest.raises(TypeError):
        _, _ = ezomero.get_image(conn, '1')
    with pytest.raises(TypeError):
        _, _ = ezomero.get_image(conn, im_id, pyramid_level='1')
    with pytest.raises(TypeError):
        _, _ = ezomero.get_image(conn, im_id, dim_order=1)
    with pytest.raises(ValueError):
        _, _ = ezomero.get_image(conn, im_id, dim_order='abxyz')

    # test default
    im, im_arr = ezomero.get_image(conn, im_id)
    assert im.getId() == im_id
    assert im_arr.shape == (1, 20, 201, 200, 3)
    assert im.getPixelsType() == im_arr.dtype
    im, im_arr = ezomero.get_image(conn, pyr_id,
                                   pyramid_level=2)
    assert im.getId() == pyr_id
    assert im_arr.shape == (1, 1, 4, 4, 1)
    assert im.getPixelsType() == im_arr.dtype

    # test non-existent id

    im_id2 = 999999999
    im2, im_arr2 = ezomero.get_image(conn, im_id2)
    assert im2 is None
    assert im_arr2 is None

    # test cross-group valid
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1]  # im2, in test_group_2
    im3, im_arr3 = ezomero.get_image(current_conn, im_id3)
    assert im3.getId() == im_id3
    assert im_arr3.shape == (1, 20, 201, 200, 3)
    assert im3.getPixelsType() == im_arr3.dtype
    current_conn.close()

    # test cross-group invalid
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    im_id4 = image_info[1][1]  # im1(in test_group_1)
    im4, im_arr4 = ezomero.get_image(current_conn, im_id4)
    assert im4 is None
    assert im_arr4 is None
    current_conn.close()

    # test cross-group valid, across_groups unset
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id5 = image_info[2][1]  # im2, in test_group_2
    im5, im_arr5 = ezomero.get_image(current_conn, im_id5, across_groups=False)
    assert im5 is None
    assert im_arr5 is None
    current_conn.close()

    # test xyzct
    im, im_arr = ezomero.get_image(conn, im_id, xyzct=True)
    assert im_arr.shape == (200, 201, 20, 3, 1)
    im, im_arr = ezomero.get_image(conn, pyr_id, xyzct=True,
                                   pyramid_level=1)
    assert im_arr.shape == (8, 8, 1, 1, 1)

    # test dim_order
    im, im_arr = ezomero.get_image(conn, im_id, dim_order='czxty')
    assert im_arr.shape == (3, 20, 200, 1, 201)
    im, im_arr = ezomero.get_image(conn, pyr_id, dim_order='zxcyt',
                                   pyramid_level=1)
    assert im_arr.shape == (1, 8, 1, 8, 1)

    # test no pixels
    im, im_arr = ezomero.get_image(conn, im_id, no_pixels=True)
    assert im_arr is None

    # test that IndexError comes up when pad=False
    with pytest.raises(IndexError):
        im, im_arr = ezomero.get_image(conn, im_id,
                                       start_coords=(195, 195, 18, 0, 0),
                                       axis_lengths=(10, 10, 3, 4, 3),
                                       pad=False)
    with pytest.raises(IndexError):
        im, im_arr = ezomero.get_image(conn, pyr_id,
                                       start_coords=(2, 2, 0, 0, 0),
                                       axis_lengths=(10, 10, 3, 4, 3),
                                       pad=False, pyramid_level=1)

    # test crop
    im, im_arr = ezomero.get_image(conn, im_id,
                                   start_coords=(101, 101, 10, 0, 0),
                                   axis_lengths=(10, 10, 3, 3, 1))
    assert im_arr.shape == (1, 3, 10, 10, 3)
    assert np.allclose(im_arr[0, 0, 0, 0, :], [0, 0, 255])
    im, im_arr = ezomero.get_image(conn, pyr_id,
                                   start_coords=(1, 1, 0, 0, 0),
                                   axis_lengths=(5, 5, 1, 1, 1),
                                   pyramid_level=1)
    assert im_arr.shape == (1, 1, 5, 5, 1)

    # test crop with padding
    im, im_arr = ezomero.get_image(conn, im_id,
                                   start_coords=(195, 195, 18, 0, 0),
                                   axis_lengths=(10, 11, 3, 4, 3),
                                   pad=True)
    assert im_arr.shape == (3, 3, 11, 10, 4)
    im, im_arr = ezomero.get_image(conn, pyr_id,
                                   start_coords=(1, 1, 0, 0, 0),
                                   axis_lengths=(8, 10, 1, 2, 1),
                                   pad=True, pyramid_level=1)
    assert im_arr.shape == (1, 1, 10, 8, 2)


def test_get_tag_and_tag_ids(conn, project_structure):
    image_info = project_structure[2]
    im_id = image_info[0][1]
    tag_ann = TagAnnotationWrapper(conn)
    tag_ann.setValue('test_tag')
    tag_ann.save()
    tag_id = tag_ann.getId()
    im = conn.getObject('Image', im_id)
    im.linkAnnotation(tag_ann)
    # Test sanitizing inputs
    with pytest.raises(TypeError):
        _ = ezomero.get_tag_ids(conn, 10, 10)
    with pytest.raises(TypeError):
        _ = ezomero.get_tag_ids(conn, 'Image', '10')
    with pytest.raises(TypeError):
        _ = ezomero.get_tag_ids(conn, 'Image', 10, ns=10)
    with pytest.raises(TypeError):
        _ = ezomero.get_tag(conn, '10')
    tag_id_from_im = ezomero.get_tag_ids(conn, 'Image', im_id)[0]

    assert tag_id_from_im == tag_id

    tag_text = ezomero.get_tag(conn, tag_id)

    assert tag_text == 'test_tag'

    conn.deleteObjects("Annotation",
                       [tag_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)


def test_get_image_ids(conn, project_structure, screen_structure,
                       users_groups, pyramid_fixture):

    project_info = project_structure[0]
    dataset_info = project_structure[1]
    image_info = project_structure[2]

    # Test orphans (should return at least 1 pyramid)
    orphan_ids = ezomero.get_image_ids(conn)
    assert len(orphan_ids) >= 1

    # Based on project ID (also tests cross-group)
    proj3_id = project_info[3][1]
    im2_id = image_info[2][1]  # im2, belongs to proj3/ds2
    im3_id = image_info[3][1]  # im3, belongs to proj3/ds3
    im4_id = image_info[4][1]  # im4, belongs to proj3/ds3
    proj3_im_ids = ezomero.get_image_ids(conn, project=proj3_id)
    assert set(proj3_im_ids) == set([im2_id, im3_id, im4_id])

    # Based on dataset ID
    ds0_id = dataset_info[0][1]  # Belongs to proj0
    im0_id = image_info[0][1]  # Belongs to ds0
    ds0_im_ids = ezomero.get_image_ids(conn, dataset=ds0_id)
    assert set(ds0_im_ids) == set([im0_id])

    # test cross-group valid
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    ds6_id = dataset_info[6][1]  # dataset 6 in test_group_2
    im6_id = image_info[6][1]  # im6, in ds6
    im7_id = image_info[7][1]  # im7, in ds6
    ds6_im_ids = ezomero.get_image_ids(current_conn, dataset=ds6_id)
    assert set(ds6_im_ids) == set([im6_id, im7_id])
    current_conn.close()

    # test cross-group invalid
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2 (test_user3 is mbr)
    current_conn = conn.suConn(username, groupname)
    ds1_id = dataset_info[1][1]  # ds1, in test_group1 (test_user3 not mbr)
    ds1_im_ids = ezomero.get_image_ids(current_conn, dataset=ds1_id)
    assert not ds1_im_ids
    current_conn.close()

    # test cross-group valid, across_groups unset
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    ds3_id = dataset_info[3][1]  # ds3 in test_group_2
    ds3_im_ids = ezomero.get_image_ids(current_conn, dataset=ds3_id,
                                       across_groups=False)
    assert not ds3_im_ids
    current_conn.close()

    # Return nothing on bad input
    bad_im_ids = ezomero.get_image_ids(conn, dataset=999999)
    assert not bad_im_ids

    # Based on well ID
    well_id = screen_structure[1]
    plate_im_id1 = screen_structure[2]
    well_im_ids = ezomero.get_image_ids(conn, well=well_id)
    assert set(well_im_ids) == set([plate_im_id1])

    # Based on plate ID
    plate_id = screen_structure[0]
    plate_im_id2 = screen_structure[5]
    plate_im_ids = ezomero.get_image_ids(conn, plate=plate_id)
    assert set(plate_im_ids) == set([plate_im_id1, plate_im_id2])


def test_get_project_ids(conn, project_structure, users_groups):

    project_info = project_structure[0]

    proj_ids = ezomero.get_project_ids(conn)
    assert len(proj_ids) == len(project_info)

    # test cross-group valid
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    pj_ids = ezomero.get_project_ids(current_conn)
    assert len(pj_ids) == len(project_info) - 1
    current_conn.close()


def test_get_dataset_ids(conn, project_structure, users_groups):

    project_info = project_structure[0]
    dataset_info = project_structure[1]

    with pytest.raises(TypeError):
        _ = ezomero.get_dataset_ids(conn, project='test')

    # Test orphans
    orphan_ids = ezomero.get_dataset_ids(conn)
    assert len(orphan_ids) == 1

    # Based on project ID (also tests cross-group)
    proj3_id = project_info[3][1]
    ds2_id = dataset_info[2][1]  # im2, belongs to proj3/ds2
    ds3_id = dataset_info[3][1]  # im3, belongs to proj3/ds3
    proj3_ds_ids = ezomero.get_dataset_ids(conn, project=proj3_id)
    assert set(proj3_ds_ids) == set([ds2_id, ds3_id])

    # Return nothing on bad input
    bad_im_ids = ezomero.get_dataset_ids(conn, project=999999)
    assert not bad_im_ids


def test_get_image_ids_params(conn):
    with pytest.raises(ValueError):
        _ = ezomero.get_image_ids(conn, project=1, plate=2)
    with pytest.raises(ValueError):
        _ = ezomero.get_image_ids(conn, dataset=1, well=2)
    with pytest.raises(TypeError):
        _ = ezomero.get_image_ids(conn, dataset='test')
    with pytest.raises(TypeError):
        _ = ezomero.get_image_ids(conn, project='test')
    with pytest.raises(TypeError):
        _ = ezomero.get_image_ids(conn, well='test')
    with pytest.raises(TypeError):
        _ = ezomero.get_image_ids(conn, plate='test')


def test_get_map_annotation_and_ids(conn, project_structure):
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    image_info = project_structure[2]
    im_id = image_info[0][1]

    # Test sanitizing inputs
    with pytest.raises(TypeError):
        _ = ezomero.get_map_annotation_ids(conn, 10, 10)
    with pytest.raises(TypeError):
        _ = ezomero.get_map_annotation_ids(conn, 'Image', '10')
    with pytest.raises(TypeError):
        _ = ezomero.get_map_annotation_ids(conn, 'Image', 10, ns=10)

    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    map_ann_id2 = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    map_ann_id3 = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    ns2 = "different namespace"
    map_ann_id4 = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns2)
    map_ann_ids = ezomero.get_map_annotation_ids(conn, "Image", im_id, ns=ns)

    good_ids = [map_ann_id, map_ann_id2, map_ann_id3]
    assert all([mid in map_ann_ids for mid in good_ids])
    assert map_ann_id4 not in map_ann_ids

    # Test sanitizing input
    with pytest.raises(TypeError):
        _ = ezomero.get_map_annotation(conn, '10')
    mpann = ezomero.get_map_annotation(conn, map_ann_ids[0])
    assert mpann == kv
    conn.deleteObjects("Annotation",
                       [map_ann_id, map_ann_id2, map_ann_id3, map_ann_id4],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)


def test_get_file_annotation_and_ids(conn, project_structure, tmp_path):
    image_info = project_structure[2]
    im_id = image_info[0][1]

    d = tmp_path / "input"
    d.mkdir()
    file_path = d / "hello.txt"
    file_path.write_text("hello world!")
    file_ann = str(file_path)
    ns = "jax.org/omeroutils/tests/v0"
    file_ann_id = ezomero.post_file_annotation(conn, "Image", im_id,
                                               file_ann, ns)
    file_ann_id2 = ezomero.post_file_annotation(conn, "Image", im_id,
                                                file_ann, ns)
    file_ann_id3 = ezomero.post_file_annotation(conn, "Image", im_id,
                                                file_ann, ns)
    ns2 = "different namespace"
    file_ann_id4 = ezomero.post_file_annotation(conn, "Image", im_id,
                                                file_ann, ns2)

    # Test sanitizing inputs
    with pytest.raises(TypeError):
        _ = ezomero.get_file_annotation_ids(conn, 10, 10)
    with pytest.raises(TypeError):
        _ = ezomero.get_file_annotation_ids(conn, 'Image', '10')
    with pytest.raises(TypeError):
        _ = ezomero.get_file_annotation_ids(conn, 'Image', 10, ns=10)
    with pytest.raises(TypeError):
        _ = ezomero.get_file_annotation(conn, '10')
    file_ann_ids = ezomero.get_file_annotation_ids(conn, "Image", im_id, ns=ns)

    good_ids = [file_ann_id, file_ann_id2, file_ann_id3]
    assert all([mid in file_ann_ids for mid in good_ids])
    assert file_ann_id4 not in file_ann_ids
    fann = ezomero.get_file_annotation(conn, file_ann_ids[0],
                                       folder_path='/tmp/')
    assert fann == '/tmp/hello.txt'
    conn.deleteObjects("Annotation",
                       [file_ann_id, file_ann_id2, file_ann_id3, file_ann_id4],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)


def test_get_well_id(conn, screen_structure):
    plate_id = screen_structure[0]
    well_id = screen_structure[1]
    well2_id = screen_structure[4]
    well_id_result = ezomero.get_well_id(conn, plate_id, row=1, column=1)
    well2_id_result = ezomero.get_well_id(conn, plate_id, row=2, column=2)
    assert well_id == well_id_result
    assert well2_id == well2_id_result
    assert ezomero.get_well_id(conn, plate_id, row=5, column=9) is None


def test_get_well_id_params(conn):
    with pytest.raises(TypeError):
        _ = ezomero.get_well_id(conn, "Plate name", row=0, column=0)
    with pytest.raises(TypeError):
        _ = ezomero.get_well_id(conn, 9999, row='A', column=0)
    with pytest.raises(TypeError):
        _ = ezomero.get_well_id(conn, 9999, row=0, column='B')


def test_get_group_id(conn):
    gid = ezomero.get_group_id(conn, 'system')
    assert gid == 0
    gid = ezomero.get_group_id(conn, 'user')
    assert gid == 1
    gid = ezomero.get_group_id(conn, 'guest')
    assert gid == 2
    with pytest.raises(TypeError):
        _ = ezomero.get_group_id(conn, 10)
    gid = ezomero.get_group_id(conn, 'fake_group')
    assert gid is None


def test_get_user_id(conn, users_groups):

    # test straight usage
    username = users_groups[1][0][0]  # test_user1
    uid = users_groups[1][0][1]
    user = ezomero.get_user_id(conn, username)
    assert user == uid

    # test invalid input
    user = ezomero.get_user_id(conn, "9999999999")
    assert user is None

    # test sanitizing input
    with pytest.raises(TypeError):
        _ = ezomero.get_user_id(conn, 10)

    # test cross-group
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    target_username = users_groups[1][2][0]  # test_user3
    target_uid = users_groups[1][2][1]
    user = ezomero.get_user_id(current_conn, target_username)
    assert user == target_uid
    current_conn.close()


def test_get_roi_ids(conn, project_structure, roi_fixture, users_groups):

    # test input sanitizing
    with pytest.raises(TypeError):
        _ = ezomero.get_roi_ids(conn, '9999')

    # test normal usage
    image_info = project_structure[2]
    im_id = image_info[0][1]
    roi_id = ezomero.post_roi(conn, im_id,
                              shapes=roi_fixture['shapes'],
                              name=roi_fixture['name'],
                              description=roi_fixture['desc'],
                              fill_color=roi_fixture['fill_color'],
                              stroke_color=roi_fixture['stroke_color'],
                              stroke_width=roi_fixture['stroke_width'])
    return_ids = ezomero.get_roi_ids(conn, im_id)
    assert roi_id in return_ids

    # Test getting from an invalid cross-group
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    empty_ret = ezomero.get_roi_ids(current_conn, im_id)
    assert empty_ret == []
    current_conn.close()

    # test getting from invalid IDs
    empty_ret = ezomero.get_roi_ids(conn, 999999999)
    assert empty_ret == []

    conn.deleteObjects("Roi", [roi_id], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_get_shape_and_get_shape_ids(conn, project_structure,
                                     roi_fixture, users_groups):
    # test input sanitizing
    with pytest.raises(TypeError):
        _ = ezomero.get_shape_ids(conn, '9999')
    with pytest.raises(TypeError):
        _ = ezomero.get_shape(conn, '9999')

    # test normal usage
    image_info = project_structure[2]
    im_id = image_info[0][1]
    roi_id = ezomero.post_roi(conn, im_id,
                              shapes=roi_fixture['shapes'],
                              name=roi_fixture['name'],
                              description=roi_fixture['desc'],
                              fill_color=roi_fixture['fill_color'],
                              stroke_color=roi_fixture['stroke_color'],
                              stroke_width=roi_fixture['stroke_width'])
    shape_ids = ezomero.get_shape_ids(conn, roi_id)
    assert len(shape_ids) == len(roi_fixture['shapes'])
    for i in range(len(shape_ids)):
        shape, fill, stroke, width = ezomero.get_shape(conn, shape_ids[i])
        assert hasattr(shape, 'label')
        assert fill == roi_fixture['fill_color']
        assert stroke == roi_fixture['stroke_color']
        assert width == roi_fixture['stroke_width']

    # Test getting from an invalid cross-group
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    empty_ret = ezomero.get_shape_ids(current_conn, roi_id)
    assert empty_ret is None
    current_conn.close()

    # test getting from invalid IDs
    empty_ret = ezomero.get_shape_ids(conn, 999999999)
    assert empty_ret is None
    with pytest.raises(AttributeError):
        _, _, _, _ = ezomero.get_shape(conn, 99999999)

    conn.deleteObjects("Roi", [roi_id], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_get_original_filepaths(conn, project_structure):
    # we should probably build a way to test this...
    image_info = project_structure[2]
    im_id = image_info[0][1]

    # test sanitizing input
    with pytest.raises(TypeError):
        _ = ezomero.get_original_filepaths(conn, '10')
    with pytest.raises(ValueError):
        _ = ezomero.get_original_filepaths(conn, 10, fpath=10)

    opath = ezomero.get_original_filepaths(conn, im_id)
    assert opath == []
    opath = ezomero.get_original_filepaths(conn, im_id, fpath='client')
    assert opath == []


def test_get_pyramid_levels(conn, pyramid_fixture):
    im_id = ezomero.get_image_ids(conn)[-1]
    lvls = ezomero.get_pyramid_levels(conn, im_id)
    assert len(lvls) == 3
    assert lvls[0] == (16, 16)
