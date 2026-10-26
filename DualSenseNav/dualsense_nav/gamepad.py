"""Reads a game controller through Apple's GameController framework (macOS 11 or later)."""

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    """One snapshot of the controller. Sticks and triggers are raw values; up and right are positive."""

    left: tuple = (0.0, 0.0)
    right: tuple = (0.0, 0.0)
    l2: float = 0.0
    r2: float = 0.0
    held: frozenset = frozenset()  # names of the buttons held down
    # Rotation rate in radians per second about the controller's own axes: x points right, y away
    # from you, z up out of the face. Zero unless motion sensing was switched on with set_motion_active.
    gyro: tuple = (0.0, 0.0, 0.0)


class Gamepad:
    """The first connected controller with a full gamepad layout (DualSense, DualShock 4, Xbox, ...).

    macOS only delivers input while FreeCAD is the frontmost app, so the view never moves
    from the controller while you work in another app.
    """

    RESCAN_SECONDS = 1.0

    def __init__(self):
        import GameController  # PyObjC bindings, installed by install.sh

        self._gc = GameController
        self._controller = None
        self._next_scan = 0.0

    @property
    def name(self):
        return str(self._controller.vendorName()) if self._controller is not None else None

    def read(self):
        """Returns the current State, or None when no controller is connected."""
        now = time.monotonic()
        if now >= self._next_scan:
            self._next_scan = now + self.RESCAN_SECONDS
            self._rescan()
        if self._controller is None:
            return None
        pad = self._controller.extendedGamepad()
        if pad is None:
            return None

        buttons = {
            "cross": pad.buttonA(),
            "triangle": pad.buttonY(),
            "options": pad.buttonMenu(),
            "l1": pad.leftShoulder(),
            "r1": pad.rightShoulder(),
            "dpad_up": pad.dpad().up(),
            "dpad_down": pad.dpad().down(),
            "dpad_left": pad.dpad().left(),
            "dpad_right": pad.dpad().right(),
        }
        left, right = pad.leftThumbstick(), pad.rightThumbstick()
        motion = self._controller.motion()
        gyro = (0.0, 0.0, 0.0)
        if motion is not None and motion.hasRotationRate() and motion.sensorsActive():
            rate = motion.rotationRate()
            gyro = (rate.x, rate.y, rate.z)
        return State(
            left=(left.xAxis().value(), left.yAxis().value()),
            right=(right.xAxis().value(), right.yAxis().value()),
            l2=pad.leftTrigger().value(),
            r2=pad.rightTrigger().value(),
            held=frozenset(name for name, button in buttons.items() if button.isPressed()),
            gyro=gyro,
        )

    def set_motion_active(self, on):
        """Switches the motion sensors on or off (they cost battery). Returns False if there is no gyro."""
        motion = self._controller.motion() if self._controller is not None else None
        if motion is None or not motion.hasRotationRate():
            return False
        if motion.sensorsRequireManualActivation():
            motion.setSensorsActive_(on)
        return True

    def set_light(self, rgb):
        """Sets the light bar colour, on controllers that have one."""
        light = self._controller.light() if self._controller is not None else None
        if light is not None:
            light.setColor_(self._gc.GCColor.alloc().initWithRed_green_blue_(*rgb))

    def _rescan(self):
        pads = [c for c in self._gc.GCController.controllers() if c.extendedGamepad() is not None]
        if self._controller not in pads:
            self._controller = pads[0] if pads else None
