from dataclasses import dataclass, field
from typing import List, Tuple

__all__ = ["Point",
           "Line",
           "Rectangle",
           "Ellipse",
           "Polygon"]


@dataclass(frozen=True)
class Point:
    """
    A dataclass used to represent a Point shape and create an OMERO equivalent.
    This dataclass is frozen and should not be modified after instantiation

    ...

    Attributes
    ----------
    x: float
        the x axis position of the point shape in pixels
    y: float
        the y axis position of the point shape in pixels
    z: int, optional
        the z position of the point in pixels (default is None)
        Note this is the z plane to which the shape is linked and not the sub-voxel resolution position of your shape
        If None (the default) is provided, it will not be linked to any z plane
    c: int, optional
        the channel index to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any channel
    t: int, optional
        the time frame to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any time frame
    label: str, optional
        the label of the shape (default is None)
    """

    x: float = field(metadata={'units': 'PIXELS'})
    y: float = field(metadata={'units': 'PIXELS'})
    z: int = field(default=None)
    c: int = field(default=None)
    t: int = field(default=None)
    label: str = field(default=None)


@dataclass(frozen=True)
class Line:
    """
    A dataclass used to represent a Line shape and create an OMERO equivalent.
    This dataclass is frozen and should not be modified after instantiation

    ...

    Attributes
    ----------
    x1: float
        the x axis position of the start point of the line shape in pixels
    y1: float
        the y axis position of the start point of the line shape in pixels
    x2: float
        the x axis position of the end point of the line shape in pixels
    y2: float
        the y axis position of the end point of the line shape in pixels
    z: int, optional
        the z position of the point in pixels (default is None)
        Note this is the z plane to which the shape is linked and not the sub-voxel resolution position of your shape
        If None (the default) is provided, it will not be linked to any z plane
    c: int, optional
        the channel index to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any channel
    t: int, optional
        the time frame to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any time frame
    label: str, optional
        the label of the shape (default is None)
    """

    x1: float = field(metadata={'units': 'PIXELS'})
    y1: float = field(metadata={'units': 'PIXELS'})
    x2: float = field(metadata={'units': 'PIXELS'})
    y2: float = field(metadata={'units': 'PIXELS'})
    z: int = field(default=None)
    c: int = field(default=None)
    t: int = field(default=None)
    label: str = field(default=None)


@dataclass(frozen=True)
class Rectangle:
    """
    A dataclass used to represent a Rectangle shape and create an OMERO equivalent.
    This dataclass is frozen and should not be modified after instantiation

    ...

    Attributes
    ----------
    x: float
        the x axis position of the rectangle shape in pixels
    y: float
        the y axis position of the rectangle shape in pixels
    width: float
        the width (x axis) of the rectangle shape in pixels
    height: float
        the height (y axis) of the rectangle shape in pixels
    z: int, optional
        the z position of the point in pixels (default is None)
        Note this is the z plane to which the shape is linked and not the sub-voxel resolution position of your shape
        If None (the default) is provided, it will not be linked to any z plane
    c: int, optional
        the channel index to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any channel
    t: int, optional
        the time frame to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any time frame
    label: str, optional
        the label of the shape (default is None)
    """

    x: float = field(metadata={'units': 'PIXELS'})
    y: float = field(metadata={'units': 'PIXELS'})
    width: float = field(metadata={'units': 'PIXELS'})
    height: float = field(metadata={'units': 'PIXELS'})
    z: int = field(default=None)
    c: int = field(default=None)
    t: int = field(default=None)
    label: str = field(default=None)


@dataclass(frozen=True)
class Ellipse:
    """
    A dataclass used to represent an Ellipse shape and create an OMERO equivalent.
    This dataclass is frozen and should not be modified after instantiation

    ...

    Attributes
    ----------
    x: float
        the x axis position of the ellipse shape in pixels
    y: float
        the y axis position of the ellipse shape in pixels
    x-rad: float
        the x radius of the ellipse shape in pixels
    y-rad: float
        the y radius of the ellipse shape in pixels
    z: int, optional
        the z position of the point in pixels (default is None)
        Note this is the z plane to which the shape is linked and not the sub-voxel resolution position of your shape
        If None (the default) is provided, it will not be linked to any z plane
    c: int, optional
        the channel index to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any channel
    t: int, optional
        the time frame to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any time frame
    label: str, optional
        the label of the shape (default is None)
    """

    x: float = field(metadata={'units': 'PIXELS'})
    y: float = field(metadata={'units': 'PIXELS'})
    x_rad: float = field(metadata={'units': 'PIXELS'})
    y_rad: float = field(metadata={'units': 'PIXELS'})
    z: int = field(default=None)
    c: int = field(default=None)
    t: int = field(default=None)
    label: str = field(default=None)


@dataclass(frozen=True)
class Polygon:
    """
    A dataclass used to represent a Polygon shape and create an OMERO equivalent.
    This dataclass is frozen and should not be modified after instantiation

    ...

    Attributes
    ----------
    points: list of tuples of 2 floats
        a list of 2 element tuples corresponding to the (x, y) coordinates of each vertex of the polygon
    z: int, optional
        the z position of the point in pixels (default is None)
        Note this is the z plane to which the shape is linked and not the sub-voxel resolution position of your shape
        If None (the default) is provided, it will not be linked to any z plane
    c: int, optional
        the channel index to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any channel
    t: int, optional
        the time frame to which the shape is linked (default is None)
        If None (the default) is provided, it will not be linked to any time frame
    label: str, optional
        the label of the shape (default is None)
    """

    points: List[Tuple[float, float]] = field(metadata={'units': 'PIXELS'})
    z: int = field(default=None)
    c: int = field(default=None)
    t: int = field(default=None)
    label: str = field(default=None)

