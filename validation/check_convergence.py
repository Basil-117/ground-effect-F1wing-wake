"""Check whether each validation case has settled: downforce at every saved iteration
(500, 1000, ... ) and the change over the last saved interval.  Flags cases that still drift
or oscillate (> 0.5 %), which steady RANS cannot be trusted for.
Usage:  python3 check_convergence.py          (run inside ~/dirty_air/validation)"""
import os, re, glob, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
rows = []
for sub in ("cfd2d", "frontwing2d"):
    base = os.path.join(here, "..", sub)
    for case in sorted(glob.glob(os.path.join(base, "val_*"))):
        if not os.path.isdir(case): continue
        name = os.path.basename(case)
        out = subprocess.run([sys.executable, "forces.py", name], cwd=base, capture_output=True, text=True).stdout
        hist = [(int(float(m.group(1))), -float(m.group(2))) for m in re.finditer(r"^(\S+) Cl=([-0-9.]+)", out, re.M)]
        log = os.path.join(case, "log.simpleFoam")
        crashed = os.path.exists(log) and "FOAM FATAL" in open(log, errors="ignore").read()
        if len(hist) < 2:
            rows.append((name, "-", "-", "NO RESULTS" + (" (solver crashed)" if crashed else ""))); continue
        last, prev = hist[-1][1], hist[-2][1]
        tail = [c for _, c in hist[-3:]]
        change = abs(last - prev) / abs(last) * 100
        spread = (max(tail) - min(tail)) / abs(last) * 100
        verdict = "ok" if change < 0.5 else ("DRIFTING" if spread < 3 * change + 1e-9 else "OSCILLATING")
        rows.append((name, " ".join(f"{c:.3f}" for _, c in hist), f"{change:.2f}%", verdict))
w = max(len(r[0]) for r in rows)
print(f"{'case':<{w}}  C_L at each saved iteration (500, 1000, ...)        last change  verdict")
for r in rows: print(f"{r[0]:<{w}}  {r[1]:<52} {r[2]:>9}   {r[3]}")
bad = [r[0] for r in rows if r[3] != "ok"]
print(f"\n{len(rows) - len(bad)} of {len(rows)} cases settled." + (f"  Not settled: {', '.join(bad)}" if bad else ""))
