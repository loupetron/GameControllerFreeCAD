#!/bin/zsh
# Installs the DualSense navigation add-on into FreeCAD on macOS:
#  1. Apple's GameController bindings (PyObjC) into FreeCAD's per-user Python package folder
#  2. a link to DualSenseNav in FreeCAD's per-user Mod folder
# Nothing inside FreeCAD.app is changed. Set FREECAD_APP to use a FreeCAD other than /Applications/FreeCAD.app.
set -eu

here=${0:A:h}
freecad=${FREECAD_APP:-/Applications/FreeCAD.app}
bin=$freecad/Contents/Resources/bin

userdata=$("$bin/freecadcmd" -c "import FreeCAD; print('USERDATA=' + FreeCAD.getUserAppDataDir())" | sed -n 's/^USERDATA=//p')
userdata=${userdata%/}
pyver=$("$bin/python" -c 'import sys; print("py%d%d" % sys.version_info[:2])')
packages="$userdata/AdditionalPythonPackages/$pyver"
mods="$userdata/Mod"

echo "Installing GameController bindings into: $packages"
"$bin/python" -m pip install --quiet --disable-pip-version-check --upgrade --target "$packages" pyobjc-framework-GameController

echo "Linking add-on into: $mods/DualSenseNav"
mkdir -p "$mods"
ln -sfn "$here/DualSenseNav" "$mods/DualSenseNav"

echo "Done. Restart FreeCAD, connect the controller and press Options to turn navigation on or off."
