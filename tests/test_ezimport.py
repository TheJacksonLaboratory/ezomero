import ezomero
from io import StringIO

# Test imports


def test_ezimport(conn, monkeypatch):

    # test simple import, single file
    fpath = "tests/data/test_pyramid.ome.tif"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath)
    assert len(id) == 1
    conn.deleteObjects("Image", id)

#     # test simple import, multifile/multi-image
    fpath = "tests/data/vsi-ets-test-jpg2k.vsi"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath)
    assert len(id) == 2

#     # test simple import, new orphan dataset
    fpath = "tests/data/test_pyramid.ome.tif"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath, dataset="test_ds")
    assert len(id) == 1
    ds_id = ezomero.get_dataset_ids(conn)[-1]
    im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
    assert len(im_ids) == 1
    assert im_ids[0] == id[-1]

#     # test simple import, existing dataset
    fpath = "tests/data/test_pyramid.ome.tif"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath, dataset=ds_id)
    im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
    assert len(im_ids) == 2
    assert im_ids[-1] == id[-1]
    conn.deleteObjects("Dataset", [ds_id], deleteChildren=True)

#     # test simple import, new project
    fpath = "tests/data/test_pyramid.ome.tif"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath,
                          project="test_proj", dataset="test_ds")
    assert len(id) == 1
    proj_id = ezomero.get_project_ids(conn)[-1]
    ds_id = ezomero.get_dataset_ids(conn, project=proj_id)[-1]
    im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
    assert len(im_ids) == 1
    assert im_ids[0] == id[-1]

#     # test simple import, existing project, new dataset
    fpath = "tests/data/test_pyramid.ome.tif"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath,
                          project=proj_id, dataset="new_test_ds")
    ds_ids = ezomero.get_dataset_ids(conn, project=proj_id)
    im_ids = ezomero.get_image_ids(conn, dataset=ds_ids[-1])
    assert len(ds_ids) == 2
    assert len(im_ids) == 1
    assert im_ids[0] == id[-1]

#     # test simple import, existing project, existing dataset
    fpath = "tests/data/test_pyramid.ome.tif"
    str_input = ["omero", 'import',
                 '-k', conn.getSession().getUuid().val,
                 '-s', conn.host,
                 '-p', str(conn.port),
                 fpath, "\n"]
    io = StringIO(" ".join(str_input))
    monkeypatch.setattr('sys.stdin', io)
    id = ezomero.ezimport(conn, fpath,
                          project=proj_id, dataset=ds_id)
    ds_id = ezomero.get_dataset_ids(conn, project=proj_id)[0]
    im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
    assert len(im_ids) == 2
    assert im_ids[-1] == id[-1]

    conn.deleteObjects("Project", [proj_id], deleteChildren=True)
