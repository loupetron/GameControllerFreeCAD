"""Tuning values, kept in FreeCAD's parameters so they can be changed in Tools > Edit parameters."""

import FreeCAD as App

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/DualSenseNav"

# (attribute, parameter name, default)
FIELDS = (
    ("enabled", "Enabled", True),
    ("deadzone", "Deadzone", 0.12),  # stick travel ignored around centre, 0..1
    ("curve", "Curve", 2.0),  # 1 = linear; higher gives finer control near centre
    ("orbit_speed", "OrbitSpeed", 120.0),  # degrees per second at full stick
    ("roll_speed", "RollSpeed", 90.0),  # degrees per second while L1/R1 is held
    ("pan_speed", "PanSpeed", 0.8),  # view heights per second at full stick
    ("zoom_speed", "ZoomSpeed", 1.6),  # 1.6 is about 5x magnification per second at full trigger
    ("invert_orbit_x", "InvertOrbitX", False),
    ("invert_orbit_y", "InvertOrbitY", False),
    ("invert_pan_x", "InvertPanX", False),
    ("invert_pan_y", "InvertPanY", False),
    ("gyro_speed", "GyroSpeed", 1.5),  # model turns this many times as far as the controller
    ("gyro_deadzone", "GyroDeadzone", 2.0),  # degrees per second of controller turn ignored (sensor drift)
    ("gyro_roll", "GyroRoll", False),  # also roll the view when tilting the controller like a steering wheel
    ("invert_gyro_yaw", "InvertGyroYaw", False),
    ("invert_gyro_pitch", "InvertGyroPitch", False),
    ("orbit_around_selection", "OrbitAroundSelection", True),
    ("light_bar", "LightBar", True),
)


class Settings:
    def __init__(self):
        self._params = App.ParamGet(PARAM_PATH)
        existing = {name for _, name, _ in self._params.GetContents() or ()}
        for _, name, default in FIELDS:
            if name not in existing:
                self._write(name, default)
        self.reload()

    def reload(self):
        for attr, name, default in FIELDS:
            if isinstance(default, bool):
                value = self._params.GetBool(name, default)
            else:
                value = self._params.GetFloat(name, default)
            setattr(self, attr, value)

    def set_enabled(self, on):
        self.enabled = on
        self._write("Enabled", on)

    def _write(self, name, value):
        if isinstance(value, bool):
            self._params.SetBool(name, value)
        else:
            self._params.SetFloat(name, value)
