import logging
import os
import numpy as np
from ._ezomero import do_across_groups
from omero.gateway import FileAnnotationWrapper
from omero import ApiUsageException
from omero.model import MapAnnotationI, TagAnnotationI
from omero.rtypes import rint, rlong
from omero.sys import Parameters


# gets
@do_across_groups
def get_image(conn, image_id, no_pixels=False, start_coords=None,
              axis_lengths=None, xyzct=False, pad=False, across_groups=True):
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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

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
    # Get an entire image as a numpy array:

    >>> im_object, im_array = get_image(conn, 314)

    # Get a subregion of an image as a numpy array:

    >>> im_o, im_a = get_image(conn, 314, start_coords=(40, 50, 4, 0, 0),
    ...                        axis_lengths=(256, 256, 12, 10, 10))

    # Get only the OMERO image object, no pixels:

    >>> im_object, _ = get_image(conn, 314, no_pixels=True)
    >>> im_object.getId()
    314
    """

    if image_id is None:
        raise TypeError('Object ID cannot be empty')
    pixel_view = None
    image = conn.getObject('Image', image_id)
    if image is None:
        logging.warning(f'Cannot load image {image_id} - '
                        'check if you have permissions to do so')
        return (None, None)
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
        overhangs = [(al + sc) - osz
                     for al, sc, osz
                     in zip(axis_lengths,
                            start_coords,
                            orig_sizes)]
        overhangs = [np.max((0, o)) for o in overhangs]
        if any([x > 0 for x in overhangs]) & (pad is False):
            raise IndexError('Attempting to access out-of-bounds pixel. '
                             'Either adjust axis_lengths or use pad=True')

        axis_lengths = [al - oh for al, oh in zip(axis_lengths, overhangs)]

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


@do_across_groups
def get_image_ids(conn, project=None, dataset=None, plate=None, well=None,
                  across_groups=True):
    """Return a list of image ids based on image container

    If no container is specified, function will return orphans.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    project : int, optional
        ID of Project from which to return image IDs. This will return IDs of
        all images contained in all child Datasets of the specified Project.
    dataset : int, optional
        ID of Dataset from which to return image IDs.
    plate : int, optional
        ID of Plate from which to return image IDs. This will return IDs of
        all images contained in all Wells belonging to the specified Plate.
    well : int, optional
        ID of Well from which to return image IDs.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Returns
    -------
    im_ids : list of ints
        List of image IDs contained in the specified container.

    Notes
    -----
    User and group information comes from the `conn` object. Be sure to use
    ``ezomero.set_group`` to specify group prior to passing
    the `conn` object to this function.

    Only one of Project, Dataset, Plate, or Well can be specified. If none of
    those are specified, orphaned images are returned.

    Examples
    --------
    # Return orphaned images:

    >>> orphans = get_image_ids(conn)

    # Return IDs of all images from Dataset with ID 448:

    >>> ds_ims = get_image_ids(conn, dataset=448)
    """
    arg_counter = 0
    for arg in [project, dataset, plate, well]:
        if arg is not None:
            arg_counter += 1
    if arg_counter > 1:
        raise ValueError('Only one of Project/Dataset/Plate/Well'
                         ' can be specified')

    q = conn.getQueryService()
    params = Parameters()

    if project is not None:
        if not isinstance(project, int):
            raise TypeError('Project ID must be integer')
        params.map = {"project": rlong(project)}
        results = q.projection(
            "SELECT i.id FROM Project p"
            " JOIN p.datasetLinks pdl"
            " JOIN pdl.child d"
            " JOIN d.imageLinks dil"
            " JOIN dil.child i"
            " WHERE p.id=:project",
            params,
            conn.SERVICE_OPTS
            )
    elif dataset is not None:
        if not isinstance(dataset, int):
            raise TypeError('Dataset ID must be integer')
        params.map = {"dataset": rlong(dataset)}
        results = q.projection(
            "SELECT i.id FROM Dataset d"
            " JOIN d.imageLinks dil"
            " JOIN dil.child i"
            " WHERE d.id=:dataset",
            params,
            conn.SERVICE_OPTS
            )
    elif plate is not None:
        if not isinstance(plate, int):
            raise TypeError('Plate ID must be integer')
        params.map = {"plate": rlong(plate)}
        results = q.projection(
            "SELECT i.id FROM Plate pl"
            " JOIN pl.wells w"
            " JOIN w.wellSamples ws"
            " JOIN ws.image i"
            " WHERE pl.id=:plate",
            params,
            conn.SERVICE_OPTS
            )
    elif well is not None:
        if not isinstance(well, int):
            raise TypeError('Well ID must be integer')
        params.map = {"well": rlong(well)}
        results = q.projection(
            "SELECT i.id FROM Well w"
            " JOIN w.wellSamples ws"
            " JOIN ws.image i"
            " WHERE w.id=:well",
            params,
            conn.SERVICE_OPTS
            )
    elif ((well is None) &
          (dataset is None) &
          (project is None) &
          (plate is None)):
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


@do_across_groups
def get_map_annotation_ids(conn, object_type, object_id, ns=None,
                           across_groups=True):
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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Returns
    -------
    map_ann_ids : list of ints

    Examples
    --------
    # Return IDs of all map annotations belonging to an image:

    >>> map_ann_ids = get_map_annotation_ids(conn, 'Image', 42)

    # Return IDs of map annotations with namespace "test" linked to a Dataset:

    >>> map_ann_ids = get_map_annotation_ids(conn, 'Dataset', 16, ns='test')
    """

    target_object = conn.getObject(object_type, object_id)
    map_ann_ids = []
    for ann in target_object.listAnnotations(ns):
        if ann.OMERO_TYPE is MapAnnotationI:
            map_ann_ids.append(ann.getId())
    return map_ann_ids


@do_across_groups
def get_tag_ids(conn, object_type, object_id, ns=None,
                across_groups=True):
    """Get IDs of tag annotations associated with an object

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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Returns
    -------
    tag_ids : list of ints

    Examples
    --------
    # Return IDs of all tags linked to an image:

    >>> tag_ids = get_tag_ids(conn, 'Image', 42)

    # Return IDs of tags with namespace "test" linked to a Dataset:

    >>> tag_ids = get_tag_ids(conn, 'Dataset', 16, ns='test')
    """

    target_object = conn.getObject(object_type, object_id)
    tag_ids = []
    for ann in target_object.listAnnotations(ns):
        if ann.OMERO_TYPE is TagAnnotationI:
            tag_ids.append(ann.getId())
    return tag_ids


@do_across_groups
def get_file_annotation_ids(conn, object_type, object_id, ns=None,
                            across_groups=True):
    """Get IDs of file annotations associated with an object

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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Returns
    -------
    file_ann_ids : list of ints

    Examples
    --------
    # Return IDs of all file annotations linked to an image:

    >>> file_ann_ids = get_file_annotation_ids(conn, 'Image', 42)

    # Return IDs of file annotations with namespace "test" linked to a Dataset:

    >>> file_ann_ids = get_file_annotation_ids(conn, 'Dataset', 16, ns='test')
    """

    target_object = conn.getObject(object_type, object_id)
    file_ann_ids = []
    for ann in target_object.listAnnotations(ns):
        if isinstance(ann, FileAnnotationWrapper):
            file_ann_ids.append(ann.getId())
    return file_ann_ids


@do_across_groups
def get_well_id(conn, plate_id, row, column, across_groups=True):
    """Get ID of well based on plate ID, row, and column

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    plate_id : int
        ID of plate for which the well ID is needed
    row : int
        Row of well (zero-based indexing)
    column : int
        Column of well (zero-based indexing)

    Returns
    -------
    well_id : int
        ID of well being queried.
    """
    if not isinstance(plate_id, int):
        raise ValueError('Plate ID must be an integer')
    if not isinstance(row, int):
        raise ValueError('Row index must be an integer')
    if not isinstance(column, int):
        raise ValueError('Column index must be an integer')
    q = conn.getQueryService()
    params = Parameters()
    params.map = {"plate": rlong(plate_id),
                  "row": rint(row),
                  "column": rint(column)}
    results = q.projection(
        "SELECT w.id FROM Plate pl"
        " JOIN pl.wells w"
        " WHERE pl.id=:plate"
        " AND w.row=:row"
        " AND w.column=:column",
        params,
        conn.SERVICE_OPTS
        )
    if len(results) == 0:
        return None
    return [r[0].val for r in results][0]


@do_across_groups
def get_map_annotation(conn, map_ann_id, across_groups=True):
    """Get the value of a map annotation object

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    map_ann_id : int
        ID of map annotation to get.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

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
    return dict(conn.getObject('MapAnnotation', map_ann_id).getValue())


@do_across_groups
def get_tag(conn, tag_id, across_groups=True):
    """Get the value of a tag annotation object

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    tag_id : int
        ID of tag annotation to get.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Returns
    -------
    tag : str
        The value of the specified tag annotation object.

    Examples
    --------
    >>> tag = get_tag(conn, 62)
    >>> print(tag)
    This_is_a_tag
    """
    return conn.getObject('TagAnnotation', tag_id).getValue()


@do_across_groups
def get_file_annotation(conn, file_ann_id, folder_path=None,
                        across_groups=True):
    """Get the value of a file annotation object

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    file_ann_id : int
        ID of map annotation to get.
    folder_path : str
        Path where file annotation will be saved. Defaults to local script
        directory.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Returns
    -------
    file_path : str
        The path to the created file.

    Examples
    --------
    >>> attch_path = get_file_annotation(conn,
    ...                                  62,
    ...                                  folder_path='/home/user/Downloads')
    >>> print(attch_path)
    '/home/user/Downloads/attachment.txt'
    """

    if not folder_path or not os.path.exists(folder_path):
        folder_path = os.path.dirname(__file__)
    ann = conn.getObject('FileAnnotation', file_ann_id)
    file_path = os.path.join(folder_path, ann.getFile().getName())
    with open(str(file_path), 'wb') as f:
        for chunk in ann.getFileInChunks():
            f.write(chunk)
    return file_path


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

    try:
        g = conn.c.sf.getAdminService().lookupGroup(group_name)
        return g.id.val
    except ApiUsageException:
        pass
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


@do_across_groups
def get_original_filepaths(conn, image_id, fpath='repo', across_groups=True):
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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

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
    # Return (relative) path of file in ManagedRepository:

    >>> get_original_filepaths(conn, 745)
    ['djme_2/2020-06/16/13-38-36.468/PJN17_083_07.ndpi']

    # Return client path (location of file when it was imported):

    >>> get_original_filepaths(conn, 2201, fpath='client')
    ['/client/omero/smith_lab/stack2/PJN17_083_07.ndpi']
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
