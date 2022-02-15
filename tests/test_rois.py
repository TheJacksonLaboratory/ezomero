from ezomero.rois import Point, Line, Rectangle, Ellipse, Polygon
from ezomero.rois import Polyline, Label


def test_point_constructor():
    point = Point(x=4.0, y=5.0, z=1, c=0, t=5, label='test_point')
    assert point


def test_line_constructor():
    line = Line(x1=4.0, y1=5.0, x2=7.0, y2=9.0,
                z=1, c=0, t=5, label='test_line')
    assert line
    arrow = Line(x1=2.0, y1=3.0, x2=3.0, y2=4.0,
                 z=1, c=0, t=5, label='test_arrow',
                 markerStart="Arrow", markerEnd="Arrow")
    assert arrow


def test_rectangle_constructor():
    rectangle = Rectangle(x=4.0, y=5.0, width=30.0, height=40.0,
                          z=1, c=0, t=5, label='test_rectangle')
    assert rectangle


def test_ellipse_constructor():
    ellipse = Ellipse(x=4, y=5, x_rad=30.0, y_rad=40.0, z=1,
                      c=0, t=5, label='test_ellipse')
    assert ellipse


def test_polygon_constructor():
    polygon = Polygon(points=[(4.0, 5.0), (14.0, 15.0), (4.0, 15.0)],
                      z=1, c=0, t=5, label='test_polygon')
    assert polygon


def test_polyline_constructor():
    polyline = Polyline(points=[(4.0, 5.0), (14.0, 15.0), (4.0, 15.0)],
                        z=1, c=0, t=5, label='test_polyline')
    assert polyline


def test_label_constructor():
    label = Label(x=4.0, y=5.0, z=1, c=0, t=5, label='test_label',
                  fontSize=60)
    assert label
