# DualSense navigation for FreeCAD (macOS)

Use a PlayStation DualSense (or any controller macOS recognises: DualShock 4, Xbox, ...) to orbit, pan and
zoom FreeCAD's 3D view instead of a 3D mouse. It's a FreeCAD add-on with no workbench of its own: it runs in
the background whenever FreeCAD is open, in every workbench.

## Controls

| Control | Action |
|---|---|
| Left stick | Orbit. The model follows the stick: push right and the near side swings right. With something selected, it turns about the selection; otherwise about the centre of the view |
| Right stick | Pan (the model moves the way you push) |
| R2 / L2 | Zoom in / out, pressure-sensitive |
| R1 / L1 | Roll clockwise / counter-clockwise |
| Triangle | Fit all |
| D-pad | Up: Top view. Down: Front view. Right: Right view. Left: Isometric view |
| X (Cross) | Turn gyro rotation on/off (see below) |
| Options | Turn controller navigation on/off |

The light bar shows the mode: blue when navigation is on, purple when gyro rotation is on as well, and dim
amber when navigation is off.

The controller only moves the view while FreeCAD is the frontmost app. Sticks, triggers, L1/R1 and the gyro
can be used together.

### Gyro rotation

Tap X and the model turns the way you turn the controller, as if you were holding the model:

- **Turn the controller left or right** (keeping it level) and the model spins the same way around its vertical axis.
- **Tilt the far edge (light bar end) up or down** and the model's far side rises or drops.
- **Tilting like a steering wheel** does nothing by default, so the model stays upright. Set `GyroRoll` to true
  to roll the view with it.

The model turns 1.5x as far as the controller by default (`GyroSpeed`), so small wrist movements are enough.
Like the left stick, the gyro turns about the selected object if there is one. Tap X again to stop, and set the
model down before you pick the controller up. The gyro is off each time the controller connects, and turning
navigation off with Options also turns it off. The motion sensors only run while the gyro is on, to save battery.

## Install

```bash
./install.sh
```

Then quit and reopen FreeCAD. The Report view (View > Panels > Report view) shows
`DualSense navigation: using DualSense Wireless Controller` once the controller is picked up.

`install.sh` changes nothing inside `FreeCAD.app`. It:

1. installs Apple's GameController bindings (`pyobjc-framework-GameController`) with FreeCAD's own Python into
   `~/Library/Application Support/FreeCAD/v1-1/AdditionalPythonPackages/py311`, the same folder the Addon Manager uses
2. links `DualSenseNav/` into `~/Library/Application Support/FreeCAD/v1-1/Mod/`, so edits in this folder take
   effect the next time FreeCAD starts

## Settings

Open Tools > Edit parameters and go to `BaseApp > Preferences > Mod > DualSenseNav`. Changes take effect within 2 seconds.

| Parameter | Default | Meaning |
|---|---|---|
| `OrbitSpeed` | 120 | Degrees per second at full stick |
| `PanSpeed` | 0.8 | Screen heights per second at full stick |
| `ZoomSpeed` | 1.6 | Zoom rate; 1.6 is about 5x magnification per second at full trigger |
| `RollSpeed` | 90 | Degrees per second while L1/R1 is held |
| `Deadzone` | 0.12 | Stick travel ignored around centre (0–1); raise it if the view drifts |
| `Curve` | 2.0 | Response curve. 1 is linear; higher gives finer control for small stick movements |
| `InvertOrbitX`, `InvertOrbitY`, `InvertPanX`, `InvertPanY` | false | Reverse an axis. Inverting both orbit axes makes the left stick move the camera instead of the model |
| `GyroSpeed` | 1.5 | How many times as far the model turns as the controller |
| `GyroDeadzone` | 2.0 | Controller turn rate ignored, in degrees per second; raise it if the model creeps while you hold still |
| `GyroRoll` | false | Also roll the view when you tilt the controller like a steering wheel |
| `InvertGyroYaw`, `InvertGyroPitch` | false | Reverse the gyro's turn or tilt direction |
| `OrbitAroundSelection` | true | Turn about the selected object instead of the centre of the view |
| `LightBar` | true | Set the light bar colour to show the mode |
| `Enabled` | true | Same as the Options button |

To toggle navigation from the keyboard, assign a shortcut to **Toggle DualSense navigation** in
Tools > Customize > Keyboard.

## Troubleshooting

- **Nothing happens.** The DualSense goes to sleep after a while. Press the PS button to reconnect it; FreeCAD
  picks it up within a second. Check that it's listed as connected in System Settings > Bluetooth.
- **The PS button opens something in macOS.** That button belongs to macOS and isn't used by the add-on.
- **The Report view says "DualSense navigation did not start".** Run `./install.sh` again; the GameController bindings are missing.

## Tests

```bash
tests/run_tests.sh
```

This opens FreeCAD with a temporary profile (your settings and add-ons aren't touched). It drives the add-on with
a simulated controller, checks how the model moves on screen, prints PASS/FAIL lines and closes FreeCAD. A
FreeCAD window appears briefly while it runs.

## Uninstall

```bash
rm "$HOME/Library/Application Support/FreeCAD/v1-1/Mod/DualSenseNav"
```

This removes the add-on link. The GameController bindings stay in `AdditionalPythonPackages/py311` (the
`objc`, `Foundation`, `AppKit`, `Cocoa`, `CoreFoundation`, `GameController`, `PyObjCTools` and `PyObjCTest` folders
and their `pyobjc_*` entries). Delete those too if no other add-on uses them.
