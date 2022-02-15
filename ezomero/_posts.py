import logging
import mimetypes
import numpy as np
from ._ezomero import do_across_groups, set_group
from ._misc import link_datasets_to_project
from omero.model import RoiI, PointI, LineI, RectangleI, EllipseI
from omero.model import PolygonI, PolylineI, LabelI, LengthI, enums
from omero.model import DatasetI, ProjectI, ScreenI
from omero.gateway import ProjectWrapper, DatasetWrapper
from omero.gateway import ScreenWrapper
from omero.gateway import MapAnnotationWrapper
from omero.rtypes import rstring, rint, rdouble
from .rois import Point, Line, Rectangle, Ellipse, Polygon, Polyline, Label


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
        if across_groups:
            conn.SERVICE_OPTS.setOmeroGroup('-1')
        project = conn.getObject('Project', project_id)
        if project is not None:
            ret = set_group(conn, project.getDetails().group.id.val)
            if ret is False:
                return None
        else:
            logging.warning(f'Project {project_id} could not be found '
                            '(check if you have permissions to it)')
            return None
    # if project_id is None, honor conn group
    dataset = DatasetWrapper(conn, DatasetI())
    dataset.setName(dataset_name)
    if description is not None:
        dataset.setDescription(description)
    dataset.save()

    if project is not None:
        link_datasets_to_project(conn, [dataset.getId()], project_id)
    return dataset.getId()


def post_image(conn, image, image_name, description=None, dataset_id=None,
               source_image_id=None, channel_list=None,
               dim_order=None, across_groups=True):
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
    dim_order : str, optional
        String containing the letters 'x', 'y', 'z', 'c' and 't' in some order,
        specifying the order of dimensions the `image` array was supplied on.
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

    if dim_order is not None:
        if type(dim_order) is not str:
            raise TypeError('dim_order must be a str')
        if set(dim_order.lower()) != set('xyzct'):
            raise ValueError('dim_order must contain letters xyzct \
                             exactly once')

    if dataset_id is not None:
        if type(dataset_id) is not int:
            raise TypeError("Dataset ID must be an integer")
        if across_groups:
            conn.SERVICE_OPTS.setOmeroGroup('-1')
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
        # if dataset_id is None, honor conn group
        dataset = None
    if dim_order is not None:
        order_dict = dict(zip(dim_order, range(5)))
        order_vector = [order_dict[c.lower()] for c in 'xyzct']
        image = np.moveaxis(image,
                            order_vector,
                            [0, 1, 2, 3, 4])
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


def post_screen(conn, screen_name, description=None):
    """Create a new screen.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object
        OMERO connection.
    screen_name : str
        Name of the new object to be created.
    description : str, optional
        Description for the new Screen.

    Returns
    -------
    screen_id : int
        Id of the new Screen.

    Notes
    -----
    Screen will be created in the Group specified in the connection. Group can
    be changed using ``conn.SERVICE_OPTS.setOmeroGroup``.

    Examples
    --------
    >>> screen_id = post_screen(conn, "My New Screen")
    >>> print(screen_id)
    238
    """
    if type(screen_name) is not str:
        raise TypeError('Screen name must be a string')

    if type(description) is not str and description is not None:
        raise TypeError('Screen description must be a string')

    screen = ScreenWrapper(conn, ScreenI())
    screen.setName(screen_name)
    if description is not None:
        screen.setDescription(description)
    screen.save()
    return screen.getId()


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

    if type(image_id) is not int:
        raise TypeError('Image ID must be an integer')

    if not isinstance(shapes, list):
        raise TypeError('Shapes must be a list')

    if not isinstance(fill_color, tuple):
        raise TypeError('Fill color must be a tuple')
    if len(fill_color) != 4:
        raise ValueError('Fill color must contain 4 integers')

    if not isinstance(stroke_color, tuple):
        raise TypeError('Stroke color must be a tuple')
    if len(stroke_color) != 4:
        raise ValueError('Stroke color must contain 4 integers')

    if type(stroke_width) is not int:
        raise TypeError('Stroke width must be an integer')

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
        if shape.markerStart is not None:
            omero_shape.markerStart = rstring(shape.markerStart)
        if shape.markerEnd is not None:
            omero_shape.markerEnd = rstring(shape.markerEnd)
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
        points_str = "".join("".join([str(x), ',', str(y), ', '])
                             for x, y in shape.points)[:-2]
        omero_shape.points = rstring(points_str)
    elif isinstance(shape, Polyline):
        omero_shape = PolylineI()
        points_str = "".join("".join([str(x), ',', str(y), ', '])
                             for x, y in shape.points)[:-2]
        omero_shape.points = rstring(points_str)
    elif isinstance(shape, Label):
        omero_shape = LabelI()
        omero_shape.x = rdouble(shape.x)
        omero_shape.y = rdouble(shape.y)
        omero_shape.fontSize = LengthI(shape.fontSize,
                                       enums.UnitsLength.POINT)
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
    rgba_int = sum([r, g, b, a])
    if rgba_int > (2**31-1):  # convert to signed 32-bit int
        rgba_int = rgba_int - 2**32
    return rgba_int
