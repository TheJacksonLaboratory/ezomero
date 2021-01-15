import pytest
import numpy as np
import ezomero


def test_omero_connection(conn, omero_params):
    assert conn.getUser().getName() == omero_params[0]


# Test posts
############
def test_post_dataset(conn, project_structure, timestamp):
    # Orphaned dataset, with descripion
    ds_test_name = 'test_post_dataset_' + timestamp
    did = ezomero.post_dataset(conn, ds_test_name, description='New test')
    assert conn.getObject("Dataset", did).getName() == ds_test_name
    assert conn.getObject("Dataset", did).getDescription() == "New test"

    # Dataset in project, no description
    ds_test_name2 = 'test_post_dataset2_' + timestamp
    pid = project_structure['proj']
    did2 = ezomero.post_dataset(conn, ds_test_name2, project_id=pid)
    ds = conn.getObjects("Dataset", opts={'project': pid})
    ds_names = [d.getName() for d in ds]
    assert ds_test_name2 in ds_names
    conn.deleteObjects("Dataset", [did, did2], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_image(conn, project_structure, timestamp, image_fixture):
    # Post image in dataset
    image_name = 'test_post_image_' + timestamp
    im_id = ezomero.post_image(conn, image_fixture, image_name,
                               description='This is an image',
                               dataset_id=project_structure["ds"])
    assert conn.getObject("Image", im_id).getName() == image_name

    # Post orphaned image
    im_id2 = ezomero.post_image(conn, image_fixture, image_name)
    assert conn.getObject("Image", im_id2).getName() == image_name
    conn.deleteObjects("Image", [im_id, im_id2], deleteAnns=True,
                       deleteChildren=True, wait=True)


def test_post_get_map_annotation(conn, project_structure):
    # This test both ezomero.post_map_annotation and ezomero.get_map_annotation
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    im_id = project_structure['im']
    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    kv_pairs = ezomero.get_map_annotation(conn, map_ann_id)
    assert kv_pairs["key2"] == "value2"
    conn.deleteObjects("Annotation", [map_ann_id], deleteAnns=True,
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

def test_get_image(conn, project_structure):
    im_id = project_structure['im']
    # test default
    im, im_arr = ezomero.get_image(conn, im_id)
    assert im.getId() == im_id
    assert im_arr.shape == (1, 20, 201, 200, 3)
    assert im.getPixelsType() == im_arr.dtype

    # test xyzct
    im, im_arr = ezomero.get_image(conn, im_id, xyzct=True)
    assert im_arr.shape == (200, 201, 20, 3, 1)

    # test no pixels
    im, im_arr = ezomero.get_image(conn, im_id, no_pixels=True)
    assert im_arr is None

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

    # test that IndexError comes up when pad=False
    with pytest.raises(IndexError):
        im, im_arr = ezomero.get_image(conn, im_id,
                                       start_coords=(195, 195, 18, 0, 0),
                                       axis_lengths=(10, 10, 3, 4, 3),
                                       pad=False)


def test_get_image_ids(conn, project_structure):
    # Based on dataset ID
    main_ds_id = project_structure['ds']
    im_id = project_structure['im']
    im_ids = ezomero.get_image_ids(conn, dataset=main_ds_id)
    assert im_ids[0] == im_id
    assert len(im_ids) == 1

    # Based on well ID
    well_id = project_structure['well']
    im_id1 = project_structure['im1']
    im_ids = ezomero.get_image_ids(conn, well=well_id)
    assert im_ids[0] == im_id1
    assert len(im_ids) == 1

    # Need to add test for orphans

    # Return nothing on bad input
    im_ids2 = ezomero.get_image_ids(conn, dataset=999999)
    assert len(im_ids2) == 0


def test_get_map_annotation_ids(conn, project_structure):
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    im_id = project_structure['im']
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


def test_get_group_id(conn):
    gid = ezomero.get_group_id(conn, 'system')
    assert gid == 0
    gid = ezomero.get_group_id(conn, 'user')
    assert gid == 1
    gid = ezomero.get_group_id(conn, 'guest')
    assert gid == 2


# Test puts
###########

def test_put_map_annotation(conn, project_structure):
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    im_id = project_structure['im']
    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    kv = {"key1": "changed1",
          "key2": "value2"}
    ezomero.put_map_annotation(conn, map_ann_id, kv)
    kv_pairs = ezomero.get_map_annotation(conn, map_ann_id)
    assert kv_pairs['key1'] == kv['key1']
    conn.deleteObjects("Annotation",
                       [map_ann_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
