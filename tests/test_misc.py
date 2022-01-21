import ezomero
import pytest
from omero.gateway import PlateWrapper
from omero.model import PlateI
from omero.gateway import TagAnnotationWrapper


def test_filter_by_tag_value(conn, project_structure, users_groups):
    proj3_id = project_structure[0][3][1]
    im3_id = project_structure[2][3][1]
    group2_id = users_groups[0][1][1]

    current_group = conn.getGroupFromContext().getId()
    conn.SERVICE_OPTS.setOmeroGroup(group2_id)
    tag_ann = TagAnnotationWrapper(conn)
    tag_ann.setValue('test_tag_filter')
    tag_ann.save()
    tag_id = tag_ann.getId()

    im = conn.getObject('Image', im3_id)
    im.linkAnnotation(tag_ann)

    proj3_all_im_ids = ezomero.get_image_ids(conn, project=proj3_id)

    with pytest.raises(TypeError):
        _ = ezomero.filter_by_tag_value(conn, 10, 'test_tag_filter')
    with pytest.raises(TypeError):
        _ = ezomero.filter_by_tag_value(conn, [10], 10)

    proj3_tag_only_im_ids = ezomero.filter_by_tag_value(conn, proj3_all_im_ids,
                                                        'test_tag_filter')

    assert set(proj3_tag_only_im_ids) == set([im3_id])

    conn.deleteObjects("Annotation",
                       [tag_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
    conn.SERVICE_OPTS.setOmeroGroup(current_group)


def test_filter_by_kvpair(conn, project_structure):
    proj3_id = project_structure[0][3][1]
    im3_id = project_structure[2][3][1]

    current_conn = conn.suConn('test_user1', 'test_group_2')

    kv_dict = {'testkey': 'testvalue',
               'testkey2': 'testvalue2'}

    ma_id = ezomero.post_map_annotation(current_conn, 'Image', im3_id,
                                        kv_dict=kv_dict, ns='test')

    proj3_all_im_ids = ezomero.get_image_ids(current_conn, project=proj3_id)

    with pytest.raises(TypeError):
        _ = ezomero.filter_by_kv(conn, 10, 'test', 'test')
    with pytest.raises(TypeError):
        _ = ezomero.filter_by_kv(conn, [10], 10, 'test')
    with pytest.raises(TypeError):
        _ = ezomero.filter_by_kv(conn, [10], 'test', 10)

    proj3_kv_only_im_ids = ezomero.filter_by_kv(current_conn,
                                                proj3_all_im_ids,
                                                key='testkey2',
                                                value='testvalue2')

    assert set(proj3_kv_only_im_ids) == set([im3_id])

    current_conn.deleteObjects("Annotation",
                               [ma_id],
                               deleteAnns=True,
                               deleteChildren=True,
                               wait=True)
    current_conn.close()


def test_prints(conn, project_structure, users_groups):
    pid = project_structure[0][0][1]
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    ezomero.print_datasets(conn, project=pid)
    with pytest.raises(TypeError):
        ezomero.print_datasets(conn, '10')
    ezomero.print_datasets(conn)
    ezomero.print_projects(conn)
    ezomero.print_groups(conn)
    current_conn = conn.suConn(username, groupname)
    ezomero.print_groups(current_conn)
    image_info = project_structure[2]
    im_id = image_info[0][1]
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"
    map_ann_id = ezomero.post_map_annotation(conn, "Image", im_id, kv, ns)
    ezomero.print_map_annotation(conn, map_ann_id)
    with pytest.raises(TypeError):
        ezomero.print_map_annotation(conn, '10')
    conn.deleteObjects("Annotation", [map_ann_id],
                       deleteAnns=True, deleteChildren=True, wait=True)
    current_conn.close()


def test_set_group(conn, users_groups):
    print(users_groups)
    username = users_groups[1][2][0]  # test_user3
    groupname = users_groups[0][1][0]  # test_group_2
    current_conn = conn.suConn(username, groupname)
    with pytest.raises(TypeError):
        _ = ezomero.set_group(current_conn, '10')
    new_group = users_groups[0][0][1]  # test_group_1
    ret = ezomero.set_group(current_conn, int(new_group))
    assert ret is False
    current_conn.close()

    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    new_group = users_groups[0][1][1]  # test_group_2
    ret = ezomero.set_group(current_conn, int(new_group))
    assert ret is True
    current_conn.close()


def test_link_images_to_dataset(conn, image_fixture):
    ds_id = ezomero.post_dataset(conn, 'test dataset')
    im_id1 = ezomero.post_image(conn,
                                image_fixture,
                                'test image')
    im_id2 = ezomero.post_image(conn,
                                image_fixture,
                                'test image')
    with pytest.raises(TypeError):
        _ = ezomero.link_images_to_dataset(conn, 10, ds_id)
    with pytest.raises(TypeError):
        _ = ezomero.link_images_to_dataset(conn, [im_id1, im_id2], '10')
    _ = ezomero.link_images_to_dataset(conn, [im_id1, im_id2], ds_id)
    im_ids = ezomero.get_image_ids(conn, dataset=ds_id)
    assert im_id1 in im_ids
    assert im_id2 in im_ids
    conn.deleteObjects("Image",
                       [im_id1, im_id2],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
    conn.deleteObjects("Dataset",
                       [ds_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)


def test_link_datasets_to_project(conn):
    ds_id1 = ezomero.post_dataset(conn, 'test1')
    ds_id2 = ezomero.post_dataset(conn, 'test2')
    pj_id = ezomero.post_project(conn, 'test project')
    with pytest.raises(TypeError):
        _ = ezomero.link_datasets_to_project(conn, 10, pj_id)
    with pytest.raises(TypeError):
        _ = ezomero.link_datasets_to_project(conn, [ds_id1, ds_id2], 'test')

    _ = ezomero.link_datasets_to_project(conn, [ds_id1, ds_id2], pj_id)
    pj = conn.getObject('Project', pj_id)
    ds = pj.listChildren()
    ds_ids = []
    for d in ds:
        ds_ids.append(d.id)
    assert ds_id1 in ds_ids
    assert ds_id2 in ds_ids
    conn.deleteObjects("Dataset",
                       [ds_id1, ds_id2],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
    conn.deleteObjects("Project",
                       [pj_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)


def test_link_plates_to_screen(conn, image_fixture):
    sc_id = ezomero.post_screen(conn, 'test screen')
    plate_name = "testplate1"
    plate = PlateWrapper(conn, PlateI())
    plate.setName(plate_name)
    plate.save()
    pl_id1 = plate.getId()
    plate_name2 = "testplate2"
    plate2 = PlateWrapper(conn, PlateI())
    plate2.setName(plate_name2)
    plate2.save()
    pl_id2 = plate2.getId()
    with pytest.raises(TypeError):
        _ = ezomero.link_plates_to_screen(conn, 10, sc_id)
    with pytest.raises(TypeError):
        _ = ezomero.link_plates_to_screen(conn, [pl_id1, pl_id2], '10')
    _ = ezomero.link_plates_to_screen(conn, [pl_id1, pl_id2], sc_id)
    pj = conn.getObject('Screen', sc_id)
    pl = pj.listChildren()
    pl_ids = []
    for p in pl:
        pl_ids.append(p.id)
    assert pl_id1 in pl_ids
    assert pl_id2 in pl_ids
    conn.deleteObjects("Plate",
                       [pl_id1, pl_id2],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
    conn.deleteObjects("Screen",
                       [sc_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
