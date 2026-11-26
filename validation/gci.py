"""Grid Convergence Index (Celik et al., J. Fluids Eng. 130, 078001, 2008) from results_mesh_study.csv.

For each (config, h/c) with three mesh levels it reports the apparent order p, the Richardson-
extrapolated C_L, and GCI_fine (the numerical uncertainty band of the finest mesh, 95 %).
With only two levels it reports the relative change between them.
Usage:  python3 gci.py [results_mesh_study.csv]"""
import sys, math, os, pandas as pd
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_mesh_study.csv")
df = pd.read_csv(path)
R_NOMINAL = 1.5                       # intended refinement ratio between levels (cell size)
print(f"{'config':8} {'h/c':6} {'levels':7} {'cells (coarse->fine)':26} {'C_L':>26}   result")
for (cfg, h), g in df.groupby(["config", "h_c"]):
    g = g.sort_values("level"); n = len(g)
    cells = list(g.cells); cl = list(g.CL); lv = list(g.level)
    settled = all(abs(a - b) / abs(a) < 0.005 for a, b in zip(g.CL, g.CL_prev) if b)
    note = "" if settled else "  [warning: a run was still changing >0.5% over its last 500 iterations]"
    if n >= 3:
        f1, f2, f3 = cl[-1], cl[-2], cl[-3]            # fine, medium, coarse
        r21 = math.sqrt(cells[-1] / cells[-2]); r32 = math.sqrt(cells[-2] / cells[-3])   # 2D: h ~ N^-1/2
        e21, e32 = f2 - f1, f3 - f2
        if e21 == 0 or e32 == 0 or e21 * e32 < 0:
            res = "oscillatory convergence - GCI not defined; report the spread %.3f" % (max(cl) - min(cl))
        elif abs(e21) >= abs(e32):
            res = (f"NOT in the asymptotic range: the fine-mesh change ({e21:+.4f}) is larger than the medium-mesh change "
                   f"({e32:+.4f}); add a finer level or report the fine-mesh value with uncertainty >= {100*abs(e21/f1):.1f}%")
        else:
            s = 1.0; p = abs(math.log(abs(e32 / e21))) / math.log(r21)
            for _ in range(50):                             # fixed-point iteration for p (Celik eq. 3)
                q = math.log((r21 ** p - s) / (r32 ** p - s)) if r21 != r32 else 0.0
                p = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
            f_ext = (r21 ** p * f1 - f2) / (r21 ** p - 1)
            ea = abs((f2 - f1) / f1); gci = 1.25 * ea / (r21 ** p - 1)
            res = f"p = {p:.2f}, extrapolated C_L = {f_ext:.4f}, GCI_fine = {100 * gci:.2f}%"
            if p > 3: res += "  (p > 3 is unphysical: meshes not yet in the asymptotic range; treat GCI as indicative)"
    elif n == 2:
        res = f"change level {lv[0]}->{lv[1]}: {100 * (cl[1] - cl[0]) / cl[1]:+.2f}%  (two levels only)"
    else:
        res = "only one level"
    print(f"{cfg:8} {h:<6} {str(lv):7} {str(cells):26} {str([round(c, 4) for c in cl]):>26}   {res}{note}")
