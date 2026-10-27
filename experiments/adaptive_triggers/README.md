# Can the triggers push back? (DualSense adaptive triggers)

This branch is for finding out whether DualSense navigation can use the DualSense's adaptive triggers: motors in
L2 and R2 that add resistance, a click or a buzz to the pull. Nothing here changes the add-on yet. The probe in
this folder sets the effects from FreeCAD's Python console, so they can be tried out while zooming.

## What we know already

Checked against `pyobjc-framework-GameController` 12.2.2 (what `install.sh` installs today) and the macOS
GameController headers it was built from:

- On a DualSense, `extendedGamepad()` is a `GCDualSenseGamepad`, and its `leftTrigger()` and `rightTrigger()` are
  `GCDualSenseAdaptiveTrigger` objects. These are the same objects `Gamepad.read()` already reads `value()` from, so
  an effect is one call on a trigger the add-on already holds. No new connection or library is needed.
- The bindings include every effect, and the structs that the zoned effects take:

| Effect | Call on the trigger | Feels like | macOS |
|---|---|---|---|
| Off | `setModeOff()` | A plain trigger | 11.3 |
| Feedback | `setModeFeedbackWithStartPosition_resistiveStrength_(start, strength)` | Steady resistance from `start` to the end of the pull | 11.3 |
| Weapon | `setModeWeaponWithStartPosition_endPosition_resistiveStrength_(start, end, strength)` | Resistance between `start` and `end` that gives way with a click | 11.3 |
| Vibration | `setModeVibrationWithStartPosition_amplitude_frequency_(start, amplitude, frequency)` | A buzz once pulled past `start` | 11.3 |
| Slope feedback | `setModeSlopeFeedbackWithStartPosition_endPosition_startStrength_endStrength_(...)` | Resistance that ramps between two strengths | 12.3 |
| Zoned feedback | `setModeFeedbackWithResistiveStrengths_(strengths)` | A separate strength for each tenth of the pull | 12.3 |
| Zoned vibration | `setModeVibrationWithAmplitudes_frequency_(amplitudes, frequency)` | A separate buzz for each tenth of the pull | 12.3 |

All values run from 0 to 1. The trigger also reports back its `mode()`, its `status()` (such as "weapon fired"
or "feedback, load applied") and `armPosition()`, where the motor arm sits. The macOS versions come from Apple's
documentation; `tp.report()` shows what your Mac actually offers.

Xbox controllers have rumble motors in their triggers ("impulse triggers") instead. Those go through a different
API: `GCController.haptics()` with the `LeftTrigger`/`RightTrigger` localities, driven by Core Haptics, which is a
separate PyObjC package. They're out of scope here; `tp.report()` lists the haptic localities a controller has.

## What we need to find out on the controller

Fill in the result column as you go.

| # | Question | How to check | Result |
|---|---|---|---|
| 1 | Do effects work from inside FreeCAD over Bluetooth? Over USB? | `tp.feedback(0.0, 1.0)` and pull | |
| 2 | Does the trigger report back? Do `mode()` and `status()` change when an effect is set, and does `status()` show "weapon fired" after a click? | `tp.weapon(0.3, 0.6, 0.8)`, then `tp.watch()` and pull through the click | |
| 3 | Does an effect change the `value()` that zoom reads? Can you still reach 1.0, and does the value jitter? | `tp.watch()` with and without `tp.feedback(0.0, 1.0)` | |
| 4 | What happens to an effect when FreeCAD isn't the frontmost app, when the controller sleeps and reconnects, and when FreeCAD quits? A trigger left stiff after quitting would be a problem. | Set an effect, switch to another app, disconnect the controller in System Settings > Bluetooth and reconnect it, then quit FreeCAD | |
| 5 | Which effects make zooming easier, and which get in the way? | `tp.tour()` with a model open, pulling R2 at each stop | |
| 6 | Does a constant effect drain the battery noticeably? | Leave `tp.feedback(0.0, 0.3)` on for a session and compare | |
| 7 | Do the zoned effects (12.3) accept the 10 values from Python? | `tp.zones([0, 0, 0, 0.3, 0.3, 0.3, 0.6, 0.6, 0.6, 0.9])` | |

## Run the probe

1. Install the add-on as usual (`./install.sh`), connect the DualSense and open FreeCAD.
2. Open **View > Panels > Report view** and **View > Panels > Python console**. The probe writes to the Report view.
3. In the Python console, with the path to this folder:

   ```python
   import sys; sys.path.insert(0, "/path/to/GameControllerFreeCAD/experiments/adaptive_triggers")
   import trigger_probe as tp
   tp.report()
   ```

| Command | What it does |
|---|---|
| `tp.report()` | Controller, gamepad profile, macOS version, which effects this Mac supports, and each trigger's current state |
| `tp.tour()` | Sets each effect on R2 for 6 seconds, then turns it off. `tp.tour(10, "both")` uses 10 seconds and both triggers |
| `tp.feedback(start, strength)` | Steady resistance from `start` |
| `tp.weapon(start, end, strength)` | A click between `start` and `end` |
| `tp.vibration(start, amplitude, frequency)` | A buzz past `start` |
| `tp.slope(start, end, start_strength, end_strength)` | Resistance that ramps |
| `tp.zones([10 strengths])`, `tp.vibration_zones([10 amplitudes], frequency)` | One value for each tenth of the pull |
| `tp.watch(seconds=10)` | Logs each trigger's pull, arm position, mode and status as they change |
| `tp.off()` | Plain triggers again |
| `tp.stop()` | Ends a tour or watch and turns the effects off |

Every effect takes `which="l2"`, `"r2"` or `"both"` (the default). With a document open the triggers still zoom
while you try them, which is the point. Press Options to turn navigation off if you only want to feel the effect.

## Ideas to judge during the tour

- **Light resistance over the whole pull**, so a slow zoom is easier to hold steady.
- **A wall halfway down**, marking the change from slow to fast zoom.
- **Resistance that grows with the pull**, matching the zoom's response curve (`Curve`).
- **A click at the end of the pull** as a detent for a discrete action, such as zooming to the selection.
- **A buzz** when zoom reaches full speed, or a short one when gyro rotation turns on or off, so the mode can be
  felt without looking at the light bar.
- **A different feel while gyro rotation is on**, like the light bar's change to purple.

## If the answer is yes

A sketch of the next step, for a later branch:

- `Gamepad.set_trigger_effect(...)`, next to `set_light`, that does nothing on controllers without adaptive
  triggers. `FakeGamepad` in the tests gets the same method, so the tests can check which effect is set when.
- A setting (for example `TriggerFeedback`) to turn it off, and the effects reset whenever navigation turns off,
  the controller disconnects or FreeCAD quits, the same way the light bar follows the mode.
