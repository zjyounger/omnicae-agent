#!/usr/bin/env python3
"""Check whether a *CLOAD block covers the whole surface it was meant to load.

FreeCAD distributes a face force by area-weighting the mesh faces that lie on
the reference face. A mesh face whose node count is not 3, 4, 6 or 8 falls
through every branch of the weighting code and contributes nothing, so its
share of the load is dropped without a word. See GAPS.md G2.

This reads the deck alone. It reconstructs the element faces sitting on the
loaded node set and reports the ones that were skipped, so the shortfall can be
attributed before any result is believed.
"""

import math
import sys

# CalculiX C3D10 faces: corner nodes then mid-side nodes, 1-based within the element
C3D10_FACES = [((1, 2, 3), (5, 6, 7)), ((1, 4, 2), (8, 9, 5)),
               ((2, 4, 3), (9, 10, 6)), ((3, 4, 1), (10, 8, 7))]


def parse(path):
    nodes, elements, cload = {}, {}, []
    section = None
    for raw in open(path):
        line = raw.strip()
        if line.startswith("**"):
            continue
        if line.startswith("*"):
            upper = line.upper().replace(" ", "")
            if upper.startswith("*NODE") and not any(
                w in upper for w in ("FILE", "PRINT", "OUTPUT")
            ):
                section = "nodes"
            elif upper.startswith("*ELEMENT") and "C3D10" in upper:
                section = "elements"
            elif upper.startswith("*CLOAD"):
                section = "cload"
            else:
                section = None
            continue
        if not line or section is None:
            continue
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if section == "nodes" and len(parts) == 4:
            nodes[int(parts[0])] = tuple(float(v) for v in parts[1:])
        elif section == "elements" and len(parts) == 11:
            elements[int(parts[0])] = [int(p) for p in parts[1:]]
        elif section == "cload" and len(parts) == 3:
            cload.append((int(parts[0]), int(parts[1]), float(parts[2])))
    return nodes, elements, cload


def area(nodes, a, b, c):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = nodes[a], nodes[b], nodes[c]
    u = (bx - ax, by - ay, bz - az)
    v = (cx - ax, cy - ay, cz - az)
    return 0.5 * math.hypot(u[1] * v[2] - u[2] * v[1],
                            u[2] * v[0] - u[0] * v[2],
                            u[0] * v[1] - u[1] * v[0])


def main(path, intended=None):
    nodes, elements, cload = parse(path)
    loaded = {n for n, _, _ in cload}
    if not loaded:
        print("no *CLOAD nodes in this deck")
        return
    print("deck:          %s" % path)
    print("loaded nodes:  %d" % len(loaded))

    resultant = {1: 0.0, 2: 0.0, 3: 0.0}
    for node, dof, value in cload:
        resultant[dof] += value
    total = math.sqrt(sum(v * v for v in resultant.values()))
    print("resultant:     Fx=%.4f Fy=%.4f Fz=%.4f  |F|=%.4f"
          % (resultant[1], resultant[2], resultant[3], total))

    # free surface faces: a corner triple used by exactly one element
    seen = {}
    for eid, nn in elements.items():
        for fno, (corners, _) in enumerate(C3D10_FACES, 1):
            seen.setdefault(frozenset(nn[i - 1] for i in corners), []).append((eid, fno))
    free = [v[0] for v in seen.values() if len(v) == 1]

    counted, skipped = 0.0, []
    faces = 0
    for eid, fno in free:
        nn = elements[eid]
        corners, mids = C3D10_FACES[fno - 1]
        face = [nn[i - 1] for i in corners] + [nn[i - 1] for i in mids]
        if not all(n in loaded for n in face[:3]):
            continue                      # not part of the loaded surface
        a = area(nodes, face[0], face[1], face[2])
        if all(n in loaded for n in face):
            faces += 1
            counted += a
        else:
            absent = [n for n in face if n not in loaded]
            skipped.append((absent[0], a))

    print("\nelement faces on the loaded surface")
    print("  weighted:    %-5d  area %10.4f mm2" % (faces, counted))
    if not skipped:
        print("  skipped:     none")
        print("\nthe whole loaded surface was weighted.")
    else:
        lost = sum(a for _, a in skipped)
        print("  skipped:     %-5d  area %10.4f mm2   <-- a mid-side node is missing"
              % (len(skipped), lost))
        share = lost / (counted + lost)
        print("\n%d faces were dropped, %.4f mm2, %.2f%% of the surface."
              % (len(skipped), lost, 100 * share))
        print("this is a LOWER BOUND: a face whose corner node is also missing")
        print("from the load set cannot be seen from the deck alone. GAPS.md G2.")
        radii = sorted({round(math.hypot(nodes[n][0], nodes[n][1]), 6)
                        for n, _ in skipped})
        print("absent nodes lie at radius %s"
              % ", ".join("%.6f" % r for r in radii[:6]))
        if intended:
            print("\nintended %.4f N, deck %.4f N, ratio %.5f"
                  % (intended, total, total / intended))
            print("expected ratio from the dropped faces alone: %.5f" % (1 - share))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
