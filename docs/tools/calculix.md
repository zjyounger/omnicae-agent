# CalculiX (ccx)

Solver. `ccx 2.21` from the distribution; FreeCAD bundles 2.23 and that is the
one actually used through the FEM workbench. Interface is a keyword deck, not
an API.

## Documentation

The distribution package ships **no manual at all** — only a changelog and a
copyright file. The official manual is at `knowledge/calculix/`, taken as the
2.23 HTML edition because it matches the bundled solver and because HTML is
searchable. 534 pages; the 143 keyword cards are indexed in
`knowledge/calculix/keyword_index.txt`.

**Read the card. Do not write keywords from memory.** They are low-frequency,
they differ between versions, and a wrong one often fails silently rather than
erroring. Two examples of details that recall would have got wrong:

- `*PRE-TENSION SECTION` accepts an `ELEMENT` parameter, so a single linear B31
  beam element can represent a whole bolt. This makes an idealised bolt far
  cheaper than modelling the solid.
- The same card forbids a pre-tension surface adjacent to quadratic elements
  whose faces belong to a contact surface. Violating it does not raise an
  error; it produces spurious stress concentrations.

## Reading a deck

Comments start with `**`, which also matches a naive test for `*`. A parser
that checks `startswith("*")` before checking for comments will silently drop
whole sections.

`tools/inspect_deck.py` reports where every node set, load, and boundary
condition actually landed — node counts and coordinate extents — plus the load
resultant. Read the deck, not the CAD model: a constraint attached to nothing
looks exactly like one that worked.

## Reading results

`.frd` is fixed-width. Element definitions also begin with ` -1`, so a parser
keyed only on that prefix will read them as nodes. Node coordinates are easier
to take from the `.inp`, which uses the same numbering.

`tools/inspect_frd.py` reports the extremes **and their locations**, flagging
any peak that sits on a constrained node.

`.dat` holds whatever `*NODE PRINT` / `*EL PRINT` requested; without those it is
effectively empty. `*NODE PRINT, NSET=..., TOTALS=ONLY` with `RF` gives reaction
totals for a set, which is the cheapest independent check on an applied load.

## Failure modes seen

`*ERROR in e_c3d: nonpositive jacobian`, exit code 201, `.frd` containing a mesh
but no results. Almost always distorted second-order elements. See
[gmsh.md](gmsh.md).
