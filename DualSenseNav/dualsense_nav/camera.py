"""Moves the camera of a FreeCAD 3D view, working in world coordinates with FreeCAD vectors."""

import math

from pivy import coin  # must be imported before a view will hand out its camera node
import FreeCAD as App

X = App.Vector(1, 0, 0)
Y = App.Vector(0, 1, 0)
Z = App.Vector(0, 0, 1)


class Camera:
    """The Coin camera of a 3D view. Coin cameras look down their local -Z axis with +Y up."""

    def __init__(self, view):
        self.node = view.getCameraNode()
        self.perspective = isinstance(self.node, coin.SoPerspectiveCamera)

    @property
    def position(self):
        return App.Vector(*self.node.position.getValue().getValue())

    @position.setter
    def position(self, v):
        self.node.position.setValue(v.x, v.y, v.z)

    @property
    def orientation(self):
        return App.Rotation(*self.node.orientation.getValue().getValue())

    @orientation.setter
    def orientation(self, r):
        self.node.orientation.setValue(coin.SbRotation(*r.Q))

    @property
    def right(self):
        return self.orientation.multVec(X)

    @property
    def up(self):
        return self.orientation.multVec(Y)

    @property
    def direction(self):
        return self.orientation.multVec(-Z)

    @property
    def focal_point(self):
        return self.position + self.direction * self.node.focalDistance.getValue()

    @property
    def view_height(self):
        """Height of the visible area at the focal point, in model units."""
        if self.perspective:
            return 2 * self.node.focalDistance.getValue() * math.tan(self.node.heightAngle.getValue() / 2)
        return self.node.height.getValue()

    def orbit(self, rotation, pivot):
        """Turns the model by `rotation` about `pivot`, by moving the camera the opposite way."""
        back = rotation.inverted()
        self.position = pivot + back.multVec(self.position - pivot)
        self.orientation = back.multiply(self.orientation)

    def pan(self, dx, dy):
        """Slides the model across the screen by dx, dy view heights (positive is right, up)."""
        shift = (self.right * dx + self.up * dy) * self.view_height
        self.position = self.position - shift

    def zoom(self, factor):
        """Magnifies the model by `factor` (above 1 zooms in), keeping the focal point in place."""
        if self.perspective:
            focus = self.focal_point
            distance = max(self.node.focalDistance.getValue() / factor, 1e-6)
            self.position = focus - self.direction * distance
            self.node.focalDistance.setValue(distance)
        else:
            self.node.height.setValue(max(self.node.height.getValue() / factor, 1e-6))
