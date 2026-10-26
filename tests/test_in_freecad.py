# Runs inside the FreeCAD GUI (see run_tests.sh). Drives the navigator with a fake controller
# and checks how the model moves on screen. Writes one PASS/FAIL line per check to $DSN_TEST_OUT.

import math
import os
import sys
import traceback

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

sys.path.insert(0, os.environ["DSN_ADDON_DIR"])

from dualsense_nav import camera, commands, navigator, settings  # noqa: E402
from dualsense_nav.gamepad import State  # noqa: E402

OUT = os.environ["DSN_TEST_OUT"]
results = []


def check(name, ok, detail=""):
    results.append("%s  %s%s" % ("PASS" if ok else "FAIL", name, "  (%s)" % detail if detail else ""))


class FakeGamepad:
    name = "Fake controller"

    def __init__(self):
        self.state = State()
        self.light = None
        self.has_gyro = True
        self.motion_active = False

    def read(self):
        return self.state

    def set_motion_active(self, on):
        if not self.has_gyro:
            return False
        self.motion_active = on
        return True

    def set_light(self, rgb):
        self.light = rgb


class FakeClock:
    t = 100.0

    def __call__(self):
        return self.t


pad, clock = FakeGamepad(), FakeClock()
nav = navigator.Navigator(pad, clock=clock)


def hold(state, seconds=0.5):
    pad.state = state
    for _ in range(int(seconds * 60)):
        clock.t += 1 / 60
        nav.tick()
    pad.state = State()
    clock.t += 1 / 60
    nav.tick()


def press(button):
    hold(State(held=frozenset([button])), 1 / 60)


def cam():
    return camera.Camera(Gui.activeView())


def screen(p):
    """Where world point p sits on screen, relative to the centre (orthographic view)."""
    c = cam()
    rel = p - c.focal_point
    return rel.dot(c.right), rel.dot(c.up)


def standard_view(command):
    Gui.runCommand(command)
    Gui.runCommand("Std_ViewFitAll")
    Gui.Selection.clearSelection()


def close(a, b, tol=1e-4):
    return (a - b).Length < tol


def run():
    App.ParamGet("User parameter:BaseApp/Preferences/View").SetBool("UseNavigationAnimations", False)
    doc = App.newDocument("NavTest")
    box = doc.addObject("Part::Box", "Box")  # 10 mm cube from the origin
    doc.recompute()
    center = App.Vector(5, 5, 5)
    Gui.activeView().setCameraType("Orthographic")
    hold(State(), 0.1)

    standard_view("Std_ViewFront")
    before = (cam().position, cam().orientation.Q)
    hold(State(left=(0.1, -0.1), right=(0.1, 0.1)))
    check("small stick drift is ignored", close(before[0], cam().position) and before[1] == cam().orientation.Q)

    near = App.Vector(5, 0, 5)  # middle of the front face
    standard_view("Std_ViewFront")
    x0, _ = screen(near)
    focus = cam().focal_point
    hold(State(left=(1.0, 0.0)))
    check("left stick right: near side of model swings right", screen(near)[0] > x0 + 1, "x %.2f -> %.2f" % (x0, screen(near)[0]))
    check("orbit with nothing selected keeps the view centre", close(cam().focal_point, focus))

    standard_view("Std_ViewFront")
    _, y0 = screen(near)
    hold(State(left=(0.0, 1.0)))
    check("left stick up: near side of model swings up", screen(near)[1] > y0 + 1, "y %.2f -> %.2f" % (y0, screen(near)[1]))

    for view in ("Std_ViewTop", "Std_ViewBottom", "Std_ViewRear"):
        standard_view(view)
        c = cam()
        low_near = center - c.up * 5 - c.direction * 5  # screen-bottom edge, toward the viewer
        x0, _ = screen(low_near)
        hold(State(left=(1.0, 0.0)))
        check("left stick right in %s: lower near side swings right" % view[8:], screen(low_near)[0] > x0 + 1, "x %.2f -> %.2f" % (x0, screen(low_near)[0]))

    standard_view("Std_ViewFront")
    x0, y0 = screen(center)
    hold(State(right=(1.0, 0.0)))
    check("right stick right: model moves right", screen(center)[0] > x0 + 1)
    x1, y1 = screen(center)
    hold(State(right=(0.0, 1.0)))
    check("right stick up: model moves up", screen(center)[1] > y1 + 1 and abs(screen(center)[0] - x1) < 1e-4)

    standard_view("Std_ViewFront")
    h0, focus = cam().view_height, cam().focal_point
    hold(State(r2=1.0))
    h1 = cam().view_height
    check("R2 zooms in", h1 < h0 * 0.5, "height %.2f -> %.2f" % (h0, h1))
    hold(State(l2=1.0))
    check("L2 zooms out", cam().view_height > h1 * 2)
    check("zoom keeps the view centre", close(cam().focal_point, focus))

    standard_view("Std_ViewFront")
    right_side = App.Vector(10, 5, 5)
    _, y0 = screen(right_side)
    hold(State(held=frozenset(["r1"])))
    check("R1 rolls clockwise", screen(right_side)[1] < y0 - 1)
    _, y0 = screen(right_side)
    hold(State(held=frozenset(["l1"])), 1.0)
    check("L1 rolls counter-clockwise", screen(right_side)[1] > y0 + 1)

    standard_view("Std_ViewFront")
    hold(State(right=(1.0, 0.6)))
    Gui.Selection.addSelection(box)
    pivot_screen = screen(center)
    q0 = cam().orientation.Q
    hold(State(left=(0.8, 0.5)))
    moved = screen(center)
    check(
        "orbit turns about the selected object",
        abs(moved[0] - pivot_screen[0]) < 1e-3 and abs(moved[1] - pivot_screen[1]) < 1e-3 and cam().orientation.Q != q0,
        "selection centre %s -> %s" % (tuple(round(v, 4) for v in pivot_screen), tuple(round(v, 4) for v in moved)),
    )
    Gui.Selection.clearSelection()

    hold(State(right=(1.0, 1.0)), 1.0)
    press("triangle")
    x, y = screen(center)
    check("Triangle fits all", abs(x) < 0.5 and abs(y) < 0.5, "centre at %.2f, %.2f" % (x, y))

    expected = {
        "dpad_up": App.Vector(0, 0, -1),
        "dpad_down": App.Vector(0, 1, 0),
        "dpad_right": App.Vector(-1, 0, 0),
    }
    for button, direction in expected.items():
        press(button)
        check("%s gives the expected standard view" % button, close(cam().direction, direction), str(cam().direction))
    press("dpad_left")
    d = cam().direction
    check("dpad_left gives isometric", abs(abs(d.x) - abs(d.y)) < 1e-4 and abs(abs(d.y) - abs(d.z)) < 1e-4, str(d))

    standard_view("Std_ViewFront")
    before = cam().orientation.Q
    hold(State(gyro=(1.0, 1.0, 1.0)))
    check("gyro does nothing until X is pressed", before == cam().orientation.Q and not pad.motion_active)

    press("cross")
    check("X turns gyro on", nav.gyro_on and pad.motion_active and pad.light == navigator.LIGHT_GYRO)

    standard_view("Std_ViewFront")
    q0 = cam().orientation
    x0, _ = screen(near)
    hold(State(gyro=(0.0, 0.0, 1.0)))  # controller turning left (counter-clockwise from above) at 1 rad/s
    turned = math.degrees(cam().orientation.multiply(q0.inverted()).Angle)
    expected = (math.degrees(1.0) - nav.settings.gyro_deadzone) * nav.settings.gyro_speed * 0.5
    check("turning the controller left turns the model the same way", screen(near)[0] > x0 + 1, "near side x %.2f -> %.2f" % (x0, screen(near)[0]))
    check("gyro turn = (rate - GyroDeadzone) x GyroSpeed", abs(turned - expected) < 1.0, "%.1f deg, expected %.1f" % (turned, expected))

    standard_view("Std_ViewFront")
    far = center + cam().direction * 5
    _, y0 = screen(far)
    hold(State(gyro=(1.0, 0.0, 0.0)))
    check("tilting the controller's far edge up raises the model's far side", screen(far)[1] > y0 + 1)

    standard_view("Std_ViewFront")
    before = cam().orientation.Q
    hold(State(gyro=(0.03, -0.02, 0.03)))  # about 1.7 deg/s, typical drift at rest
    check("gyro drift below GyroDeadzone is ignored", before == cam().orientation.Q)
    hold(State(gyro=(0.0, 1.0, 0.0)))
    check("steering-wheel tilt is ignored by default", before == cam().orientation.Q)

    App.ParamGet(settings.PARAM_PATH).SetBool("GyroRoll", True)
    nav.settings.reload()
    _, y0 = screen(right_side)
    hold(State(gyro=(0.0, 1.0, 0.0)))
    check("with GyroRoll on, steering-wheel tilt right rolls clockwise", screen(right_side)[1] < y0 - 1)
    App.ParamGet(settings.PARAM_PATH).SetBool("GyroRoll", False)
    nav.settings.reload()

    press("cross")
    check("X turns gyro off", not nav.gyro_on and not pad.motion_active and pad.light == navigator.LIGHT_ON)

    pad.has_gyro = False
    press("cross")
    check("X does nothing on a controller without a gyro", not nav.gyro_on)
    pad.has_gyro = True

    standard_view("Std_ViewFront")
    press("cross")
    press("options")
    check("Options turns navigation off", not nav.settings.enabled and pad.light == navigator.LIGHT_OFF)
    check("Options off also stops the gyro", not nav.gyro_on and not pad.motion_active)
    before = cam().position
    hold(State(left=(1.0, 0.0), right=(1.0, 0.0), r2=1.0))
    check("sticks do nothing while off", close(before, cam().position))
    press("options")
    check("Options turns navigation back on", nav.settings.enabled and pad.light == navigator.LIGHT_ON)

    commands.register()
    check("toggle command is registered", "DualSenseNav_Toggle" in Gui.listCommands())

    Gui.activeView().setCameraType("Perspective")
    standard_view("Std_ViewFront")
    c = cam()
    check("perspective camera detected", c.perspective)
    d0, focus = c.node.focalDistance.getValue(), c.focal_point
    hold(State(r2=1.0))
    check("perspective R2 moves closer, keeping the view centre", cam().node.focalDistance.getValue() < d0 * 0.5 and close(cam().focal_point, focus, 1e-3))
    hold(State(left=(1.0, 0.0), right=(0.0, 1.0)))
    check("perspective orbit and pan run", not close(cam().position, focus))

    App.closeDocument(doc.Name)
    hold(State(left=(1.0, 1.0)), 0.2)
    check("no document open: no error", nav._last_error is None, str(nav._last_error))


def finish():
    try:
        run()
    except Exception:
        results.append("FAIL  test script crashed:\n" + traceback.format_exc())
    try:
        real = check_real_controller()
    except Exception:
        real = "FAIL  real controller check crashed:\n" + traceback.format_exc()
    results.append(real)
    with open(OUT, "w") as f:
        f.write("\n".join(results) + "\n")
    for name in list(App.listDocuments()):
        App.closeDocument(name)
    os._exit(0)


def check_real_controller():
    packages = os.environ.get("DSN_PACKAGES")
    if not packages or not os.path.isdir(packages):
        return "SKIP  real controller (GameController bindings not installed)"
    sys.path.append(packages)
    from dualsense_nav.gamepad import Gamepad

    real = Gamepad()
    state = real.read()
    for _ in range(20):  # give macOS a moment to report the controller
        if state is not None:
            break
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(100, loop.quit)
        loop.exec()
        real._next_scan = 0.0
        state = real.read()
    if state is None:
        return "INFO  real controller: none found from FreeCAD (is it connected?)"
    return "PASS  real controller read inside FreeCAD: %s, sticks %s %s" % (real.name, state.left, state.right)


QtCore.QTimer.singleShot(120000, lambda: os._exit(1))  # never leave a stuck FreeCAD behind
QtCore.QTimer.singleShot(1500, finish)
