"""FreeCAD command for turning controller navigation on and off (bind it to a shortcut or toolbar)."""

import FreeCADGui as Gui


class ToggleCommand:
    def GetResources(self):
        return {
            "MenuText": "Toggle DualSense navigation",
            "ToolTip": "Turn 3D view navigation with the game controller on or off "
            "(the controller's Options button does the same)",
        }

    def Activated(self):
        import dualsense_nav

        dualsense_nav.toggle()

    def IsActive(self):
        return True


def register():
    if "DualSenseNav_Toggle" not in Gui.listCommands():
        Gui.addCommand("DualSenseNav_Toggle", ToggleCommand())
