"""Tries out the DualSense adaptive triggers (resistance, a click or a buzz in L2/R2) from FreeCAD's Python console.

An experiment, not part of the add-on: it finds out whether macOS, the PyObjC bindings and the controller let us
set trigger effects, and what they feel like while zooming. See README.md next to this file.

In FreeCAD, open View > Panels > Report view and Python console, then:

    import sys; sys.path.insert(0, "/path/to/GameControllerFreeCAD/experiments/adaptive_triggers")
    import trigger_probe as tp
    tp.report()              # what this controller and macOS support
    tp.tour()                # each effect on R2 in turn, 6 seconds each
    tp.feedback(0.3, 0.8)    # resistance from 30% of the pull, strength 0.8, on both triggers
    tp.watch()               # log pull, arm position, mode and status for 10 seconds
    tp.off()                 # plain triggers again (tp.stop() also ends a tour or watch)

Positions, strengths, amplitudes and frequencies run from 0 to 1; which is "l2", "r2" or "both".
Output goes to the Report view.
"""

import os
import platform
import sys
import time

import FreeCAD as App
from PySide import QtCore

# Names for the GCDualSenseAdaptiveTriggerMode and GCDualSenseAdaptiveTriggerStatus values.
MODES = {0: "off", 1: "feedback", 2: "weapon", 3: "vibration", 4: "slope feedback"}
STATUSES = {
    -1: "unknown",
    0: "feedback, no load",
    1: "feedback, load applied",
    2: "weapon ready",
    3: "weapon firing",
    4: "weapon fired",
    5: "vibration, not vibrating",
    6: "vibration, vibrating",
    7: "slope ready",
    8: "slope, applying load",
    9: "slope finished",
}

# Every effect the framework offers. The last three came after the first DualSense support.
SELECTORS = (
    "setModeOff",
    "setModeFeedbackWithStartPosition:resistiveStrength:",
    "setModeWeaponWithStartPosition:endPosition:resistiveStrength:",
    "setModeVibrationWithStartPosition:amplitude:frequency:",
    "setModeSlopeFeedbackWithStartPosition:endPosition:startStrength:endStrength:",
    "setModeFeedbackWithResistiveStrengths:",
    "setModeVibrationWithAmplitudes:frequency:",
)

REPORT_DELAY_MS = 300  # time for the controller to take an effect before we read back its mode and status

_timers = []  # running tour and watch timers, kept so they aren't garbage collected


def _say(message):
    App.Console.PrintMessage("Trigger probe: %s\n" % message)


def _gc():
    """The GameController bindings, from the folder install.sh puts them in."""
    path = os.path.join(App.getUserAppDataDir(), "AdditionalPythonPackages", "py%d%d" % sys.version_info[:2])
    if os.path.isdir(path) and path not in sys.path:
        sys.path.append(path)
    import GameController

    return GameController


def _controller():
    pads = [c for c in _gc().GCController.controllers() if c.extendedGamepad() is not None]
    return pads[0] if pads else None


def _triggers(which):
    """[(name, GCDualSenseAdaptiveTrigger)] for "l2", "r2" or "both"."""
    if which not in ("l2", "r2", "both"):
        raise ValueError('which must be "l2", "r2" or "both", not %r' % which)
    controller = _controller()
    if controller is None:
        raise RuntimeError("no controller connected")
    pad = controller.extendedGamepad()
    if not pad.isKindOfClass_(_gc().GCDualSenseGamepad):
        raise RuntimeError("%s has no adaptive triggers (only the DualSense does)" % controller.vendorName())
    found = (("L2", pad.leftTrigger()), ("R2", pad.rightTrigger()))
    return [(name, trigger) for name, trigger in found if which in ("both", name.lower())]


def _describe(trigger):
    return "pull %.1f, arm %.1f, %s / %s" % (
        trigger.value(),
        trigger.armPosition(),
        MODES.get(trigger.mode(), trigger.mode()),
        STATUSES.get(trigger.status(), trigger.status()),
    )


def _check(**values):
    for name, value in values.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError("%s must be between 0 and 1, not %s" % (name, value))


def _tenths(struct_name, values):
    """One of the framework's positional structs: a value for each tenth of the pull, from rest to fully pulled."""
    values = tuple(float(v) for v in values)
    if len(values) != 10:
        raise ValueError("give 10 values, one for each tenth of the pull, not %d" % len(values))
    _check(**{"value %d" % (i + 1): v for i, v in enumerate(values)})
    return getattr(_gc(), struct_name)(values)


def _apply(which, selector, *args):
    """Calls an effect selector on the trigger(s), then logs the mode and status they report back."""
    for name, trigger in _triggers(which):
        if not trigger.respondsToSelector_(selector):
            _say("%s: this macOS can't do %s" % (name, selector))
            continue
        getattr(trigger, selector.replace(":", "_"))(*args)
        QtCore.QTimer.singleShot(
            REPORT_DELAY_MS, lambda name=name, trigger=trigger: _say("%s set: %s" % (name, _describe(trigger)))
        )


def _every(ms, step):
    """Calls step every ms milliseconds until it returns True or raises."""
    timer = QtCore.QTimer()

    def run():
        try:
            done = step()
        except Exception as e:
            _say("stopped: %s" % e)
            done = True
        if done:
            timer.stop()
            _timers.remove(timer)

    timer.timeout.connect(run)
    timer.start(ms)
    _timers.append(timer)


def off(which="both"):
    """Plain triggers again."""
    _apply(which, "setModeOff")


def feedback(start, strength, which="both"):
    """Steady resistance from start (0 = at rest, 1 = fully pulled) to the end of the pull."""
    _check(start=start, strength=strength)
    _apply(which, "setModeFeedbackWithStartPosition:resistiveStrength:", start, strength)


def weapon(start, end, strength, which="both"):
    """Resistance between start and end that gives way with a click, like a gun trigger."""
    _check(start=start, end=end, strength=strength)
    _apply(which, "setModeWeaponWithStartPosition:endPosition:resistiveStrength:", start, end, strength)


def vibration(start, amplitude, frequency, which="both"):
    """A buzz once the trigger is pulled past start."""
    _check(start=start, amplitude=amplitude, frequency=frequency)
    _apply(which, "setModeVibrationWithStartPosition:amplitude:frequency:", start, amplitude, frequency)


def slope(start, end, start_strength, end_strength, which="both"):
    """Resistance that ramps from start_strength at start to end_strength at end."""
    _check(start=start, end=end, start_strength=start_strength, end_strength=end_strength)
    _apply(
        which,
        "setModeSlopeFeedbackWithStartPosition:endPosition:startStrength:endStrength:",
        start,
        end,
        start_strength,
        end_strength,
    )


def zones(strengths, which="both"):
    """Resistance set separately for each tenth of the pull: 10 strengths from rest to fully pulled."""
    strengths = _tenths("GCDualSenseAdaptiveTriggerPositionalResistiveStrengths", strengths)
    _apply(which, "setModeFeedbackWithResistiveStrengths:", strengths)


def vibration_zones(amplitudes, frequency, which="both"):
    """A buzz set separately for each tenth of the pull: 10 amplitudes from rest to fully pulled."""
    _check(frequency=frequency)
    amplitudes = _tenths("GCDualSenseAdaptiveTriggerPositionalAmplitudes", amplitudes)
    _apply(which, "setModeVibrationWithAmplitudes:frequency:", amplitudes, frequency)


def report():
    """Logs what the connected controller and this macOS support."""
    import objc

    gc = _gc()
    _say("macOS %s, PyObjC %s" % (platform.mac_ver()[0], objc.__version__))
    controller = _controller()
    if controller is None:
        _say("no controller connected")
        return
    pad = controller.extendedGamepad()
    _say("%s, profile %s" % (controller.vendorName(), pad.className()))
    if pad.isKindOfClass_(gc.GCDualSenseGamepad):
        for name, trigger in _triggers("both"):
            _say("%s: %s" % (name, _describe(trigger)))
        for selector in SELECTORS:
            _say("  %s %s" % ("yes" if pad.rightTrigger().respondsToSelector_(selector) else "NO ", selector))
    else:
        _say("no adaptive triggers on this controller (only the DualSense has them)")
    haptics = controller.haptics() if controller.respondsToSelector_("haptics") else None
    localities = sorted(str(x) for x in haptics.supportedLocalities()) if haptics is not None else ()
    _say("haptic localities: %s" % (", ".join(localities) or "none"))


def watch(seconds=10.0, which="both"):
    """Logs each trigger's pull, arm position, mode and status whenever one of them changes."""
    triggers = _triggers(which)
    last = {}
    end = time.monotonic() + seconds

    def poll():
        for name, trigger in triggers:
            line = "%s: %s" % (name, _describe(trigger))
            if last.get(name) != line:
                last[name] = line
                _say(line)
        if time.monotonic() >= end:
            _say("watch finished")
            return True

    _every(50, poll)


# Each stop of the tour: what to judge while pulling, and the effect that sets it up.
TOUR = (
    ("plain trigger, for comparison", off, ()),
    ("light, even resistance over the whole pull: is a slow zoom easier to hold?", feedback, (0.0, 0.2)),
    ("firm from halfway: a gear change between slow and fast zoom?", feedback, (0.5, 0.7)),
    ("resistance that grows with the pull, like the zoom's response curve", slope, (0.0, 1.0, 0.0, 0.8)),
    ("stepped zones: can you find a zoom speed by feel?", zones, ((0, 0, 0, 0.3, 0.3, 0.3, 0.6, 0.6, 0.6, 0.9),)),
    ("a click between 30% and 60% that you pull through", weapon, (0.3, 0.6, 0.8)),
    ("a buzz past 80%: zooming at full speed", vibration, (0.8, 0.4, 0.3)),
)


def tour(seconds=6.0, which="r2"):
    """Sets each effect in TOUR in turn, then turns the trigger(s) off. Pull while each one is on.

    With a document open the triggers still zoom, so each effect can be judged while zooming.
    """
    _triggers(which)  # fail now rather than halfway through
    steps = list(TOUR)

    def step():
        if not steps:
            off(which)
            _say("tour finished")
            return True
        text, effect, args = steps.pop(0)
        _say("%d/%d %s" % (len(TOUR) - len(steps), len(TOUR), text))
        try:
            effect(*args, which=which)
        except Exception as e:
            _say("  failed: %s" % e)

    step()
    _every(int(seconds * 1000), step)


def stop():
    """Ends a running tour or watch and turns the effects off."""
    while _timers:
        _timers.pop().stop()
    off()
