from attr import dataclass
import pytest
import ezomero

# Test puts
###########


def test_put_map_annotation(conn, project_structure, users_groups):
    kv = {"key1": "value1",
          "key2": "value2"}
    ns = "jax.org/omeroutils/tests/v0"

    # test sanitized input
    with pytest.raises(TypeError):
        _ = ezomero.put_map_annotation(conn, '10', kv)
    with pytest.raises(ValueError):
        _ = ezomero.put_map_annotation(conn, 99999999, kv)

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
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id2 = image_info[2][1]  # im2, in test_group_2
    map_ann_id2 = ezomero.post_map_annotation(current_conn, "Image", im_id2,
                                              kv, ns)
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
    username = users_groups[1][0][0]  # test_user1
    groupname = users_groups[0][0][0]  # test_group_1
    current_conn = conn.suConn(username, groupname)
    im_id3 = image_info[2][1]  # im2, in test_group_2
    map_ann_id3 = ezomero.post_map_annotation(current_conn, "Image", im_id3,
                                              kv, ns)
    print(map_ann_id3)
    kv_changed = {"key1": "changed1",
                  "key2": "value2"}
    with pytest.raises(ValueError):
        ezomero.put_map_annotation(current_conn, map_ann_id3, kv_changed,
                                   across_groups=False)
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
