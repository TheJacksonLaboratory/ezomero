from omero.sys import Parameters
from omero.rtypes import rstring
from omero.model import DatasetImageLinkI, ImageI, ExperimenterI
from omero.model import DatasetI, ProjectI, ProjectDatasetLinkI


# filters
def filter_by_filename(conn, im_ids, imported_filename):
    """Filter list of image ids by originalFile name

    Sometimes we know the filename of an image that has been imported into
    OMERO but not necessarily the image ID. This is frequently the case when
    we want to annotate a recently imported image. This funciton will help
    to filter a list of image IDs to only those associated with a particular
    filename.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    im_ids : list of int
        List of OMERO image IDs.
    imported_filename : str
        The full filename (with extension) of the file whose OMERO image
        we are looking for. NOT the path of the image.

    Returns
    -------
    filtered_im_ids : list of int
        Filtered list of images with originalFile name matching
        ``imported_filename``.

    Notes
    -----
    This function should be used as a filter on an image list that has been
    already narrowed down as much as possible. Note that many different images
    in OMERO may share the same filename (e.g., image.tif).

    Examples
    --------
    >>> im_ids = get_image_ids(conn, dataset=303)
    >>> im_ids = filter_by_filename(conn, im_ids, "feb_2020.tif")]
    """

    q = conn.getQueryService()
    params = Parameters()
    params.map = {"oname": rstring(imported_filename)}
    results = q.projection(
        "SELECT i.id FROM Image i"
        " JOIN i.fileset fs"
        " JOIN fs.usedFiles u"
        " JOIN u.originalFile o"
        " WHERE o.name=:oname",
        params,
        conn.SERVICE_OPTS
        )
    im_id_matches = [r[0].val for r in results]

    return list(set(im_ids) & set(im_id_matches))


# linking functions
def link_images_to_dataset(conn, image_ids, dataset_id):
    """Link images to the specified dataset.

    Nothing is returned by this function.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    im_ids : list of int
        List of OMERO image IDs.
    dataset_id : int
        Id of dataset to which images will be linked.
    """
    user_id = _get_current_user(conn)
    for im_id in image_ids:
        link = DatasetImageLinkI()
        link.setParent(DatasetI(dataset_id, False))
        link.setChild(ImageI(im_id, False))
        link.details.owner = ExperimenterI(user_id, False)
        conn.getUpdateService().saveObject(link, conn.SERVICE_OPTS)


def link_datasets_to_project(conn, dataset_ids, project_id):
    """Link datasets to the specified project.

    Nothing is returned by this function.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    im_ids : list of int
        List of OMERO Dataset Ids.
    dataset_id : int
        Id of Project to which Datasets will be linked.
    """
    user_id = _get_current_user(conn)
    for did in dataset_ids:
        link = ProjectDatasetLinkI()
        link.setParent(ProjectI(project_id, False))
        link.setChild(DatasetI(did, False))
        link.details.owner = ExperimenterI(user_id, False)
        conn.getUpdateService().saveObject(link, conn.SERVICE_OPTS)


def _get_current_user(conn):
    userid = conn.SERVICE_OPTS.getOmeroUser()
    if userid is None:
        userid = conn.getUserId()
    return userid


# prints
def print_map_annotation(conn, map_ann_id):
    """Print some information and value of a map annotation.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    map_ann_id : int
        Id of the MapAnnotation to be displayed.
    """
    map_ann = conn.getObject('MapAnnotation', map_ann_id)
    print(f'Map Annotation: {map_ann_id}')
    print(f'Namespace: {map_ann.getNs()}')
    print('Key-Value Pairs:')
    for k, v in map_ann.getValue():
        print(f'\t{k}:\t{v}')


def print_groups(conn):
    """Print all Groups with IDs and membership info.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    """
    user_id = conn.getUser().getId()
    print("Groups:")
    for g in conn.listGroups():
        if g.getId() not in [0, 1, 2]:
            owners, members = g.groupSummary()
            owner_ids = [e.getId() for e in owners]
            member_ids = [e.getId() for e in members]
            if user_id in owner_ids:
                group_status = 'owner'
            elif user_id in member_ids:
                group_status = 'member'
            else:
                group_status = ''
            print(f'{g.getName():>25}: {g.getId()}\t{group_status}')


def print_projects(conn):
    """Print all available Projects.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    """
    print("Projects:")
    for p in conn.listProjects():
        print(f'\t{p.getName()}:\t{p.getId()}')


def print_datasets(conn, project=None):
    """Print all available Datasets for a given Project.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    project : int or `None`, optional
        ID of Project for which to list datasets. If project is `None`,
        orphans are listed.
    """
    if project is not None:
        p = conn.getObject("Project", project)
        datasets = p.listChildren()
        print(f'Datasets in Project \"{p.getName()}\":')
    else:
        datasets = conn.listOrphans("Dataset")
        print('Orphaned Datsets:')

    for d in datasets:
        print(f"\t{d.getName()}:\t{d.getId()}")
