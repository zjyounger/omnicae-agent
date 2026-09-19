#!/usr/bin/env python3
"""Report where a CalculiX deck's sets, constraints, and loads actually land.

Reads the deck the solver was given, not the CAD model, so it catches a
constraint that silently attached to nothing.
"""

import math
import re
import sys


def parse(path):
    nodes, nsets, cload, boundary = {}, {}, [], []
    section = None
    with open(path) as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("**"):      # comment; must be tested before "*"
                continue
            if line.startswith("*"):
                upper = line.upper()
                if upper.startswith("*NODE") and not any(
                    w in upper for w in ("FILE", "PRINT", "OUTPUT")
                ):
                    section = ("nodes", None)
                elif upper.startswith("*NSET"):
                    name = re.search(r"NSET\s*=\s*([^,]+)", line, re.I).group(1).strip()
                    section = ("nset", name)
                    nsets.setdefault(name, [])
                elif upper.startswith("*CLOAD"):
                    section = ("cload", None)
                elif upper.startswith("*BOUNDARY"):
                    section = ("boundary", None)
                else:
                    section = None
                continue
            if not line or section is None:
                continue
            parts = [p.strip() for p in line.split(",")]
            kind = section[0]
            if kind == "nodes" and len(parts) == 4:
                nodes[int(parts[0])] = tuple(float(v) for v in parts[1:])
            elif kind == "nset":
                nsets[section[1]] += [int(p) for p in parts if p.isdigit()]
            elif kind == "cload" and len(parts) == 3:
                cload.append((parts[0], int(parts[1]), float(parts[2])))
            elif kind == "boundary" and len(parts) >= 2:
                boundary.append(parts)
    return nodes, nsets, cload, boundary


def resolve_nodes(target, nsets):
    """Resolve a CalculiX node number or node-set name into node IDs."""

    if target.isdigit():
        return [int(target)]
    return nsets.get(target, [])


def load_summary(nsets, cload):
    """Return loaded node IDs and the expanded force resultant."""

    ids = set()
    totals = {1: 0.0, 2: 0.0, 3: 0.0}
    unresolved = []
    for target, dof, value in cload:
        resolved = resolve_nodes(target, nsets)
        if not resolved:
            unresolved.append(target)
            continue
        ids.update(resolved)
        totals[dof] += value * len(resolved)
    return ids, totals, unresolved


def constrained_nodes(nsets, boundary):
    """Return only nodes named by *BOUNDARY cards, not every declared set."""

    ids = set()
    unresolved = []
    for row in boundary:
        resolved = resolve_nodes(row[0], nsets)
        if resolved:
            ids.update(resolved)
        else:
            unresolved.append(row[0])
    return ids, unresolved


def extent(nodes, ids, title):
    pts = [nodes[i] for i in ids if i in nodes]
    if not pts:
        print("  %-16s EMPTY  <-- attached to nothing" % title)
        return
    xs, ys, zs = zip(*pts)
    radii = [math.hypot(x, y) for x, y in zip(xs, ys)]
    print(
        "  %-16s n=%-5d x[%7.2f,%7.2f] y[%7.2f,%7.2f] z[%7.2f,%7.2f] r[%6.2f,%6.2f]"
        % (title, len(pts), min(xs), max(xs), min(ys), max(ys),
           min(zs), max(zs), min(radii), max(radii))
    )


def main(path):
    nodes, nsets, cload, boundary = parse(path)
    print("deck: %s" % path)
    print("nodes: %d\n" % len(nodes))

    print("node sets")
    for name in sorted(nsets):
        extent(nodes, nsets[name], name)

    print("\nconcentrated loads")
    ids, totals, unresolved = load_summary(nsets, cload)
    extent(nodes, sorted(ids), "CLOAD nodes")
    print("  resultant       Fx=%.3f  Fy=%.3f  Fz=%.3f" % (totals[1], totals[2], totals[3]))
    for target in unresolved:
        print("  unresolved      %s  <-- unknown node or set" % target)

    print("\nboundary conditions")
    for row in boundary[:10]:
        target = row[0]
        ids = resolve_nodes(target, nsets)
        first = row[1]
        last = row[2] if len(row) >= 3 and row[2] else first
        value = row[3] if len(row) >= 4 and row[3] else "0"
        dofs = first if first == last else "%s-%s" % (first, last)
        print("  %-16s dof %-5s value %-10s%s" % (
            target, dofs, value, "" if ids else "   <-- unknown node or set"
        ))


if __name__ == "__main__":
    main(sys.argv[1])
