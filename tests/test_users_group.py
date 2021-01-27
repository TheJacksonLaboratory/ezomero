import ezomero


def test_ug(conn, users_groups):
    group_info, user_info = users_groups
    gid = ezomero.get_group_id(conn, group_info[0][0])
    assert gid is not None
    assert group_info[0][1] == gid
    uid = ezomero.get_user_id(conn, user_info[0][0])
    assert user_info[0][1] == uid
