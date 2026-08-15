"""Headless installation check for the bundled FreeCAD FEM workbench."""

import os

import FreeCAD
import Fem  # noqa: F401
from femmesh import gmshtools  # noqa: F401
from femsolver.calculix import solver  # noqa: F401

prefix = os.environ["PREFIX"]
ccx = os.path.join(prefix, "bin", "ccx")
gmsh = os.path.join(prefix, "bin", "gmsh")

assert os.path.isfile(ccx), ccx
assert os.path.isfile(gmsh), gmsh

print("FreeCAD:", ".".join(FreeCAD.Version()[:3]))
print("FEM module: OK")
print("CalculiX adapter: OK")
print("Gmsh adapter: OK")
print("Bundled ccx:", ccx)
print("Bundled gmsh:", gmsh)
