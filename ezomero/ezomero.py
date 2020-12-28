import logging
import numpy as np
from omero.gateway import MapAnnotationWrapper, DatasetWrapper, ProjectWrapper
from omero.model import MapAnnotationI, DatasetI, ProjectI, ProjectDatasetLinkI
from omero.model import DatasetImageLinkI, ImageI, ExperimenterI
from omero.rtypes import rlong, rstring
from omero.sys import Parameters


# posts
def post_dataset(conn, dataset_name, project_id=None, description=None):
    """Create a new dataset.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    dataset_name : str
        Name of the Dataset being created.
    project_id : int, optional
        Id of Project in which to create the Dataset. If no Project is
        specified, the Dataset will be orphaned.
    description : str
        Description for the new Dataset.

    Returns
    -------
    dataset_id : int
        Id of the dataset that has been created.

    Examples
    --------
    Create a new orphaned Dataset:
    >>> did = post_dataset(conn, "New Dataset")
    >>> did
    234

    Create a new Dataset in Project:120:
    >>> did = post_dataset(conn, "Child of 120", project_id=120)
    >>> did
    """
    if type(dataset_name) is not str:
        raise TypeError('Dataset name must be a string')

    if type(description) is not str and description is not None:
        raise TypeError('Dataset description must be a string')

    dataset = DatasetWrapper(conn, DatasetI())
    dataset.setName(dataset_name)
    if description is not None:
        dataset.setDescription(description)
    dataset.save()

    if project_id is not None:
        if type(project_id) is not int:
            raise TypeError('Project ID must be integer')
        link_datasets_to_project(conn, [dataset.getId()], project_id)

    return dataset.getId()


def post_image(conn, image, image_name, description=None, dataset_id=None,
               source_image_id=None, channel_list=None):
    """Create a new OMERO image from numpy array.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    image : ``numpy.ndarray``
        The numpy array from which a new OMERO image will be created. Note that
        array.ndim must equal 5. The function assumes this ``ndarray`` uses
        XYZCT ordering.
    image_name : str
        New of the new image to be created.
    description : str, optional
        Description for the new image.
    dataset_id : str, optional
        Id of the Dataset in which to create the image. If no Dataset is
        specified, an orphaned image will be created.
    source_image_id : int, optional
        If specified, copy this image with metadata, then add pixel data from
        ``image`` parameter.
    channel_list : list of ints
        Copies metadata from these channels in source image (if specified).

    Returns
    -------
    image_id : int
        Id of the new image that has been created.

    Examples
    --------
    >>> test_image = np.zeros((200, 200, 20, 3, 1), dtype=np.uint8)
    >>> im_id = post_image(conn, test_image, "test", dataset_id=105)
    >>> print(im_id)
    234
    """

    logging.warning('Using this function to save images to OMERO is not '
                    'recommended when `transfer=ln_s` is the primary mechanism'
                    ' for data import on your OMERO instance. Please consult '
                    'with your OMERO administrator.')
    if not isinstance(image, np.ndarray):
        raise TypeError("Input image must be `numpy.ndarray`")

    if image.ndim != 5:
        raise ValueError("Input image must have five dimensions: XYZCT")

    if type(image_name) is not str:
        raise TypeError("Image name must be a string")

    if dataset_id is not None:
        if type(dataset_id) is not int:
            raise ValueError("Dataset ID must be an integer")
        dataset = conn.getObject("Dataset", dataset_id)
    else:
        dataset = None

    image_sizez = image.shape[2]
    image_sizec = image.shape[3]
    image_sizet = image.shape[4]

    def plane_gen(image, image_sizez, image_sizec, image_sizet):
        for z in range(image_sizez):
            for c in range(image_sizec):
                for t in range(image_sizet):
                    yield image[:, :, z, c, t].T

    new_im = conn.createImageFromNumpySeq(plane_gen(image,
                                                    image_sizez,
                                                    image_sizec,
                                                    image_sizet),
                                          image_name,
                                          image_sizez,
                                          image_sizec,
                                          image_sizet,
                                          description,
                                          dataset,
                                          source_image_id,
                                          channel_list)
    return new_im.getId()


def post_map_annotation(conn, object_type, object_ids, kv_dict, ns):
    """Create new MapAnnotation and link to images.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    object_type : str
       OMERO object type, passed to ``BlitzGateway.getObjects``
    object_ids : int or list of ints
        IDs of objects to which the new MapAnnotation will be linked.
    kv_dict : dict
        key-value pairs that will be included in the MapAnnotation
    ns : str
        Namespace for the MapAnnotation

    Returns
    -------
    map_ann_id : int
        IDs of newly created MapAnnotation

    Examples
    --------
    >>> ns = 'jax.org/jax/example/namespace'
    >>> d = {'species': 'human',
             'occupation': 'time traveler'
             'first name': 'Kyle',
             'surname': 'Reese'}
    >>> post_map_annotation(conn, "Image", [23,56,78], d, ns)
    234
    """
    if type(object_ids) not in [list, int]:
        raise TypeError('object_ids must be list or integer')
    if type(object_ids) is not list:
        object_ids = [object_ids]

    if len(object_ids) == 0:
        raise ValueError('object_ids must contain one or more items')

    if type(kv_dict) is not dict:
        raise TypeError('kv_dict must be of type `dict`')

    kv_pairs = []
    for k, v in kv_dict.items():
        k = str(k)
        v = str(v)
        kv_pairs.append([k, v])

    map_ann = MapAnnotationWrapper(conn)
    map_ann.setNs(str(ns))
    map_ann.setValue(kv_pairs)
    map_ann.save()
    for o in conn.getObjects(object_type, object_ids):
        o.linkAnnotation(map_ann)
    return map_ann.getId()


def post_project(conn, project_name, description=None):
    """Create a new project.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    project_name : str
        Name of the new object to be created.
    description : str, optional
        Description for the new Project.

    Returns
    -------
    project_id : int
        Id of the new Project.

    Notes
    -----
    Project will be created in the Group specified in the connection. Group can
    be changed using ``conn.SERVICE_OPTS.setOmeroGroup``.

    Examples
    --------
    >>> project_id = post_project(conn, "My New Project")
    >>> print(project_id)
    238
    """
    if type(project_name) is not str:
        raise TypeError('Project name must be a string')

    if type(description) is not str and description is not None:
        raise TypeError('Project description must be a string')

    project = ProjectWrapper(conn, ProjectI())
    project.setName(project_name)
    if description is not None:
        project.setDescription(description)
    project.save()
    return project.getId()


# gets
def get_image(conn, image_id, no_pixels=False, start_coords=None,
              axis_lengths=None, xyzct=False, pad=False):
    """Get omero image object along with pixels as a numpy array.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    image_id : int
        Id of the image to get.
    no_pixels : bool, optional
        If true, no pixel data is returned, only the OMERO image object.
        Default is `False`.
    start_coords : list or tuple of int, optional
        Starting coordinates for each axis for the pixel region to be returned
        if `no_pixels` is `False` (assumes XYZCT ordering). If `None`, the zero
        coordinate is used for each axis. Default is None.
    axis_lengths : list or tuple of int, optional
        Lengths for each axis for the pixel region to be returned if
        `no_pixels` is `False`. If `None`, the lengths will be set such that
        the entire possible range of pixels is returned. Default is None.
    xyzct : bool, optional
        Option to return array with dimensional ordering XYZCT. If `False`, the
        ``skimage`` preferred ordering will be used (TZYXC). Default is False.
    pad : bool, optional
        If `axis_lengths` values would result in out-of-bounds indices, pad
        pixel array with zeros. Otherwise, such an operation will raise an
        exception. Ignored if `no_pixels` is True.

    Returns
    -------
    image : ``omero.gateway.ImageWrapper`` object
        OMERO image object.
    pixels : ndarray
        Array containing pixel values from OMERO image. Can be a subregion
        of the image if `start_coords` and `axis_lengths` are specified.

    Notes
    -----
    Regardless of whether `xyzct` is `True`, the numpy array is created as
    TZYXC, for performance reasons. If `xyzct` is `True`, the returned `pixels`
    array is actually a view of the original TZYXC array.

    Examples
    --------
    Get an entire image as a numpy array:
    >>> im_object, im_array = get_image(conn, 314)

    Get a subregion of an image as a numpy array:
    >>> im_o, im_a = get_image(conn, 314, start_coords=(40, 50, 4, 0, 0),
                               axis_lengths=(256, 256, 12, 10, 10))

    Get only the OMERO image object, no pixels:
    >>> im_object, _ = get_image(conn, 314, no_pixels=True)
    >>> im_object.getId()
    314
    """
    pixel_view = None
    image = conn.getObject('Image', image_id)
    size_x = image.getSizeX()
    size_y = image.getSizeY()
    size_z = image.getSizeZ()
    size_c = image.getSizeC()
    size_t = image.getSizeT()
    pixels_dtype = image.getPixelsType()
    orig_sizes = [size_x, size_y, size_z, size_c, size_t]

    if start_coords is None:
        start_coords = (0, 0, 0, 0, 0)

    if axis_lengths is None:
        axis_lengths = (orig_sizes[0] - start_coords[0],  # X
                        orig_sizes[1] - start_coords[1],  # Y
                        orig_sizes[2] - start_coords[2],  # Z
                        orig_sizes[3] - start_coords[3],  # C
                        orig_sizes[4] - start_coords[4])  # T

    if type(start_coords) not in (list, tuple):
        raise TypeError('start_coords must be supplied as list or tuple')
    if type(axis_lengths) not in (list, tuple):
        raise TypeError('axis_lengths must be supplied as list of tuple')
    if len(start_coords) != 5:
        raise ValueError('start_coords must have length 5 (XYZCT)')
    if len(axis_lengths) != 5:
        raise ValueError('axis_lengths must have length 5 (XYZCT)')

    if no_pixels is False:
        primary_pixels = image.getPrimaryPixels()
        reordered_sizes = [axis_lengths[4],
                           axis_lengths[2],
                           axis_lengths[1],
                           axis_lengths[0],
                           axis_lengths[3]]
        pixels = np.zeros(reordered_sizes, dtype=pixels_dtype)

        # check here if you need to trim the axis_lengths, trim if necessary
        overhangs = [(l + sc) - osz
                     for l, sc, osz
                     in zip(axis_lengths,
                            start_coords,
                            orig_sizes)]
        overhangs = [np.max((0, o)) for o in overhangs]
        if any([x > 0 for x in overhangs]) & (pad is False):
            raise IndexError('Attempting to access out-of-bounds pixel. '
                             'Either adjust axis_lengths or use pad=True')

        axis_lengths = [l - o for l, o in zip(axis_lengths, overhangs)]

        # get pixels
        zct_list = []
        for z in range(start_coords[2],
                       start_coords[2] + axis_lengths[2]):
            for c in range(start_coords[3],
                           start_coords[3] + axis_lengths[3]):
                for t in range(start_coords[4],
                               start_coords[4] + axis_lengths[4]):
                    zct_list.append((z, c, t))

        if reordered_sizes == [size_t, size_z, size_y, size_x, size_c]:
            plane_gen = primary_pixels.getPlanes(zct_list)
        else:
            tile = (start_coords[0], start_coords[1],
                    axis_lengths[0], axis_lengths[1])
            zct_list = [list(zct) for zct in zct_list]
            for zct in zct_list:
                zct.append(tile)
            plane_gen = primary_pixels.getTiles(zct_list)

        for i, plane in enumerate(plane_gen):
            zct_coords = zct_list[i]
            z = zct_coords[0] - start_coords[2]
            c = zct_coords[1] - start_coords[3]
            t = zct_coords[2] - start_coords[4]
            pixels[t, z, :axis_lengths[1], :axis_lengths[0], c] = plane

        if xyzct is True:
            pixel_view = np.moveaxis(pixels, [0, 1, 2, 3, 4], [4, 2, 1, 0, 3])
        else:
            pixel_view = pixels
    return (image, pixel_view)


def get_image_ids(conn, dataset=None, well=None):
    """return a list of image ids based on project and dataset

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    dataset : int, optional
        ID of Dataset from which to return image IDs.
    well : int, optional
        ID of Well from which to return image IDs.

    Returns
    -------
    im_ids : list of ints
        List of image IDs contained in the given Dataset, Well, or orphans.

    Notes
    -----
    User and group information comes from the `conn` object. Be sure to use
    ``ezomero.set_group`` to specify group prior to passing
    the `conn` object to this function.

    If no Dataset or Well is specified, orphaned images are returned.

    Examples
    --------
    Return orphaned images:
    >>> orphans = get_image_ids(conn)

    Return IDs of all images from Dataset with ID 448:
    >>> ds_ims = get_image_ids(conn, dataset=448)
    """
    if (dataset is not None) & (well is not None):
        raise Exception('Dataset and Well can not both be specified')

    q = conn.getQueryService()
    params = Parameters()

    if dataset is not None:
        if not isinstance(dataset, int):
            raise TypeError('dataset must be integer')
        params.map = {"dataset": rlong(dataset)}
        results = q.projection(
            "SELECT i.id FROM Dataset d"
            " JOIN d.imageLinks dil"
            " JOIN dil.child i"
            " WHERE d.id=:dataset",
            params,
            conn.SERVICE_OPTS
            )
    elif well is not None:
        if not isinstance(well, int):
            raise TypeError('well must be integer')
        params.map = {"well": rlong(well)}
        results = q.projection(
            "SELECT i.id FROM Well w"
            " JOIN w.wellSamples ws"
            " JOIN ws.image i"
            " WHERE w.id=:well",
            params,
            conn.SERVICE_OPTS
            )
    elif (well is None) & (dataset is None):
        results = q.projection(
            "SELECT i.id FROM Image i"
            " WHERE NOT EXISTS ("
            " SELECT dil FROM DatasetImageLink dil"
            " WHERE dil.child=i.id"
            " )"
            " AND NOT EXISTS ("
            " SELECT ws from WellSample ws"
            " WHERE ws.image=i.id"
            " )",
            params,
            conn.SERVICE_OPTS
            )
    else:
        results = []

    return [r[0].val for r in results]


def get_map_annotation_ids(conn, object_type, object_id, ns=None):
    """Get IDs of map annotations associated with an object

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    object_type : str
        OMERO object type, passed to ``BlitzGateway.getObject``
    object_id : int
        ID of object of ``object_type``.
    ns : str
        Namespace with which to filter results

    Returns
    -------
    map_ann_ids : list of ints

    Examples
    --------
    Return IDs of all map annotations belonging to an image:
    >>> map_ann_ids = get_map_annotation_ids(conn, 'Image', 42)

    Return IDs of map annotations with namespace "test" linked to a Dataset:
    >>> map_ann_ids = get_map_annotation_ids(conn, 'Datset', 16, ns='test')
    """

    target_object = conn.getObject(object_type, object_id)
    map_ann_ids = []
    for ann in target_object.listAnnotations(ns):
        if ann.OMERO_TYPE is MapAnnotationI:
            map_ann_ids.append(ann.getId())
    return map_ann_ids


def get_map_annotation(conn, map_ann_id):
    """Get the value of a map annotation object

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    map_ann_id : int
        ID of map annotation to get.

    Returns
    -------
    kv_dict : dict
        The value of the specified map annotation object, as a Python dict.

    Examples
    --------
    >>> ma_dict = get_map_annotation(conn, 62)
    >>> print(ma_dict)
    {'testkey': 'testvalue', 'testkey2': 'testvalue2'}
    """
    kv_pairs = conn.getObject('MapAnnotation', map_ann_id).getValue()
    kv_dict = {}
    for k, v in kv_pairs:
        kv_dict[k] = v
    return kv_dict


def get_group_id(conn, group_name):
    """Get ID of a group based on group name.

    Must be an exact match. Case sensitive.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    group_name : str
        Name of the group for which an ID is to be returned.

    Returns
    -------
    group_id : int
        ID of the OMERO group. Returns `None` if group cannot be found.

    Examples
    --------
    >>> get_group_id(conn, "Research IT")
    304
    """
    if type(group_name) is not str:
        raise TypeError('OMERO group name must be a string')

    for g in conn.listGroups():
        if g.getName() == group_name:
            return g.getId()
    return None


def get_user_id(conn, user_name):
    """Get ID of a user based on user name.

    Must be an exact match. Case sensitive.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    user_name : str
        Name of the user for which an ID is to be returned.

    Returns
    -------
    user_id : int
        ID of the OMERO user. Returns `None` if group cannot be found.

    Examples
    --------
    >>> get_user_id(conn, "jaxl")
    35
    """
    if type(user_name) is not str:
        raise TypeError('OMERO user name must be a string')

    for u in conn.containedExperimenters(1):
        if u.getName() == user_name:
            return u.getId()
    return None


def get_original_filepaths(conn, image_id, fpath='repo'):
    """Get paths to original files for specified image.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    image_id : int
        ID of image for which filepath info is to be returned.
    fpath : {'repo', 'client'}, optional
        Specify whether you want to return path to file in the managed
        repository ('repo') or the path from which the image was imported
        ('client'). The latter is useful for images that were imported by
        the "in place" method. Defaults to 'repo'.

    Notes
    -----
    The ManagedRepository ('repo') paths are relative, whereas the client paths
    are absolute.

    The client path may not be accessible if the image was not imported using
    "in place" imports (e.g., ``transfer=ln_s``).

    Returns
    -------
    original_filepaths : list of str

    Examples
    --------
    Return (relative) path of file in ManagedRepository:
    >>> get_original_filepaths(conn, 745)
    ['djme_2/2020-06/16/13-38-36.468/PJN17_083_07.ndpi']

    Return client path (location of file when it was imported):
    >>> get_original_filepaths(conn, 2201, fpath='client')
    ['/hyperfile/omero/Nishina_lab/Krebs_stack/PJN17_083_07.ndpi']
    """

    q = conn.getQueryService()
    params = Parameters()
    params.map = {"imid": rlong(image_id)}

    if fpath == 'client':
        results = q.projection(
            "SELECT fe.clientPath"
            " FROM Image i"
            " JOIN i.fileset f"
            " JOIN f.usedFiles fe"
            " WHERE i.id=:imid",
            params,
            conn.SERVICE_OPTS
            )
        results = ['/' + r[0].val for r in results]
    elif fpath == 'repo':
        results = q.projection(
            "SELECT o.path||o.name"
            " FROM Image i"
            " JOIN i.fileset f"
            " JOIN f.usedFiles fe"
            " JOIN fe.originalFile o"
            " WHERE i.id=:imid",
            params,
            conn.SERVICE_OPTS
            )
        results = [r[0].val for r in results]
    else:
        raise ValueError("Parameter fpath must be 'client' or 'repo'")

    return results


# puts
def put_map_annotation(conn, map_ann_id, kv_dict, ns=None):
    """Update an existing map annotation with new values (kv pairs)

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    map_ann_id : int
        ID of map annotation whose values (kv pairs) will be replaced.
    kv_dict : dict
        New values (kv pairs) for the MapAnnotation.
    ns : str
        New namespace for the MapAnnotation. If left as None, the old
        namespace will be used.

    Returns
    -------
    Returns None.

    Examples
    --------
    Change only the values of an existing map annotation:
    >>> new_values = {'testkey': 'testvalue', 'testkey2': 'testvalue2'}
    >>> put_map_annotation(conn, 15, new_values)

    Change both the values and namespace of an existing map annotation:
    >>> put_map_annotation(conn, 16, new_values, 'test_v2')
    """
    map_ann = conn.getObject('MapAnnotation', map_ann_id)

    if ns is None:
        ns = map_ann.getNs()
    map_ann.setNs(ns)

    kv_pairs = []
    for k, v in kv_dict.items():
        k = str(k)
        v = str(v)
        kv_pairs.append([k, v])
    map_ann.setValue(kv_pairs)
    map_ann.save()
    return None


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


def image_has_imported_filename(conn, im_id, imported_filename):
    """Ask whether an image is associated with a particular image file.

    THIS FUNCTION IS DEPRECATED AND WILL BE REMOVED

    Sometimes we know the filename of an image that has been imported into
    OMERO but not necessarily the image ID. This is frequently the case when
    we want to annotate a recently imported image. This funciton will help
    to filter a list of image IDs to only those associated with a particular
    filename in ImportedImageFiles.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    im_id : int
        ID of OMERO image.
    imported_filename : str
        The full filename (with extension) of the file whose OMERO image
        we are looking for. NOT the path of the image.

    Returns
    -------
    answer : boolean
        Answer to the question of whether the given image has an associated
        ImportedImageFile of the given name.

    Notes
    -----
    This function should be used as a filter on an image list that has been
    already narrowed down as much as possible. Note that many different images
    in OMERO may share the same filename (e.g., image.tif).

    Examples
    --------
    >>> im_ids = get_image_ids(conn, dataset=303)
    >>> im_ids = [im_id for im_id in im_ids
    ...           if image_has_imported_filename(conn, im_id, "feb_2020.tif")]
    """

    q = conn.getQueryService()
    params = Parameters()
    params.map = {"imid": rlong(im_id)}
    results = q.projection(
        "SELECT o.name FROM Image i"
        " JOIN i.fileset fs"
        " JOIN fs.usedFiles u"
        " JOIN u.originalFile o"
        " WHERE i.id=:imid",
        params,
        conn.SERVICE_OPTS
        )
    imp_filenames = [r[0].val for r in results]

    if imported_filename in imp_filenames:
        return True
    else:
        return False


# linking functions
def link_images_to_dataset(conn, image_ids, dataset_id):
    """
    TODO: WRITE THIS DOCSTRING
    """
    user_id = _get_current_user(conn)
    for im_id in image_ids:
        link = DatasetImageLinkI()
        link.setParent(DatasetI(dataset_id, False))
        link.setChild(ImageI(im_id, False))
        link.details.owner = ExperimenterI(user_id, False)
        conn.getUpdateService().saveObject(link, conn.SERVICE_OPTS)


def link_datasets_to_project(conn, dataset_ids, project_id):
    """
    TODO: WRITE THIS DOCSTRING
    """
    user_id = _get_current_user(conn)
    for did in dataset_ids:
        link = ProjectDatasetLinkI()
        link.setParent(ProjectI(project_id, False))
        link.setChild(DatasetI(did, False))
        link.details.owner = ExperimenterI(user_id, False)
        conn.getUpdateService().saveObject(link, conn.SERVICE_OPTS)


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
        print(f'Orphaned Datsets:')

    for d in datasets:
        print(f"\t{d.getName()}:\t{d.getId()}")


# functions for managing connection context and service options.

def set_group(conn, group_id):
    """Safely switch OMERO group.

    This function will change the user's current group to that specified by
    `group_id`, but only if the user is a member of that group. This is a
    "safer" way to do this than ``conn.SERVICE_OPTS.setOmeroGroup``, which will
    allow switching to a group that a user does not have permissions, which can
    lead to server-side errors.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    group_id : int
        The id of the group to switch to.

    Returns
    -------
    change_status : bool
        Returns `True` if group is changed, otherwise returns `False`.
    """
    user_id = conn.getUser().getId()
    g = conn.getObject("ExperimenterGroup", group_id)
    owners, members = g.groupSummary()
    owner_ids = [e.getId() for e in owners]
    member_ids = [e.getId() for e in members]
    if (user_id in owner_ids) or (user_id in member_ids):
        conn.SERVICE_OPTS.setOmeroGroup(group_id)
        return True
    else:
        logging.warning(f'User {user_id} is not a member of Group {group_id}')
        return False


# private functions
def _get_current_user(conn):
    userid = conn.SERVICE_OPTS.getOmeroUser()
    if userid is None:
        userid = conn.getUserId()
    return userid
