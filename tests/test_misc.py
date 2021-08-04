import ezomero
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

    proj3_tag_only_im_ids = ezomero.filter_by_tag_value(conn, proj3_all_im_ids,
                                                        'test_tag_filter')

    assert set(proj3_tag_only_im_ids) == set([im3_id])

    conn.deleteObjects("Annotation",
                       [tag_id],
                       deleteAnns=True,
                       deleteChildren=True,
                       wait=True)
    conn.SERVICE_OPTS.setOmeroGroup(current_group)