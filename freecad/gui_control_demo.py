"""Open a visible FreeCAD FEM session to verify GUI control."""

import FreeCAD as App
import FreeCADGui as Gui

Gui.activateWorkbench("FemWorkbench")

doc = App.newDocument("Codex_GUI_Demo")
box = doc.addObject("Part::Box", "DemoSolid")
box.Label = "GUI control demo solid"
box.Length = 40
box.Width = 20
box.Height = 10
doc.recompute()

view = Gui.activeDocument().activeView()
view.viewAxonometric()
view.fitAll()

Gui.activeDocument().activeView().setAnimationEnabled(False)
Gui.updateGui()
