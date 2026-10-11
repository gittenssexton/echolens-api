"""Diagnose replay differences without accepting approximate equality as a pass."""
import argparse
import json
import math
from pathlib import Path


def compare(a, b, path="$", out=None):
    out = [] if out is None else out
    if type(a) is not type(b):
        out.append((path, "type difference", str(type(a)), str(type(b))))
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}.{k}", "missing key", str(k in a), str(k in b)))
            else:
                compare(a[k], b[k], f"{path}.{k}", out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, "length difference", str(len(a)), str(len(b))))
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f"{path}[{i}]", out)
    elif a != b:
        delta = abs(a-b) if isinstance(a, float) and isinstance(b, float) and math.isfinite(a) and math.isfinite(b) else None
        out.append((path, "different value" if delta is None else f"numeric delta={delta:.12g}", repr(a), repr(b)))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("expected")
    p.add_argument("actual")
    a = p.parse_args()
    lhs = json.loads(Path(a.expected).read_text())
    rhs = json.loads(Path(a.actual).read_text())
    mismatches = compare(lhs, rhs)
    print(f"JSON value mismatch count: {len(mismatches)}")
    for item in mismatches[:30]:
        print(" | ".join(item))
    raise SystemExit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
