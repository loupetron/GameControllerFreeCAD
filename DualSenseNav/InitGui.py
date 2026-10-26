# FreeCAD runs this file when its GUI starts. The add-on has no workbench:
# it starts reading the controller in the background once the window is up.


def _start_dualsense_nav():
    import FreeCAD

    try:
        import dualsense_nav

        dualsense_nav.commands.register()
        dualsense_nav.start()
    except Exception as e:
        FreeCAD.Console.PrintWarning("DualSense navigation did not start: %s\n" % e)


from PySide import QtCore

QtCore.QTimer.singleShot(0, _start_dualsense_nav)
