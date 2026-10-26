#!/bin/zsh
# Opens FreeCAD with a throwaway profile (your own settings and add-ons are not touched),
# runs test_in_freecad.py with a simulated controller, prints the results and closes FreeCAD.
set -u

here=${0:A:h}
freecad=${FREECAD_APP:-/Applications/FreeCAD.app}
bin=$freecad/Contents/Resources/bin

userdata=$("$bin/freecadcmd" -c "import FreeCAD; print('USERDATA=' + FreeCAD.getUserAppDataDir())" | sed -n 's/^USERDATA=//p')
userdata=${userdata%/}
pyver=$("$bin/python" -c 'import sys; print("py%d%d" % sys.version_info[:2])')

profile=$(mktemp -d)
trap 'rm -rf "$profile"' EXIT
export FREECAD_USER_HOME=$profile
export DSN_TEST_OUT=$profile/results.txt
export DSN_ADDON_DIR=$here/../DualSenseNav
export DSN_PACKAGES=$userdata/AdditionalPythonPackages/$pyver

"$freecad/Contents/MacOS/FreeCAD" "$here/test_in_freecad.py" >"$profile/freecad.log" 2>&1

if [[ ! -s $DSN_TEST_OUT ]]; then
  echo "No results; FreeCAD output:"
  tail -30 "$profile/freecad.log"
  exit 1
fi
cat "$DSN_TEST_OUT"
! grep -q '^FAIL' "$DSN_TEST_OUT"
