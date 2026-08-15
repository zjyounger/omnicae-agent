# FreeCAD FEM

This directory holds the official FreeCAD Linux AppImage. FreeCAD 1.1.3 x86_64
is installed here, verified against the official SHA-256:

```text
3a853eb69ee595f779f2255dbf80a765926981d8ff68903cefee4dfb03a8f5ef
```

The AppImage bundles CalculiX 2.23 and Gmsh 4.15.0; the system also keeps
independently callable CalculiX 2.21, CGX 2.21, and Gmsh 4.12.1.

Launch:

```bash
./FreeCAD_1.1.3-Linux-x86_64-py311.AppImage
```

Once installed it can also be run directly:

```bash
freecad
```

Inside FreeCAD, select **FEM** from the workbench dropdown. The AppImage's
bundled CalculiX and Gmsh are used by default; the system-level command paths
are `/usr/bin/ccx`, `/usr/bin/cgx`, and `/usr/bin/gmsh` respectively.

Headless verification:

```bash
freecad freecadcmd --version
```

Source: <https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.3>
