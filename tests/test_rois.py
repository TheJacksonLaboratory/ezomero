from ezomero.rois import Point, Line, Rectangle, Ellipse, Polygon
from ezomero.rois import Polyline, Label


def test_point_constructor():
    point1 = Point(1.0, 2.0)
    assert point1
    point2 = Point(x=4.0, y=5.0, z=1, c=0, t=5, label='test_point')
    assert point2
    point3 = Point(x=3.0, y=7.0, z=2, c=1, t=4, label='test_point2',
                   fill_color=(0, 0, 0, 0), stroke_color=(255, 255, 0),
                   stroke_width=2.0)
    assert point3


def test_line_constructor():
    line1 = Line(1.0, 2.0, 3.0, 4.0)
    assert line1
    line2 = Line(x1=4.0, y1=5.0, x2=7.0, y2=9.0,
                 z=1, c=0, t=5, label='test_line')
    assert line2
    line3 = Line(x1=4.0, y1=5.0, x2=7.0, y2=9.0,
                 z=1, c=0, t=5, label='test_line',
                 fill_color=(0, 0, 0, 0), stroke_color=(255, 255, 0),
                 stroke_width=2.0)
    assert line3
    arrow = Line(x1=2.0, y1=3.0, x2=3.0, y2=4.0,
                 z=1, c=0, t=5, label='test_arrow',
                 markerStart="Arrow", markerEnd="Arrow")
    assert arrow


def test_rectangle_constructor():
    rectangle1 = Rectangle(1.0, 2.0, 3.0, 4.0)
    assert rectangle1
    rectangle2 = Rectangle(x=4.0, y=5.0, width=30.0, height=40.0,
                           z=1, c=0, t=5, label='test_rectangle')
    assert rectangle2
    rectangle3 = Rectangle(x=4.0, y=5.0, width=30.0, height=40.0,
                           z=1, c=0, t=5, label='test_rectangle',
                           fill_color=(0, 0, 0, 0), stroke_color=(255, 255, 0),
                           stroke_width=2.0)
    assert rectangle3


def test_ellipse_constructor():
    ellipse1 = Ellipse(1.0, 2.0, 3.0, 4.0)
    assert ellipse1
    ellipse2 = Ellipse(x=4, y=5, x_rad=30.0, y_rad=40.0, z=1,
                       c=0, t=5, label='test_ellipse')
    assert ellipse2
    ellipse3 = Ellipse(x=4, y=5, x_rad=30.0, y_rad=40.0, z=1,
                       c=0, t=5, label='test_ellipse',
                       fill_color=(0, 0, 0, 0), stroke_color=(255, 255, 0),
                       stroke_width=2.0)
    assert ellipse3


def test_polygon_constructor():
    polygon1 = Polygon([(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)])
    assert polygon1
    polygon2 = Polygon(points=[(4.0, 5.0), (14.0, 15.0), (4.0, 15.0)],
                       z=1, c=0, t=5, label='test_polygon')
    assert polygon2
    polygon3 = Polygon(points=[(4.0, 5.0), (14.0, 15.0), (4.0, 15.0)],
                       z=1, c=0, t=5, label='test_polygon',
                       fill_color=(0, 0, 0, 0), stroke_color=(255, 255, 0),
                       stroke_width=2.0)
    assert polygon3


def test_polyline_constructor():
    polyline1 = Polyline([(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)])
    assert polyline1
    polyline2 = Polyline(points=[(4.0, 5.0), (14.0, 15.0), (4.0, 15.0)],
                         z=1, c=0, t=5, label='test_polyline')
    assert polyline2
    polyline3 = Polyline(points=[(4.0, 5.0), (14.0, 15.0), (4.0, 15.0)],
                         z=1, c=0, t=5, label='test_polyline',
                         fill_color=(0, 0, 0, 0), stroke_color=(255, 255, 0),
                         stroke_width=2.0)
    assert polyline3


def test_label_constructor():
    label1 = Label(1.0, 2.0, "test_label", 60)
    assert label1
    label2 = Label(x=4.0, y=5.0, z=1, c=0, t=5, label='test_label',
                   fontSize=60)
    assert label2
    label3 = Label(x=4.0, y=5.0, z=1, c=0, t=5, label='test_label',
                   fontSize=60, fill_color=(0, 0, 0, 0),
                   stroke_color=(255, 255, 0), stroke_width=2.0)
    assert label3
