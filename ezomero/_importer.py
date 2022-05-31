from pathlib import Path
import logging
from omero.rtypes import rstring
from omero.sys import Parameters
from omero.gateway import MapAnnotationWrapper
from ._ezomero import do_across_groups
from ezomero import post_dataset, post_project
from ezomero import get_image_ids, link_images_to_dataset
from ezomero import post_screen, link_plates_to_screen
from omero.cli import CLI
from omero.plugins.sessions import SessionsControl
from importlib import import_module
ImportControl = import_module("omero.plugins.import").ImportControl


@do_across_groups
def set_or_create_project(conn, project):
    """Create a new Project unless one already exists with that name.
    Parameter
    ---------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    project_name : str or int
        The name of the Project needed. If there is no Project with a matching
        name in the group specified in ``conn``, a new Project will be created.
    Returns
    -------
    project_id : int
        The id of the Project that was either found or created.
    """
    if isinstance(project, str):
        project_id = post_project(conn, project)
        print(f'Created new Project:{project_id}')
    elif (isinstance(project, int)):
        project_id = project
    else:
        raise TypeError("'project' must be str or int")
    return project_id


@do_across_groups
def set_or_create_dataset(conn, dataset):
    """Create a new Dataset unless one already exists with that name/Project.
    Parameter
    ---------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    project_id : int
        Id of Project in which to find/create Dataset.
    dataset_name : str
        The name of the Dataset needed. If there is no Dataset with a matching
        name in the group specified in ``conn``, in the Project specified with
        ``project_id``, a new Dataset will be created accordingly.
    Returns
    -------
    dataset_id : int
        The id of the Dataset that was either found or created.
    """
    if isinstance(dataset, str):
        dataset_id = post_dataset(conn, dataset)
        print(f'Created new Dataset:{dataset_id}')
    elif (isinstance(dataset, int)):
        dataset_id = dataset
    else:
        raise TypeError("'dataset' must be str or int")   
    return dataset_id


@do_across_groups
def set_or_create_screen(conn, screen):
    """Create a new Screen unless one already exists with that name.
    Parameter
    ---------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    screen_name : str
        The name of the Screen needed. If there is no Screen with a matching
        name in the group specified in ``conn``, a new Screen will be created.
    Returns
    -------
    screen_id : int
        The id of the Project that was either found or created.
    """
    if isinstance(screen, str):
        screen_id = post_screen(conn, screen)
        print(f'Created new screen:{screen_id}')
    elif (isinstance(screen, int)):
        screen_id = screen
    else:
        raise TypeError("'screen' must be str or int")
    return screen_id


@do_across_groups
def multi_post_map_annotation(conn, object_type, object_ids, kv_dict, ns):
    """Create a single new MapAnnotation and link to multiple images.
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
             'occupation': 'time traveler'
             'first name': 'Kyle',
             'surname': 'Reese'}
    >>> multi_post_map_annotation(conn, "Image", [23,56,78], d, ns)
    234
    """
    if type(object_ids) not in [list, int]:
        raise TypeError('object_ids must be list or integer')
    if type(object_ids) is not list:
        object_ids = [object_ids]

    if len(object_ids) == 0:
        raise ValueError('object_ids must contain one or more items')

    if type(kv_dict) is not dict:
        raise TypeError('Annotation must be of type `dict`')

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


class Importer:
    """Class for managing OMERO imports using OMERO CLI.
    Metadata from ``import.json`` (item in 'import_targets') is required for
    assigning to Project/Dataset and adding MapAnnotations.
    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    file_path : pathlike object
        Path to the file to imported into OMERO.
    import_md : dict
        Contains metadata required for import and annotation. Generally, at
        item from ``import.json`` ('import_targets').
    Attributes
    ----------
    conn : ``omero.gateway.BlitzGateway`` object.
        From parameter given at initialization.
    file_path : ``pathlib.Path`` object
        From parameter given at initialization.
    md : dict
        From ``import_md`` parameter given at initialization.
    session_uuid : str
        UUID for OMERO session represented by ``self.conn``. Supplied to
        OMERO CLI for connection purposes.
    filename : str
        Filename of file to be imported. Populated from ``self.md``.
    project : str
        Name of Project to contain the image. Populated from ``self.md``.
    dataset : str
        Name of Dataset to contain the image. Poplulated from ``self.md``.
    imported : boolean
        Flag indicating import status.
    image_ids : list of ints
        The Ids of the images in OMERO. Populated after a file is imported.
        This list may contain one or more images derived from a single file.
    """

    def __init__(self, conn, file_path, project, dataset, screen, 
                 ln_s, ann, ns):
        self.conn = conn
        self.file_path = Path(file_path)
        self.session_uuid = conn.getSession().getUuid().val
        self.filename = self.md.pop('filename')
        self.project = project
        self.dataset = dataset
        if self.project and not self.dataset:
            raise ValueError("Cannot define project but no dataset!")
        self.screen = screen
        self.imported = False
        self.image_ids = None
        self.plate_ids = None
        self.ln_s = ln_s
        self.ann = ann
        self.ns = ns

    def get_image_ids(self):
        """Get the Ids of imported images.

        Note that this will not find images if they have not been imported.
        Also, while image_ids are returned, this method also sets
        ``self.image_ids``.
        Returns
        -------
        image_ids : list of ints
            Ids of images imported from the specified client path, which
            itself is derived from ``self.file_path`` and ``self.filename``.
        """
        if self.imported is not True:
            logging.error(f'File {self.file_path} has not been imported')
            return None
        else:
            q = self.conn.getQueryService()
            params = Parameters()
            path_query = str(self.file_path).strip('/')
            params.map = {"cpath": rstring(path_query)}
            results = q.projection(
                "SELECT i.id FROM Image i"
                " JOIN i.fileset fs"
                " JOIN fs.usedFiles u"
                " WHERE u.clientPath=:cpath",
                params,
                self.conn.SERVICE_OPTS
                )
            self.image_ids = [r[0].val for r in results]
            return self.image_ids

    def get_plate_ids(self):
        """Get the Ids of imported plates.
        Note that this will not find plates if they have not been imported.
        Also, while plate_ids are returned, this method also sets
        ``self.plate_ids``.
        Returns
        -------
        plate_ids : list of ints
            Ids of plates imported from the specified client path, which
            itself is derived from ``self.file_path`` and ``self.filename``.
        """
        if self.imported is not True:
            logging.error(f'File {self.file_path} has not been imported')
            return None
        else:
            print("time to get some IDs")
            q = self.conn.getQueryService()
            print(q)
            params = Parameters()
            path_query = str(self.file_path).strip('/')
            print(f"path query: f{path_query}")
            params.map = {"cpath": rstring(path_query)}
            print(params)
            results = q.projection(
                "SELECT DISTINCT p.id FROM Plate p"
                " JOIN p.plateAcquisitions pa"
                " JOIN pa.wellSample ws"
                " JOIN ws.image i"
                " JOIN i.fileset fs"
                " JOIN fs.usedFiles u"
                " WHERE u.clientPath=:cpath",
                params,
                self.conn.SERVICE_OPTS
                )
            print(results)
            self.plate_ids = [r[0].val for r in results]
            return self.plate_ids

    def annotate_images(self):
        """Post map annotation (``self.md``) to images ``self.image_ids``.
        Returns
        -------
        map_ann_id : int
            The Id of the MapAnnotation that was created.
        """
        if len(self.image_ids) == 0:
            logging.error('No image ids to annotate')
            return None
        else:
            map_ann_id = multi_post_map_annotation(self.conn, "Image",
                                                   self.image_ids, self.ann,
                                                   self.ns)
            return map_ann_id

    def annotate_plates(self):
        """Post map annotation (``self.md``) to plates ``self.plate_ids``.
        Returns
        -------
        map_ann_id : int
            The Id of the MapAnnotation that was created.
        """
        if len(self.plate_ids) == 0:
            logging.error('No plate ids to annotate')
            return None
        else:
            map_ann_id = multi_post_map_annotation(self.conn, "Plate",
                                                   self.plate_ids, self.ann,
                                                   self.ns)
            return map_ann_id

    def organize_images(self):
        """Move images to ``self.project``/``self.dataset``.
        Returns
        -------
        image_moved : boolean
            True if images were found and moved, else False.
        """
        if not self.image_ids:
            logging.error('No image ids to organize')
            return False
        orphans = get_image_ids(self.conn)
        for im_id in self.image_ids:
            if im_id not in orphans:
                logging.error(f'Image:{im_id} not an orphan')
            else:
                if self.project:
                    project_id = set_or_create_project(self.conn, 
                                                       self.project)
                if self.dataset:
                    dataset_id = set_or_create_dataset(self.conn,
                                                       project_id,
                                                       self.dataset)
                    link_images_to_dataset(self.conn, [im_id], dataset_id)
                    print(f'Moved Image:{im_id} to Dataset:{dataset_id}')
        return True

    def organize_plates(self):
        """Move plates to ``self.screen``.
        Returns
        -------
        plate_moved : boolean
            True if plates were found and moved, else False.
        """
        if len(self.plate_ids) == 0:
            logging.error('No plate ids to organize')
            return False
        for pl_id in self.plate_ids:
            if self.screen:
                screen_id = set_or_create_screen(self.conn, self.screen)
                link_plates_to_screen(self.conn, [pl_id], screen_id)
                print(f'Moved Plate:{pl_id} to Screen:{screen_id}')
        return True

    def ezimport(self):
        """Import file using the ``--transfer=ln_s`` option.
        Parameters
        ----------
        host : str
            Hostname of OMERO server in which images will be imported.
        port : int
            Port used to connect to OMERO.server.
        Returns
        -------
        import_status : boolean
            True if OMERO import returns a 0 exit status, else False.
        """
        cli = CLI()
        cli.register('import', ImportControl, '_')
        cli.register('sessions', SessionsControl, '_')
        if self.ln_s:
            cli.invoke(['import',
                        '-k', self.conn.getSession().getUuid().val,
                        '--transfer', 'ln_s',
                        str(self.file_path)])
        else:
            cli.invoke(['import',
                        '-k', self.conn.getSession().getUuid().val,
                        str(self.file_path)])

        if cli.rv == 0:
            self.imported = True
            print(f'Imported {self.file_path}')
            return True
        else:
            logging.error(f'Import of {self.file_path} has failed!')
            return False
