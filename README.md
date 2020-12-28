# ezomero
A module with convenience functions for writing Python code that interacts with OMERO.


# Installation

Just `pip install ezomero` and you should be good to go! The repo contains a `requirements.txt` file with the specific package versions we test `ezomero` with, but any Python>=3.6 and latest `omero-py` and `numpy` _should_ work -  note that this package is in active development!

# Usage

In general, you will need to create a `BlitzGateway` object using `omero-py`, successfully do something like `conn.connect()` and then pass the `conn` object to most of these helper functions along with function-specific parameters.


# Functions

## `post` functions

### `post_dataset(conn, dataset_name, project_id, description)`

Creates a new dataset. Returns a (new) dataset ID.

### `post_image(conn, image, image_name, description=None, dataset_id=None, source_image_id=None, channel_list=None)`

Creates a new OMERO image from a numpy array. Returns a (new) image ID.

### `post_map_annotation(conn, object_type, object_ids, kv_dict, ns)`

Creates a new MapAnnotation and links to images. Returns a (new) MapAnnotation ID.

### `post_project(conn, project_name, description=None)`

Creates a new project. Returns a (new) project ID.

## `get` functions

### `get_image(conn, image_id, no_pixels=False, start_coords=None, axis_lengths=None, xyzct=False, pad=False)`

Gets omero image object along with pixels as a numpy array. Returns an `omero.gateway.ImageWrapper` object along with an `ndarray` containing the image pixels.

### `get_image_ids(conn, dataset=None, well=None)`

Returns a list of image ids based on project and dataset. Returns a list of `int`s with the desired IDs.

### `get_map_annotation_ids(conn, object_type, object_id, ns=None)`

Get IDs of map annotations associated with an object. Returns a list of `int`s with the desired IDs.

### `get_map_annotation(conn, map_ann_id)`

Get the value of a map annotation object. Returns a `dict` with the contents of the desired `MapAnnotation`.

### `get_group_id(conn, group_name)`

Get ID of a group based on group name. Must be an exact match. Case sensitive. Returns a single `int`.

### `get_user_id(conn, user_name)`

Get ID of a user based on username. Must be an exact match. Case sensitive. Returns a single `int`.

### `get_original_filepaths(conn, image_id, fpath='repo')`

Get paths to original files for specified image. Returns a `list` of `str`.

## `put` functions

### `put_map_annotation(conn, map_ann_id, kv_dict, ns=None)`

Update an existing map annotation with new values (kv pairs). 

## Filter functions

### `filter_by_filename(conn, im_ids, imported_filename)`

Filter list of image ids by originalFile name. Returns a `list` of `int` image IDs that match.

### `image_has_imported_filename(conn, im_id, imported_filename)`

DEPRECATED. Ask whether an image is associated with a particular image file. Returns a boolean.

## Linking functions

### `link_images_to_dataset(conn, image_ids, dataset_id)`

Adds the images with given IDs to the dataset with given ID. 

### `link_datasets_to_project(conn, dataset_ids, project_id)`

Adds the datasets with given IDs to the project with given ID. 

## `print` functions

### `print_map_annotation(conn, map_ann_id)`

Print some information and value of a map annotation.

### `print_groups(conn)`

Print all Groups with IDs and membership info.

### `print_projects(conn)`

Print all available Projects.

### `print_datasets(conn, project=None)`

Print all available Datasets for a given Project.

## Other functions

### `set_group(conn, group_id)`

Safely switch OMERO group. This function will change the user's current group to that specified by `group_id`, but only if the user is a member of that group. Returns a boolean with success status.