# CalculiX GraphiX (cgx)

CalculiX's own pre- and post-processor, with a GUI. Installed as
`/usr/bin/cgx`, version 2.21.

Worth stating plainly because it was missed once: **CalculiX is not GUI-less.**
A capability gap was recorded in this project for "results cannot be
visualised" while cgx was installed and named in the repository's own README.
Check what is on the machine before concluding something cannot be done.

## The manual

Ubuntu ships **no** cgx documentation. The man page points at a
`calculix-cgx-doc` package that does not exist in the archive; only
`calculix-cgx-examples` does, and `/usr/bin/cgx` is the entire binary payload.

The official manual is now in the repository, alongside the ccx one:

| | |
|---|---|
| Manual | `knowledge/calculix/CalculiX/cgx_2.23/doc/cgx/` (339 pages) |
| Index | `knowledge/calculix/cgx_command_index.txt` — 218 commands |
| Reader | `tools/cgxdoc.py <command>`, `tools/cgxdoc.py -l` |

Installed cgx is **2.21**, the manual is 2.23 — the same version spread as ccx.
Read the card before writing a command; the command language is dense,
positional, and nothing in it is guessable. That is G5 applied to cgx.

Worked examples are worth extracting too:
`apt-get download calculix-cgx-examples` (no root needed), then
`dpkg-deb -x`. The `pressfit`, `glue` and `turbine` cases show the real
`send` idiom.

## Invocation

| | |
|---|---|
| `cgx -v job.frd job.inp` | results, together with the sets and loads taken from the deck |
| `cgx -c job.inp` | read a solver input file |
| `cgx -b file.fbd` | run a command file |
| `cgx -bg file.fbd` | same, without graphic output |

The `-v` form is the useful one for verification: it puts the results and the
boundary conditions in the same view, so a load applied to the wrong face is
visible rather than inferred.

Driven by a command language; command files (`.fbd`) make it scriptable, and
`hcpy` writes an image.

## Controlled GUI fallback

No supported CGX socket or application API was found. The project therefore
does not label live keyboard control as native. `integrations.cgx.server`
binds one exact PID/window and reports interaction level `gui-fallback`.
Each GUI command requires an exclusive write lease and records before/after
window captures, console output available to the owned process, process
survival, and an acknowledgement grade.

Attaching an already running CGX process cannot recover its parent-terminal
output, so acknowledgement may be `visual-only` or `uncertain`. That is a
real limitation, not success. A person must receive the lease before using the
same window and the agent must observe again after control returns.

A working post-processing script, run as `cgx -b post.fbd` with `DISPLAY`
set:

```
read job.frd
ds 1 e 1        # dataset 1 (DISP), entity 1 (Ux); ds 2 e 7 for von Mises
scal d 400      # displacement scale factor
view elem
rot y
rot u 20
rot r 20
frame
hcpy png        # writes hcpy_1.png into the working directory
quit
```

`rot -y` puts +Z downwards; `rot y` is the one that comes out upright.

## Reading a deck as a pre-processor

`read job.inp` inside an `.fbd` (or `cgx -c job.inp`) parses the solver deck and
**builds sets for the boundary conditions automatically**, which is what makes
it a verification tool rather than just a viewer:

| Set | Contents |
|---|---|
| `all` | everything; also reports the face count |
| the deck's own `*NSET` / `*ELSET` | e.g. `BoltFix`, `Evolumes`, `MatSteelSolid` |
| `+bou`, `+bou1`, `+bou2`, `+bou3` | constrained nodes, and one set per constrained dof |
| `+clo`, `+clo1` | nodes carrying a `*CLOAD` |
| `+C3D10` | one set per element type present |

So the loaded and constrained node sets are available for plotting even when
the writer never named them — the `*CLOAD` block in a FreeCAD deck is written
node by node with no set, and `+clo` still appears. `prnt se` lists everything.

Useful for close-ups: `comp <set> up` grows a node set to the elements using
those nodes, `comp <set> do` back down to their nodes and faces, and `frame`
fits the view to whatever is currently plotted. Plot a subset and it frames
itself.

Statements it does not know (`*PHYSICAL CONSTANTS`, `*NODE FILE`, `*EL FILE`,
`*OUTPUT`) are reported as ignored and do not stop the read.

**`hcpy` numbering restarts at 1 on every invocation.** A second `cgx` run in
the same directory silently overwrites `hcpy_1.png` onwards. Rename the images
as soon as a run finishes; this cost two figures here before it was noticed.

`-b` needs `DISPLAY` set, because `hcpy` captures the window. `-bg` is fine for
text output such as `prnt se`, but produces no images.

## Building a deck properly: sets and surfaces

This is the part that matters, and it is what a hand-written CalculiX model
looks like. Loads and constraints are attached to **named sets and surfaces**,
not written out node by node. cgx selects by coordinate, so the selection is
stated in the language of the geometry and can be re-read months later.

```
read FemMesh.inp
seta nod n all                       # nodes only — see the enq remark below
enq nod TOPN rec _ _ 72. 0.01 a      # every node at z=72, '_' = any, 'a' = all
comp TOPN f                          # add the element faces those nodes fully describe
send TOPN abq nam                    # -> TOPN.nam       *NSET,NSET=NTOPN
send TOPN abq sur                    # -> TOPN.sur       *SURFACE,NAME=STOPN
send TOPN abq pres 3.978874          # -> TOPN.dlo       *DLOAD  "elem, P3, value"
send BoltFix abq spc 123             # -> BoltFix_123.bou  *BOUNDARY lines
send all abq                         # -> all.msh        *NODE / *ELEMENT
```

The main deck then holds only physics and `*INCLUDE` lines. Note the files
carry **data lines without their keyword** (`.bou` and `.dlo` do; `.nam` and
`.sur` bring their own card), so the deck supplies `*BOUNDARY` / `*DLOAD` above
the include.

| `send <set> abq …` | writes |
|---|---|
| `nam` / `names` | `*NSET` and `*ELSET` |
| `raw` | the same numbers with no set card |
| `sur` | `*SURFACE` as `element, S<n>` |
| `spc <dofs> [<value>]` | `*BOUNDARY`, optionally prescribed displacement |
| `pres <value>` \| `pres ds<n> e<n>` | `*DLOAD` pressure, uniform or from a dataset |
| `trac <v1> <v2> <v3>` | a traction vector — **ccx rejects it**, see below |
| `film` / `rad` / `dflux` | thermal surface loads |
| `<dep> <indep> abq areampc <dofs> c` | MPC equations between two sets |
| `cycmpc` | cyclic symmetry equations |

**Why this is not cosmetics.** On the bracket, selecting the loaded annulus by
coordinate found **224 element faces / 512 nodes**; FreeCAD's own writer had
found 200 faces / 486 nodes and silently dropped the rest (GAPS.md G2). A 1 MPa
pressure on the cgx surface produced a reaction of **1256.619 N** against an
analytic area of 1256.637 mm² — 14 ppm. FreeCAD's node-by-node route was 11.8 %
short. Same mesh, same solver; the difference is entirely in how the load
surface was defined.

Traps met while doing it:

- **`enq` picks up geometry, not just nodes.** Build a node-only set first
  (`seta nod n all`), as the manual's own remark says.
- **`sur` only sees free surfaces.** Internal faces cannot be identified, so a
  surface inside the mesh cannot be built this way.
- **`comp <set> f`** is the step that turns a node selection into element
  faces; without it `send … sur` has nothing to write.
- Set names come back prefixed — `TOPN` becomes `NTOPN` as an `*NSET` and
  `STOPN` as a `*SURFACE`. Use those names in the deck, not the cgx name.

## Where it will mislead you, and what it cannot do

**CAD import is not a route into this program.** `-step` reads, in the usage
text's own words, "only points and lines", and every `SURFACE_CURVE` in the
file is refused (269 of 269 in the manual's own `halter.stp`). Worse, it is
**not automatable at all**: `read <file> stp` inside an `.fbd` answers
`ERROR, no matching file-type found`, and piping commands into
`cgx -step file.stp` does not work either — the process sits in the GUI event
loop and executes neither `prnt se` nor `send all fbd`. STEP therefore reaches
cgx only with a human at the window, which also means the imported entity
counts cannot be read back in a script. The converters the manual and the examples
assume — `cad2fbd`, `vda2fbd` — are **not packaged**; Ubuntu's calculix-cgx
installs the binary and nothing else. Source for them exists upstream as
`cgxCadTools.tar.bz2` and would have to be built.

So the practical geometry paths are: build it in cgx's own language, or bring a
mesh in (`-c`, `-ng`, `-tg`, `-stl`, `-v`). Solid CAD comes in through
FreeCAD/Gmsh, not through cgx.

**`send … abq trac` writes a card CalculiX will not read.** It emits

```
38643, TRVEC3, 3.978874e+00, 1.000000e+00, 0.000000e+00, 0.000000e+00
```

and ccx 2.21 answers `*ERROR reading *DLOAD` and stops. `TRVEC` appears nowhere
in the ccx 2.23 manual. This matters because traction is the obvious way to
apply a **tangential** distributed load, and `pres` cannot do it — pressure is
normal to the face by definition. At least it fails loudly.

The consequence for the bracket: a 5000 N radial load on the boss cannot be
applied as a surface load through either tool. Pressure is the wrong direction,
traction is unreadable, and FreeCAD's nodal route loses 11.8 %. What remains is
to compute the consistent nodal forces and write the `*CLOAD` block directly —
which is exactly the case for treating the deck, not the pre-processor, as the
artifact.

**Meshing needs external meshers.** `asgn netgen` / tetgen are what the manual's
`cad` example uses; `ng_vol` and `tetgen` are not installed here (`netgen`
itself is). The example README also warns that tetgen "generates some elements
with negative jacobian" — the same failure as G3, from a different direction.

## Where it fits

Two independent routes into the same model, which is what makes it valuable:

- as a **post-processor**, it reads the `.frd` FreeCAD also reads, so a
  disagreement between them is informative;
- as a **pre-processor**, it can build meshes and sets and write a deck without
  FreeCAD involved at all, which matters wherever the FreeCAD writer has a gap
  (bolt pre-tension, for one).
