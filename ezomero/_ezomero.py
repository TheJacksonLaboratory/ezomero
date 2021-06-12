import configparser
import logging
import os
import functools
import inspect
import mimetypes
import numpy as np
from getpass import getpass
from omero.gateway import BlitzGateway
from omero.gateway import MapAnnotationWrapper, FileAnnotationWrapper
from omero.gateway import ProjectWrapper, DatasetWrapper
from omero.model import MapAnnotationI, DatasetI, ProjectI, ProjectDatasetLinkI
from omero.model import DatasetImageLinkI, ImageI, ExperimenterI
from omero.model import RoiI, PointI, LineI, RectangleI, EllipseI
from omero.model import PolygonI, LengthI, enums
from omero.rtypes import rlong, rstring, rint, rdouble
from omero.sys import Parameters
from ezomero.rois import Point, Line, Rectangle, Ellipse, Polygon
from pathlib import Path


def get_default_args(func):
    """Retrieves the default arguments of a function.

    Parameters
    ----------
    func : function
        Function whose signature we want to inspect

    Returns
    -------
    _ : dict
        Key-value pairs of argument name and value.
    """
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


def do_across_groups(f):
    """Decorator functional for making functions work across
    OMERO groups.

    Parameters
    ----------
    f : function
        Function that will be decorated

    Returns
    -------
    wrapper : Object
        Return value of the decorated function.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        defaults = get_default_args(f)
        do_across_groups = False
        # test if user is overriding default
        if 'across_groups' in kwargs:
            # if they are, respect user settings
            if kwargs['across_groups']:
                do_across_groups = True
        else:
            # else, respect default
            if defaults['across_groups']:
                do_across_groups = True
        if do_across_groups:
            current_group = args[0].getGroupFromContext().getId()
            args[0].SERVICE_OPTS.setOmeroGroup('-1')
            res = f(*args, **kwargs)
            set_group(args[0], current_group)
        else:
            res = f(*args, **kwargs)
        return res
    return wrapper


# posts

@do_across_groups
def post_dataset(conn, dataset_name, project_id=None, description=None,
                 across_groups=True):
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
    description : str, optional
        Description for the new Dataset.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.


    Returns
    -------
    dataset_id : int
        Id of the dataset that has been created.

    Examples
    --------
    # Create a new orphaned Dataset:

    >>> did = post_dataset(conn, "New Dataset")
    >>> did
    234

    # Create a new Dataset in Project:120:

    >>> did = post_dataset(conn, "Child of 120", project_id=120)
    >>> did
    """
    if type(dataset_name) is not str:
        raise TypeError('Dataset name must be a string')

    if type(description) is not str and description is not None:
        raise TypeError('Dataset description must be a string')

    project = None
    if project_id is not None:
        if type(project_id) is not int:
            raise TypeError('Project ID must be integer')
        project = conn.getObject('Project', project_id)
        if project is not None:
            ret = set_group(conn, project.getDetails().group.id.val)
            if ret is False:
                return None
        else:
            logging.warning(f'Project {project_id} could not be found '
                            '(check if you have permissions to it)')
            return None
    else:
        default_group = conn.getDefaultGroup(conn.getUser().getId()).getId()
        set_group(conn, default_group)

    dataset = DatasetWrapper(conn, DatasetI())
    dataset.setName(dataset_name)
    if description is not None:
        dataset.setDescription(description)
    dataset.save()

    if project is not None:
        link_datasets_to_project(conn, [dataset.getId()], project_id)
    return dataset.getId()


@do_across_groups
def post_image(conn, image, image_name, description=None, dataset_id=None,
               source_image_id=None, channel_list=None, across_groups=True):
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
        Name of the new image to be created.
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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

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
        if dataset is not None:
            ret = set_group(conn, dataset.getDetails().group.id.val)
            if ret is False:
                return None
        else:
            logging.warning(f'Dataset {dataset_id} could not be found '
                            '(check if you have permissions to it)')
            return None
    else:
        default_group = conn.getDefaultGroup(conn.getUser().getId()).getId()
        set_group(conn, default_group)
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


@do_across_groups
def post_map_annotation(conn, object_type, object_id, kv_dict, ns,
                        across_groups=True):
    """Create new MapAnnotation and link to images.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    object_type : str
       OMERO object type, passed to ``BlitzGateway.getObjects``
    object_ids : int
        ID of object to which the new MapAnnotation will be linked.
    kv_dict : dict
        key-value pairs that will be included in the MapAnnotation
    ns : str
        Namespace for the MapAnnotation
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Notes
    -----
    All keys and values are converted to strings before saving in OMERO.

    Returns
    -------
    map_ann_id : int
        IDs of newly created MapAnnotation

    Examples
    --------
    >>> ns = 'jax.org/jax/example/namespace'
    >>> d = {'species': 'human',
    ...      'occupation': 'time traveler'
    ...      'first name': 'Kyle',
    ...      'surname': 'Reese'}
    >>> post_map_annotation(conn, "Image", 56, d, ns)
    234
    """

    if type(kv_dict) is not dict:
        raise TypeError('kv_dict must be of type `dict`')

    kv_pairs = []
    for k, v in kv_dict.items():
        k = str(k)
        v = str(v)
        kv_pairs.append([k, v])

    obj = None
    if object_id is not None:
        if type(object_id) is not int:
            raise TypeError('object_ids must be integer')
        obj = conn.getObject(object_type, object_id)
        if obj is not None:
            ret = set_group(conn, obj.getDetails().group.id.val)
            if ret is False:
                logging.warning('Cannot change into group '
                                f'where object {object_id} is.')
                return None
        else:
            logging.warning(f'Object {object_id} could not be found '
                            '(check if you have permissions to it)')
            return None
    else:
        raise TypeError('Object ID cannot be empty')

    map_ann = MapAnnotationWrapper(conn)
    map_ann.setNs(str(ns))
    map_ann.setValue(kv_pairs)
    map_ann.save()
    try:
        obj.linkAnnotation(map_ann)
    except:  # fix this bare exception
        logging.warning(f'Cannot link to object {object_id} - '
                        'check if you have permissions to do so')
        return None

    return map_ann.getId()


@do_across_groups
def post_file_annotation(conn, object_type, object_id, file_path, ns,
                         mimetype=None, description=None, across_groups=True):
    """Create new FileAnnotation and link to images.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    object_type : str
       OMERO object type, passed to ``BlitzGateway.getObjects``
    object_ids : int
        ID of object to which the new MapAnnotation will be linked.
    file_path : string
        local path to file to be added as FileAnnotation
    ns : str
        Namespace for the FileAnnotation
    mimetype : str
        String of the form 'type/subtype', usable for a MIME content-type
        header.
    description : str
        File description to be added to FileAnnotation
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Notes
    -----
    All keys and values are converted to strings before saving in OMERO.

    Returns
    -------
    file_ann_id : int
        IDs of newly created MapAnnotation

    Examples
    --------
    >>> ns = 'jax.org/jax/example/namespace'
    >>> path = '/home/user/Downloads/file_ann.txt'
    >>> post_file_annotation(conn, "Image", 56, path, ns)
    234
    """

    if type(file_path) is not str:
        raise TypeError('file_path must be of type `str`')

    obj = None
    if object_id is not None:
        if type(object_id) is not int:
            raise TypeError('object_ids must be integer')
        obj = conn.getObject(object_type, object_id)
        if obj is not None:
            ret = set_group(conn, obj.getDetails().group.id.val)
            if ret is False:
                logging.warning('Cannot change into group '
                                f'where object {object_id} is.')
                return None
        else:
            logging.warning(f'Object {object_id} could not be found '
                            '(check if you have permissions to it)')
            return None
    else:
        raise TypeError('Object ID cannot be empty')
    if not mimetype:
        mimetype = mimetypes.guess_type(file_path)
    file_ann = conn.createFileAnnfromLocalFile(
        file_path, mimetype=mimetype, ns=ns, desc=description)
    obj.linkAnnotation(file_ann)

    return file_ann.getId()


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


def post_roi(conn, image_id, shapes, name=None, description=None,
             fill_color=(10, 10, 10, 10), stroke_color=(255, 255, 255, 255),
             stroke_width=1):
    """Create new ROI from a list of shapes and link to an image.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    image_id : int
        IDs of the image to which the new ROI will be linked.
    shapes : list of shapes
        List of shape objects associated with the new ROI.
    name : str, optional
        Name for the new ROI.
    description : str, optional
        Description of the new ROI.
    fill_color: tuple of int, optional
        The color fill of the shape. Color is specified as a a tuple containing
        4 integers from 0 to 255, representing red, green, blue and alpha
        levels. Default is (10, 10, 10, 10).
    stroke_color: tuple of int, optional
        The color of the shape edge. Color is specified as a a tuple containing
        4 integers from 0 to 255, representing red, green, blue and alpha
        levels. Default is (255, 255, 255, 255).
    stroke_width: int, optional
        The width of the shape stroke in pixels. Default is 1.


    Returns
    -------
    ROI_id : int
        ID of newly created ROI

    Examples
    --------
    >>> shapes = list()
    >>> point = Point(x=30.6, y=80.4)
    >>> shapes.append(point)
    >>> rectangle = Rectangle(x=50.0,
                              y=51.3,
                              width=90,
                              height=40,
                              z=3,
                              label='The place')
    >>> shapes.append(rectangle)
    >>> post_roi(conn, 23, shapes, name='My Cell',
                 description='Very important',
                 fill_color=(255, 10, 10, 150),
                 stroke_color=(255, 0, 0, 0),
                 stroke_width=2)
    234
    """
    roi = RoiI()
    if name is not None:
        roi.setName(rstring(name))
    if description is not None:
        roi.setDescription(rstring(description))
    for shape in shapes:
        roi.addShape(_shape_to_omero_shape(shape, fill_color, stroke_color,
                                           stroke_width))
    image = conn.getObject('Image', image_id)
    roi.setImage(image._obj)
    roi = conn.getUpdateService().saveAndReturnObject(roi)
    return roi.getId().getValue()


def _shape_to_omero_shape(shape, fill_color, stroke_color, stroke_width):
    """ Helper function to convert ezomero shapes into omero shapes"""
    if isinstance(shape, Point):
        omero_shape = PointI()
        omero_shape.x = rdouble(shape.x)
        omero_shape.y = rdouble(shape.y)
    elif isinstance(shape, Line):
        omero_shape = LineI()
        omero_shape.x1 = rdouble(shape.x1)
        omero_shape.x2 = rdouble(shape.x2)
        omero_shape.y1 = rdouble(shape.y1)
        omero_shape.y2 = rdouble(shape.y2)
    elif isinstance(shape, Rectangle):
        omero_shape = RectangleI()
        omero_shape.x = rdouble(shape.x)
        omero_shape.y = rdouble(shape.y)
        omero_shape.width = rdouble(shape.width)
        omero_shape.height = rdouble(shape.height)
    elif isinstance(shape, Ellipse):
        omero_shape = EllipseI()
        omero_shape.x = rdouble(shape.x)
        omero_shape.y = rdouble(shape.y)
        omero_shape.radiusX = rdouble(shape.x_rad)
        omero_shape.radiusY = rdouble(shape.y_rad)
    elif isinstance(shape, Polygon):
        omero_shape = PolygonI()
        points_str = "".join("".join([str(x), ',', str(y), ', ']) for x, y in shape.points)[:-2]
        omero_shape.points = rstring(points_str)
    else:
        err = 'The shape passed for the roi is not a valid shape type'
        raise TypeError(err)

    if shape.z is not None:
        omero_shape.theZ = rint(shape.z)
    if shape.c is not None:
        omero_shape.theC = rint(shape.c)
    if shape.t is not None:
        omero_shape.theT = rint(shape.t)
    if shape.label is not None:
        omero_shape.setTextValue(rstring(shape.label))
    omero_shape.setFillColor(rint(_rgba_to_int(fill_color)))
    omero_shape.setStrokeColor(rint(_rgba_to_int(stroke_color)))
    omero_shape.setStrokeWidth(LengthI(stroke_width, enums.UnitsLength.PIXEL))

    return omero_shape


def _rgba_to_int(color: tuple):
    """ Helper function returning the color as an Integer in RGBA encoding """
    try:
        r, g, b, a = color
    except ValueError as e:
        raise e('The format for the shape color is not addequate')
    r = r << 24
    g = g << 16
    b = b << 8
    a = int(a * 255)
    rgba_int = sum([r, g, b, a])
    if rgba_int > (2**31-1):  # convert to signed 32-bit int
        rgba_int = rgba_int - 2**32

    return rgba_int


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
def get_image_ids(conn, dataset=None, well=None, across_groups=True):
    """Return a list of image ids based on image container

    If neither dataset nor well is specified, function will return orphans.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    dataset : int, optional
        ID of Dataset from which to return image IDs.
    well : int, optional
        ID of Well from which to return image IDs.
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

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
    # Return orphaned images:

    >>> orphans = get_image_ids(conn)

    # Return IDs of all images from Dataset with ID 448:

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
def get_file_annotation_ids(conn, object_type, object_id, ns=None,
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
    file_ann_ids : list of ints

    Examples
    --------
    # Return IDs of all file annotations belonging to an image:

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
def get_file_annotation(conn, file_ann_id, folder_path=None,
                        across_groups=True):
    """Get the value of a map annotation object

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


    Examples
    --------
    >>> get_file_annotation(conn, folder_path='/home/user/Downloads',62)
    """

    if not folder_path or not os.path.exists(folder_path):
        path = os.path.dirname(__file__)
    ann = conn.getObject('FileAnnotation', file_ann_id)
    file_path = os.path.join(path, ann.getFile().getName())
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


# puts
@do_across_groups
def put_map_annotation(conn, map_ann_id, kv_dict, ns=None, across_groups=True):
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
    across_groups : bool, optional
        Defines cross-group behavior of function - set to
        ``False`` to disable it.

    Notes
    -----
    All keys and values are converted to strings before saving in OMERO.

    Returns
    -------
    Returns None.

    Examples
    --------
    # Change only the values of an existing map annotation:

    >>> new_values = {'testkey': 'testvalue', 'testkey2': 'testvalue2'}
    >>> put_map_annotation(conn, 15, new_values)

    # Change both the values and namespace of an existing map annotation:

    >>> put_map_annotation(conn, 16, new_values, 'test_v2')
    """
    map_ann = conn.getObject('MapAnnotation', map_ann_id)
    if map_ann is None:
        raise ValueError("MapAnnotation is non-existent or you do not have "
                         "permissions to change it.")
        return None

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


# functions for managing connection context and service options.

def connect(user=None, password=None, group=None, host=None, port=None,
            secure=None, config_path=None):
    """Create an OMERO connection

    This function will create an OMERO connection by populating certain
    parameters for ``omero.gateway.BlitzGateway`` initialization by the
    procedure described in the notes below. Note that this function may
    ask for user input, so be cautious if using in the context of a script.

    Finally, don't forget to close the connection ``conn.close()`` when it
    is no longer needed!

    Parameters
    ----------
    user : str, optional
        OMERO username.

    password : str, optional
        OMERO password.

    group : str, optional
        OMERO group.

    host : str, optional
        OMERO.server host.

    port : int, optional
        OMERO port.

    secure : boolean, optional
        Whether to create a secure session.

    config_path : str, optional
        Path to directory containing '.ezomero' file that stores connection
        information. If left as ``None``, defaults to the home directory as
        determined by Python's ``pathlib``.

    Returns
    -------
    conn : ``omero.gateway.BlitzGateway`` object or None
        OMERO connection, if successful. Otherwise an error is logged and
        returns None.

    Notes
    -----
    The procedure for choosing parameters for ``omero.gateway.BlitzGateway``
    initialization is as follows:

    1) Any parameters given to `ezconnect` will be used to initialize
       ``omero.gateway.BlitzGateway``

    2) If a parameter is not given to `ezconnect`, populate from variables
       in ``os.environ``:
        * OMERO_USER
        * OMERO_PASS
        * OMERO_GROUP
        * OMERO_HOST
        * OMERO_PORT
        * OMERO_SECURE

    3) If environment variables are not set, try to load from a config file.
       This file should be called '.ezomero'. By default, this function will
       look in the home directory, but ``config_path`` can be used to specify
       a directory in which to look for '.ezomero'.

       The function ``ezomero.store_connection_params`` can be used to create
       the '.ezomero' file.

       Note that passwords can not be loaded from the '.ezomero' file. This is
       to discourage storing credentials in a file as cleartext.

    4) If any remaining parameters have not been set by the above steps, the
       user is prompted to enter a value for each unset parameter.
    """
    # load from .ezomero config file if it exists
    if config_path is None:
        config_fp = Path.home() / '.ezomero'
    elif type(config_path) is str:
        config_fp = Path(config_path) / '.ezomero'
    else:
        raise TypeError('config_path must be a string')

    config_dict = {}
    if config_fp.exists():
        config = configparser.ConfigParser()
        with config_fp.open() as fp:
            config.read_file(fp)
        config_dict = config["DEFAULT"]

    # set user
    if user is None:
        user = config_dict.get("OMERO_USER", user)
        user = os.environ.get("OMERO_USER", user)
    if user is None:
        user = input('Enter username: ')

    # set password
    if password is None:
        password = os.environ.get("OMERO_PASS", password)
    if password is None:
        password = getpass('Enter password: ')

    # set group
    if group is None:
        group = config_dict.get("OMERO_GROUP", group)
        group = os.environ.get("OMERO_GROUP", group)
    if group is None:
        group = input('Enter group name (or leave blank for default group): ')
    if group == "":
        group = None

    # set host
    if host is None:
        host = config_dict.get("OMERO_HOST", host)
        host = os.environ.get("OMERO_HOST", host)
    if host is None:
        host = input('Enter host: ')

    # set port
    if port is None:
        port = config_dict.get("OMERO_PORT", port)
        port = os.environ.get("OMERO_PORT", port)
    if port is None:
        port = input('Enter port: ')
    port = int(port)

    # set session security
    if secure is None:
        secure = config_dict.get("OMERO_SECURE", secure)
        secure = os.environ.get("OMERO_SECURE", secure)
    if secure is None:
        secure = input('Secure session (True or False): ')
    if type(secure) is str:
        if secure.lower() in ["true", "t"]:
            secure = True
        elif secure.lower() in ["false", "f"]:
            secure = False
        else:
            raise ValueError('secure must be set to either True or False')

    # create connection
    conn = BlitzGateway(user, password, group=group, host=host, port=port,
                        secure=secure)
    if conn.connect():
        return conn
    else:
        logging.error('Could not connect, check your settings')
        return None


def store_connection_params(user=None, group=None, host=None, port=None,
                            secure=None, config_path=None):
    """Save OMERO connection parameters in a file.

    This function creates a config file ('.ezomero') in which
    certain OMERO parameters are stored, to make it easier to create
    ``omero.gateway.BlitzGateway`` objects.

    Parameters
    ----------
    user : str, optional
        OMERO username.

    group : str, optional
        OMERO group.

    host : str, optional
        OMERO.server host.

    port : int, optional
        OMERO port.

    secure : boolean, optional
        Whether to create a secure session.

    config_path : str, optional
        Path to directory that will contain the '.ezomero' file. If left as
        ``None``, defaults to the home directory as determined by Python's
        ``pathlib``.
    """
    if config_path is None:
        config_path = Path.home()
    elif type(config_path) is str:
        config_path = Path(config_path)
    else:
        raise ValueError('config_path must be a string')

    if not config_path.is_dir():
        raise ValueError('config_path must point to a valid directory')
    ezo_file = config_path / '.ezomero'
    if ezo_file.exists():
        resp = input(f'{ezo_file} already exists. Overwrite? (Y/N)')
        if resp.lower() not in ['yes', 'y']:
            return

    # get parameters
    if user is None:
        user = input('Enter username: ')
    if group is None:
        group = input('Enter group name (or leave blank for default group): ')
    if host is None:
        host = input('Enter host: ')
    if port is None:
        port = input('Enter port: ')
    if secure is None:
        secure_str = input('Secure session (True or False): ')
        if secure_str.lower() in ["true", "t"]:
            secure = "True"
        elif secure_str.lower() in ["false", "f"]:
            secure = "False"
        else:
            raise ValueError('secure must be set to either True or False')

    # make parameter dictionary and save as configfile
    # just use 'DEFAULT' for right now, we can possibly add alt configs later
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'OMERO_USER': user,
                         'OMERO_GROUP': group,
                         'OMERO_HOST': host,
                         'OMERO_PORT': port,
                         'OMERO_SECURE': secure}
    with ezo_file.open('w') as configfile:
        config.write(configfile)
        print(f'Connection settings saved to {ezo_file}')


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
