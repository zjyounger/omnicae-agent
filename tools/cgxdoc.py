#!/usr/bin/env python3
"""Print the cgx manual entry for a command, as text.

The installed cgx ships no manual (Ubuntu has no calculix-cgx-doc package).
The official 2.23 HTML manual lives in knowledge/calculix/CalculiX/cgx_2.23/,
indexed by knowledge/calculix/cgx_command_index.txt.

    tools/cgxdoc.py send        one command
    tools/cgxdoc.py -l          list every command
"""

import html
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "knowledge", "calculix")
INDEX = os.path.join(ROOT, "cgx_command_index.txt")


def entries():
    out = []
    for line in open(INDEX):
        if line.startswith("#") or not line.strip():
            continue
        name, path = line.rsplit(None, 1)
        out.append((name.strip(), os.path.join(ROOT, path.strip())))
    return out


def text_of(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    body = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    body = re.sub(r"(?is)<div class=\"navigation\".*?</div>", "", body)
    body = re.sub(r"(?i)<br\s*/?>", "\n", body)
    body = re.sub(r"(?i)</(p|div|tr|h\d|pre|li)>", "\n", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = html.unescape(body)
    lines = [l.rstrip() for l in body.splitlines()]
    keep, blank = [], 0
    for l in lines:
        if not l.strip():
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        if l.strip() in ("Next:", "Up:", "Previous:", "Contents"):
            continue
        keep.append(l)
    return "\n".join(keep).strip()


def main(argv):
    if not argv or argv[0] in ("-l", "--list"):
        names = [n for n, _ in entries()]
        for i in range(0, len(names), 8):
            print("  ".join("%-12s" % n for n in names[i:i + 8]))
        print("\n%d commands" % len(names))
        return
    wanted = argv[0].lower()
    hits = [(n, p) for n, p in entries() if n.lower() == wanted]
    if not hits:
        hits = [(n, p) for n, p in entries() if wanted in n.lower()]
    if not hits:
        print("no such command: %s   (try -l)" % wanted)
        return
    for name, path in hits:
        print("=" * 70)
        print("%s   [%s]" % (name, os.path.relpath(path, os.path.join(ROOT, ".."))))
        print("=" * 70)
        print(text_of(path))


if __name__ == "__main__":
    main(sys.argv[1:])
