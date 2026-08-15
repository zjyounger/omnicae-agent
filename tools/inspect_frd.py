#!/usr/bin/env python3
"""Report result extremes and, crucially, where they are.

A peak stress sitting on a constrained node is usually an artefact of the
boundary condition, not a structural result, so the location matters as much
as the value.
"""

import math
import os
import sys


def parse(path):
    coords, stress, disp = {}, {}, {}
    block = None
    for raw in open(path, errors="ignore"):
        line = raw.rstrip("\n")
        tag = line[:5].strip()
        if line.strip().startswith("-4"):
            name = line.split()[1]
            block = "S" if name == "STRESS" else ("D" if name == "DISP" else None)
            continue
        if tag == "2C":
            block = "N"
            continue
        if tag in ("-3", "9999") or line.strip() == "-3":
            if block == "N":
                block = None
            continue
        if not line.startswith(" -1") or block not in ("N", "S", "D"):
            # Element definitions also start with " -1"; only read inside a
            # block we recognise.
            continue
        parts = line[3:]
        node = int(parts[:10])
        vals = []
        for i in range((len(parts) - 10) // 12):
            field = parts[10 + 12 * i: 22 + 12 * i]
            try:
                vals.append(float(field))
            except ValueError:
                vals = []
                break
        if not vals:
            continue
        if block == "N" and len(vals) >= 3:
            coords[node] = tuple(vals[:3])
        elif block == "S" and len(vals) >= 6:
            stress[node] = vals[:6]
        elif block == "D" and len(vals) >= 3:
            disp[node] = vals[:3]
    return coords, stress, disp


def von_mises(s):
    xx, yy, zz, xy, yz, zx = s
    return math.sqrt(
        0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2)
        + 3.0 * (xy * xy + yz * yz + zx * zx)
    )


def main(frd, deck=None):
    _, stress, disp = parse(frd)
    # Coordinates and node sets come from the deck: same numbering, and it is
    # the file that also says which nodes are constrained.
    deck = deck or frd[:-4] + ".inp"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from inspect_deck import parse as parse_deck

    coords, nsets, _cload, _bc = parse_deck(deck)
    constrained = {n for ids in nsets.values() for n in ids}
    print("frd: %s\nnodes %d | stress %d | disp %d\n" % (frd, len(coords), len(stress), len(disp)))
    if not stress:
        print("no stress results in file")
        return

    vm = {n: von_mises(s) for n, s in stress.items()}
    top = sorted(vm, key=vm.get, reverse=True)[:8]
    print("highest von Mises")
    for n in top:
        x, y, z = coords.get(n, (float("nan"),) * 3)
        flag = "  <-- ON A CONSTRAINED NODE" if n in constrained else ""
        print("  node %-7d %8.2f MPa   at (%7.2f, %7.2f, %7.2f)  r=%6.2f%s"
              % (n, vm[n], x, y, z, math.hypot(x, y), flag))

    if disp:
        mag = {n: math.sqrt(sum(v * v for v in d)) for n, d in disp.items()}
        n = max(mag, key=mag.get)
        x, y, z = coords.get(n, (float("nan"),) * 3)
        print("\nlargest displacement")
        print("  node %-7d %8.5f mm    at (%7.2f, %7.2f, %7.2f)" % (n, mag[n], x, y, z))


if __name__ == "__main__":
    main(*sys.argv[1:3])
