"""Turns controller input into camera moves in the active FreeCAD 3D view.

Left stick orbits, right stick pans, R2/L2 zoom in/out, R1/L1 roll, Triangle fits all,
the D-pad picks standard views and Options turns navigation on and off. Moves follow the
model: push the left stick right and the side of the model nearest you swings right.

X turns gyro rotation on and off. While it is on, the model turns the way you turn the
controller, as if you were holding the model in its place.
"""

import math
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from . import camera
from .settings import Settings

# Buttons that run a FreeCAD view command when pressed.
BUTTON_COMMANDS = {
    "triangle": "Std_ViewFitAll",
    "dpad_up": "Std_ViewTop",
    "dpad_down": "Std_ViewFront",
    "dpad_right": "Std_ViewRight",
    "dpad_left": "Std_ViewIsometric",
}

LIGHT_ON = (0.0, 0.35, 1.0)
LIGHT_GYRO = (0.6, 0.0, 1.0)
LIGHT_OFF = (0.3, 0.1, 0.0)

TICK_MS = 16
MAX_STEP_SECONDS = 0.05  # a stalled frame never turns into one big jump
SETTINGS_RELOAD_SECONDS = 2.0
TRIGGER_DEADZONE = 0.04


def shape(value, deadzone, curve):
    """Ignores drift around centre, rescales the rest to 0..1 and applies the response curve."""
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    scaled = min((magnitude - deadzone) / (1.0 - deadzone), 1.0)
    return math.copysign(scaled**curve, value)


def soft_deadzone(value, deadzone):
    """Shrinks value towards zero by deadzone, so sensor drift is ignored without a jump at the edge."""
    return math.copysign(max(abs(value) - deadzone, 0.0), value)


def active_3d_view():
    if Gui.ActiveDocument is None:
        return None
    view = Gui.activeView()
    return view if view is not None and hasattr(view, "getCameraNode") else None


def selection_center():
    """Centre of the bounding box around everything selected, in world coordinates, or None."""
    try:
        import Part
    except ImportError:
        return None
    box = App.BoundBox()
    for sel in Gui.Selection.getSelectionEx("", 0):
        for sub in sel.SubElementNames or ("",):
            try:
                shape_ = Part.getShape(sel.Object, sub, needSubElement=True)
            except Exception:
                continue
            if not shape_.isNull():
                box.add(shape_.BoundBox)
    return box.Center if box.isValid() else None


def yaw_sign(cam):
    """+1 or -1 so that turning about world Z moves the near, lower side of the model the way the
    stick points, including when looking up from below or with the view upside down."""
    near = -cam.direction - cam.up
    near.z = 0
    return -1.0 if camera.Z.cross(near).dot(cam.right) < 0 else 1.0


class Navigator:
    def __init__(self, gamepad, clock=time.monotonic):
        self.gamepad = gamepad
        self.settings = Settings()
        self._clock = clock
        self._last_tick = None
        self._next_reload = 0.0
        self._held = frozenset()
        self._connected = None
        self.gyro_on = False
        self._pivot = None  # world point the current orbit turns about
        self._yaw_sign = 1.0
        self._up_sign = 1.0
        self._last_error = None
        self._timer = QtCore.QTimer()
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def toggle(self):
        self.set_enabled(not self.settings.enabled)

    def set_enabled(self, on):
        self.settings.set_enabled(on)
        self.settings.reload()
        self._pivot = None
        self._update_light()
        self._announce("DualSense navigation %s" % ("on" if on else "off"))

    def toggle_gyro(self):
        self.set_gyro(not self.gyro_on)

    def set_gyro(self, on):
        has_gyro = self.gamepad.set_motion_active(on)
        if on and not has_gyro:
            self._announce("This controller has no gyro")
            return
        self.gyro_on = on
        self._pivot = None
        self._update_light()
        self._announce("Gyro rotation %s" % ("on" if on else "off"))

    def tick(self):
        try:
            self._tick()
            self._last_error = None
        except Exception as e:
            # Report a failure once rather than 60 times a second.
            if str(e) != self._last_error:
                self._last_error = str(e)
                App.Console.PrintWarning("DualSense navigation: %s\n" % e)

    def _tick(self):
        now = self._clock()
        dt = 0.0 if self._last_tick is None else min(max(now - self._last_tick, 0.0), MAX_STEP_SECONDS)
        self._last_tick = now
        if now >= self._next_reload:
            self._next_reload = now + SETTINGS_RELOAD_SECONDS
            self.settings.reload()

        state = self.gamepad.read()
        self._note_connection()
        if state is None:
            self._held = frozenset()
            self._pivot = None
            return

        pressed = state.held - self._held
        self._held = state.held
        if "options" in pressed:
            self.toggle()
        if not self.settings.enabled:
            if self.gyro_on:
                self.gyro_on = False
                self.gamepad.set_motion_active(False)
                self._update_light()
            return
        if "cross" in pressed:
            self.toggle_gyro()

        view = active_3d_view()
        if view is None:
            self._pivot = None
            return
        for button in pressed:
            if button in BUTTON_COMMANDS:
                self._pivot = None
                Gui.runCommand(BUTTON_COMMANDS[button])
        self._move(view, state, dt)

    def _move(self, view, state, dt):
        s = self.settings

        def stick(value, invert):
            return shape(value, s.deadzone, s.curve) * (-1.0 if invert else 1.0)

        turn_x = stick(state.left[0], s.invert_orbit_x)
        turn_y = stick(state.left[1], s.invert_orbit_y)
        pan_x = stick(state.right[0], s.invert_pan_x)
        pan_y = stick(state.right[1], s.invert_pan_y)
        zoom = shape(state.r2, TRIGGER_DEADZONE, s.curve) - shape(state.l2, TRIGGER_DEADZONE, s.curve)
        roll = ("r1" in state.held) - ("l1" in state.held)

        # Gyro angles for this frame in degrees. The controller's axes (right, away from you, up)
        # stand for the screen's (right, into the screen, up), so the model copies the controller.
        gyro_pitch = gyro_spin = gyro_yaw = 0.0
        if self.gyro_on:
            gx, gy, gz = (soft_deadzone(math.degrees(v), s.gyro_deadzone) * s.gyro_speed * dt for v in state.gyro)
            gyro_pitch = -gx if s.invert_gyro_pitch else gx
            gyro_yaw = -gz if s.invert_gyro_yaw else gz
            gyro_spin = gy if s.gyro_roll else 0.0

        turning = turn_x or turn_y or roll or gyro_pitch or gyro_yaw or gyro_spin
        if not turning:
            self._pivot = None
        if not (turning or pan_x or pan_y or zoom) or dt == 0.0:
            return

        cam = camera.Camera(view)
        if turning:
            if self._pivot is None:
                center = selection_center() if s.orbit_around_selection else None
                self._pivot = center if center is not None else cam.focal_point
                self._yaw_sign = yaw_sign(cam)
                self._up_sign = -1.0 if cam.up.z < 0 else 1.0
            step = s.orbit_speed * dt
            rotation = (
                App.Rotation(camera.Z, self._yaw_sign * turn_x * step + self._up_sign * gyro_yaw)
                .multiply(App.Rotation(cam.right, -turn_y * step + gyro_pitch))
                .multiply(App.Rotation(cam.direction, roll * s.roll_speed * dt + gyro_spin))
            )
            cam.orbit(rotation, self._pivot)
        if pan_x or pan_y:
            cam.pan(pan_x * s.pan_speed * dt, pan_y * s.pan_speed * dt)
        if zoom:
            cam.zoom(math.exp(zoom * s.zoom_speed * dt))

    def _note_connection(self):
        name = self.gamepad.name
        if name == self._connected:
            return
        if name is None:
            App.Console.PrintMessage("DualSense navigation: controller disconnected\n")
        else:
            App.Console.PrintMessage("DualSense navigation: using %s\n" % name)
        self._connected = name
        self.gyro_on = False  # a newly connected controller starts with its motion sensors off
        self._update_light()

    def _update_light(self):
        if self.settings.light_bar:
            if not self.settings.enabled:
                self.gamepad.set_light(LIGHT_OFF)
            else:
                self.gamepad.set_light(LIGHT_GYRO if self.gyro_on else LIGHT_ON)

    def _announce(self, message):
        Gui.getMainWindow().statusBar().showMessage(message, 3000)
        App.Console.PrintMessage(message + "\n")
