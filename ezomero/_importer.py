import logging
from os.path import abspath
from omero.rtypes import rstring
from omero.sys import Parameters
from omero.gateway import MapAnnotationWrapper
from ._gets import get_image_ids
from ._posts import post_dataset, post_project, post_screen
from ._misc import link_images_to_dataset
from ._misc import link_plates_to_screen
from omero.cli import CLI
from omero.plugins.sessions import SessionsControl
from importlib import import_module
ImportControl = import_module("omero.plugins.import").ImportControl


# import
def ezimport(conn, target, project=None, dataset=None,
             screen=None, ln_s=False, ann=None, ns=None,
             host=None, port=None,
             across_groups=True):
    """Entry point that creates Importer and runs import.

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    target : string
        Path to the import target to be imported into OMERO.
    project : str or int, optional
        The name or ID of the Project data will be imported into.
    dataset : str or int, optional
        The name or ID of the Dataset data will be imported into.
    screen : str or int, optional
        The name or ID of the Screen data will be imported into.
    ln_s : boolean, optional
        Whether to use ``ln_s`` softlinking during imports or not.
    ann : dict, optional
        Dictionary with key-value pairs to be added to imported images.
    ns : str, optional
        Namespace for the added key-value pairs.
    host : str, optional
        Hostname of the OMERO server to which data will be imported.
    port : int, optional
        Port of the OMERO server to which data will be imported.
    Returns
    -------
    plate_ids or image_ids : list of ints
        The ids of the Images/Plates that were generated by importing the
        specified target.
    """

    imp_ctl = Importer(conn, target, project, dataset, screen,
                       ln_s, ann, ns, host, port)
    imp_ctl.ezimport()
    if imp_ctl.screen:
        imp_ctl.get_plate_ids()
        imp_ctl.organize_plates()
        imp_ctl.annotate_plates()
        return imp_ctl.plate_ids

    else:
        imp_ctl.get_image_ids()
        imp_ctl.organize_images()
        imp_ctl.annotate_images()
        return imp_ctl.image_ids


def set_or_create_project(conn, project, across_groups=True):
    """Create or set a Project of interest.

    If argument is a string, creates a new Project with that name. If it is
    an integer, sets that Project ID as the Project of interest.
    Parameter
    ---------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    project : str or int
        The name or ID of the Project needed.
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


def set_or_create_dataset(conn, project_id, dataset, across_groups=True):
    """Create or set a Dataset of interest.

    If argument is a string, creates a new Dataset with that name. If it is
    an integer, sets that Dataset ID as the Dataset of interest. If
    ``project_id`` is specified, new Dataset will be created in that Project.
    Parameter
    ---------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    project_id : int
        Id of Project in which to find/create Dataset.
    dataset : str
        The name or ID of the Dataset needed.
    Returns
    -------
    dataset_id : int
        The id of the Dataset that was either found or created.
    """
    if isinstance(dataset, str):
        if project_id:
            dataset_id = post_dataset(conn, dataset, project_id=project_id)
        else:
            dataset_id = post_dataset(conn, dataset)
        print(f'Created new Dataset:{dataset_id}')
    elif (isinstance(dataset, int)):
        dataset_id = dataset
    else:
        raise TypeError("'dataset' must be str or int")
    return dataset_id


def set_or_create_screen(conn, screen, across_groups=True):
    """Create or set a Screen of interest.

    If argument is a string, creates a new Screen with that name. If it is
    an integer, sets that Screen ID as the Screen of interest.
    Parameter
    ---------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    screen : str or int
        The name or ID of the Screen needed.
    Returns
    -------
    screen_id : int
        The id of the Screen that was either found or created.
    """
    if isinstance(screen, str):
        screen_id = post_screen(conn, screen)
        print(f'Created new screen:{screen_id}')
    elif (isinstance(screen, int)):
        screen_id = screen
    else:
        raise TypeError("'screen' must be str or int")
    return screen_id


def multi_post_map_annotation(conn, object_type, object_ids,
                              kv_dict, ns, across_groups=True):
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

    Parameters
    ----------
    conn : ``omero.gateway.BlitzGateway`` object.
        OMERO connection.
    file_path : string
        Path to the import target to be imported into OMERO.
    project : str or int, optional
        The name or ID of the Project data will be imported into.
    dataset : str or int, optional
        The name or ID of the Dataset data will be imported into.
    screen : str or int, optional
        The name or ID of the Screen data will be imported into.
    ln_s : boolean, optional
        Whether to use ``ln_s`` softlinking during imports or not.
    ann : dict, optional
        Dictionary with key-value pairs to be added to imported images.
    ns : str, optional
        Namespace for the added key-value pairs.
    host : str, optional
        Hostname of the OMERO server to which data will be imported.
    port : int, optional
        Port of the OMERO server to which data will be imported.

    Important notes:
    1) Setting ``project`` also requires setting ``dataset``. Failing to do so
    will raise a ValueError.
    2) To annotate images, both ``ann`` and ``ns`` need to be set. If one of
    them is not set, no annotations will be made.
    3) For automating purposes, the arguments ``host`` and ``port`` can be set,
    avoiding a user prompt for that info. Both need to be set to bypass that
    prompt.
    4) The returned image IDs correspond to ALL image IDs accessible to this
    user that have the same ``ClientPath``, i.e., that have the same file
    name and have been imported from the same folder. In production, this
    should be a rare occurrence, but please keep that in mind if you are
    getting more image IDs than you were expecting!
    """

    def __init__(self, conn, file_path, project, dataset, screen,
                 ln_s, ann, ns, host, port):
        self.conn = conn
        self.file_path = abspath(file_path)
        self.session_uuid = conn.getSession().getUuid().val
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
        self.host = host
        self.port = port

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
        """Post map annotation (``self.ann``) to images ``self.image_ids``.
        Returns
        -------
        map_ann_id : int
            The Id of the MapAnnotation that was created.
        """
        if not self.ann or not self.ns:
            logging.warning("Missing annotation or namespace, "
                            "skipping annotations")
            return
        if len(self.image_ids) == 0:
            logging.error('No image ids to annotate')
            return None
        else:
            map_ann_id = multi_post_map_annotation(self.conn, "Image",
                                                   self.image_ids, self.ann,
                                                   self.ns)
            return map_ann_id

    def annotate_plates(self):
        """Post map annotation (``self.ann``) to plates ``self.plate_ids``.
        Returns
        -------
        map_ann_id : int
            The Id of the MapAnnotation that was created.
        """
        if not self.ann or not self.ns:
            logging.warning("Missing annotation or namespace, "
                            "skipping annotations")
            return
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
        if self.project:
            project_id = set_or_create_project(self.conn,
                                               self.project)
        else:
            project_id = None
        if self.dataset:
            dataset_id = set_or_create_dataset(self.conn,
                                               project_id,
                                               self.dataset)
        else:
            dataset_id = None
        for im_id in self.image_ids:
            if im_id not in orphans:
                logging.error(f'Image:{im_id} not an orphan')
            else:
                if dataset_id:
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

    def ezimport_ln_s(self):
        """Import file using the ``--transfer=ln_s`` option.
        Returns
        -------
        import_status : boolean
            True if OMERO import returns a 0 exit status, else False.
        """

        cli = CLI()
        cli.register('import', ImportControl, '_')
        cli.register('sessions', SessionsControl, '_')
        if self.host and self.port:
            cli.invoke(['import',
                        '-k', self.conn.getSession().getUuid().val,
                        '-s', self.host,
                        '-p', str(self.port),
                        '--transfer', 'ln_s',
                        str(self.file_path)])
        else:
            cli.invoke(['import',
                        '-k', self.conn.getSession().getUuid().val,
                        '--transfer', 'ln_s',
                        str(self.file_path)])

        if cli.rv == 0:
            self.imported = True
            print(f'Imported {self.file_path}')
            return True
        else:
            logging.error(f'Import of {self.file_path} has failed!')
            return False

    def ezimport(self):
        """Import file.
        Returns
        -------
        import_status : boolean
            True if OMERO import returns a 0 exit status, else False.
        """
        if self.ln_s:
            rs = self.ezimport_ln_s()
            return rs
        else:
            cli = CLI()
            cli.register('import', ImportControl, '_')
            cli.register('sessions', SessionsControl, '_')
            if self.host and self.port:
                cli.invoke(['import',
                            '-k', self.conn.getSession().getUuid().val,
                            '-s', self.host,
                            '-p', str(self.port),
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
