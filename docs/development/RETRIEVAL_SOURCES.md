# Retrieval source survey

This note records which public application sources are suitable for retrieval
experiments after CalculiX. A source being well documented does not by itself
justify adding an application integration.

## Selection criteria

A useful source is official, versionable, searchable, licensed or fetchable,
and contains enough reference material and examples to verify a retrieved API
or command against its complete context.

## Meshing

### Gmsh — next source

The installed Gmsh 4.12.1 package already has matching `gmsh-doc` material:

- one 2.3 MB HTML reference manual and a PDF copy;
- command-line, `.geo` language, option, and multi-language API references;
- 85 Python API examples and 85 `.geo` examples;
- tutorial images and additional C, C++, Julia, and Fortran examples.

This is complete enough for API, script, ordinary-text, code, and image
retrieval tests without downloading a different version. The local 4.12.1
manual should be evaluated before the current online 4.15 series so retrieved
answers match the executable.

## CAD

### FreeCAD — broad but version-sensitive

The official `FreeCAD-documentation` repository currently contains roughly
21,800 Markdown pages and 9,000 images and declares CC0-1.0. It covers user
workflows, workbenches, scripting, and many API topics. The separate online
Doxygen source documentation identifies itself as built from a 2022 docs
branch, so it must not be treated as authoritative for the local 1.1.3
AppImage.

Ingestion should begin with a versioned subset for Python scripting, core
objects, Part, Mesh, and FEM. Live capability and property discovery through
the Bridge remains authoritative when documentation and the running object
differ.

### CadQuery — compact and well structured

CadQuery's source repository contains a compact Sphinx corpus: API and class
references, a primer, workplane and selector documentation, import/export,
assemblies, examples, and about 40 supporting images. The project declares the
Apache-2.0 licence.

Its documentation is suitable for retrieval, but it should enter the corpus
only when CadQuery becomes an actual application integration; otherwise the
agent could retrieve an API it cannot operate.

## Post-processing

### PyVista — first programmatic experiment

PyVista is an MIT-licensed Python interface over VTK with a versioned user
guide, API reference, examples, readers, filters, and plotting documentation.
Version 0.48 adds a native ASCII CalculiX `FRDReader` with time-step support,
common CalculiX element types, stress/strain tensors, von Mises values, and
principal values. Its upstream tests cover FRD parsing, invalid elements,
time steps, derived stress/strain, and element ordering.

The first experiment should load an existing repository `.frd`, compare its
arrays and extremes against `tools/inspect_frd.py`, and render a deterministic
off-screen image. PyVista is not currently installed.

### ParaView — human-facing general application

ParaView is a BSD-3-Clause desktop and distributed visualization application.
It has a complete user guide, reference manual, Python API, `pvpython`, and
`pvbatch`. It is the strongest candidate for interactive general multiphysics
post-processing and already has native readers for formats such as OpenFOAM.

For CalculiX, the clean initial path is:

```text
FRD → PyVista reader → VTK/VTU → ParaView
```

This keeps the tested FRD reader in project-controlled Python while ParaView
provides the GUI and broader visualization pipeline. ParaView is not currently
installed.

### Existing fallback

CalculiX GraphiX remains the small solver-specific viewer already available in
the project. It is useful for direct inspection and screenshots, but it is not
the preferred general multiphysics post-processing interface.

## Proposed order

1. Gmsh 4.12.1 local documentation retrieval tests.
2. A targeted FreeCAD 1.1.x documentation subset.
3. PyVista against the existing CalculiX FRD cases.
4. ParaView only after the programmatic result contract is clear.
5. CadQuery when an integration is scheduled.
