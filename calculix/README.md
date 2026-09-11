# CalculiX: an open-source alternative to Abaqus

Generated CAD, meshes, results and evidence files referenced here are local,
Git-ignored artifacts. They are not included in a fresh clone; regenerate them
where a procedure is provided, or obtain the preserved local case archive.
Source scripts, authored inputs and this document remain versioned.

The Ubuntu 24.04 repository version is installed on this machine:

- `calculix-ccx` 2.21: finite element solver (`ccx` command)
- `calculix-cgx` 2.21: pre- and post-processor (`cgx` command)

CalculiX uses a keyword input file (`.inp`) close to Abaqus/Standard's. The two
are not fully compatible; complex contact, material models, user subroutines,
and output keywords need checking item by item.

## Running the verification example

Despite its legacy filename, `cantilever.inp` is a one-element uniaxial patch
test, not a bending cantilever. Its analytical reference, observed deviations,
and applicability limits are recorded in
[`../cases/calculix_axial_patch/DEFINITION.md`](../cases/calculix_axial_patch/DEFINITION.md).

From this directory:

```bash
ccx cantilever
```

On success this produces:

- `cantilever.dat`: text results
- `cantilever.frd`: field results, read by CGX
- `cantilever.sta`: increment status

View the results:

```bash
cgx cantilever.frd
```

`cgx` is a graphical program and needs a desktop session with a working X/Wayland display.

## Common commands

```bash
# solve job.inp (no extension in the command)
ccx job

# open a mesh or a result file
cgx job.inp
cgx job.frd

# check the version
ccx -v
```

## Updating or reinstalling

```bash
sudo apt update
sudo apt install calculix-ccx calculix-cgx
```
