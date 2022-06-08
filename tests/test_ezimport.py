# import ezomero
# import pytest


# This file is a placeholder for the tests we would LIKE to run
# (if running any tests that involve CLI was easier)

# Test imports


# def test_ezimport(self, conn):

#     # test simple import, single file
#     id = ezomero.ezimport(conn, "tests/data/test_pyramid.ome.tif")
#     assert len(id) == 1

#     # test simple import, multifile/multi-image
#     id = ezomero.ezimport(conn, "tests/data/vsi-ets-test-jpg2k.vsi")
#     assert len(id) == 2

#     # test simple import, new orphan dataset
#     id = ezomero.ezimport(conn, "tests/data/test_pyramid.ome.tif",
#                             dataset="test_ds")
#     assert len(id) == 1
#     ds_id = ezomero.get_dataset_ids(conn)[-1]
#     im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
#     assert len(im_ids) == 1
#     assert im_ids[0] == id

#     # test simple import, existing dataset
#     id = ezomero.ezimport(conn, "tests/data/test_pyramid.ome.tif",
#                             dataset=ds_id)
#     im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
#     assert len(im_ids) == 2
#     assert im_ids[-1] == id

#     # test simple import, new project
#     id = ezomero.ezimport(conn, "tests/data/test_pyramid.ome.tif",
#                             project="test_proj", dataset="test_ds")
#     assert len(id) == 1
#     proj_id = ezomero.get_project_ids(conn)[-1]
#     ds_id = ezomero.get_dataset_ids(conn, project=proj_id)[-1]
#     im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
#     assert len(im_ids) == 1
#     assert im_ids[0] == id

#     # test simple import, existing project, new dataset
#     id = ezomero.ezimport(conn, "tests/data/test_pyramid.ome.tif",
#                             project=proj_id, dataset="new_test_ds")
#     ds_ids = ezomero.get_dataset_ids(conn, project=proj_id)
#     im_ids = ezomero.get_image_ids(conn, dataset=ds_ids[-1])
#     assert len(ds_ids) == 2
#     assert len(im_ids) == 1
#     assert im_ids[0] == id

#     # test simple import, existing project, existing dataset
#     id = ezomero.ezimport(conn, "tests/data/test_pyramid.ome.tif",
#                             project=proj_id, dataset=ds_id)
#     ds_id = ezomero.get_dataset_ids(conn, project=proj_id)[-1]
#     im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
#     assert len(im_ids) == 2
#     assert im_ids[-1] == id
