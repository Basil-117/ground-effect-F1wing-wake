"""Design of the dirty-air campaign for the single-element wing (validated core, h/c 0.2-0.5).
Writes campaign.csv, one row per CFD case:
  case, set, hc, D, TI, dy_c, sigma_c
    hc       ride height / chord (lowest point of the wing)
    D        velocity deficit at the wake centre (fraction of U_inf), imposed at the inlet 5c upstream
    TI       peak turbulence intensity in the wake (free stream 0.5 %)
    dy_c     height of the wake centre above the wing's mid-height, in chords (0 = wake centred on the wing)
    sigma_c  Gaussian half-width of the wake, in chords (fixed at 1.0 = 223 mm)
Sets:  clean (no wake, 4 heights) | oat (one factor at a time around a reference wake) | lhs (40-point
Latin hypercube over D, TI, hc, dy_c).  Upwash is NOT a variable: in 2D above a ground plane an imposed
upwash cannot persist (continuity forces V -> 0 near the ground); it only drains mass through the top
boundary and so acts as an extra, artificial deficit.  See README."""
import numpy as np, pandas as pd
from scipy.stats import qmc
SIGMA = 1.0
BOUNDS = {"D": (0.05, 0.30), "TI": (0.005, 0.10), "hc": (0.20, 0.50), "dy_c": (0.0, 2.0)}
REF = dict(hc=0.224, D=0.0, TI=0.005, dy_c=0.0)
rows = []
def add(name, set_, **kw):
    r = dict(REF); r.update(kw); rows.append(dict(case=name, set=set_, **r, sigma_c=SIGMA))
for i, h in enumerate((0.20, 0.30, 0.40, 0.50)):                    # clean-air baselines on the same mesh
    add(f"cmp_c{i}", "clean", hc=h)
k = 0
def oat(**kw):
    global k; add(f"cmp_o{k:02d}", "oat", **kw); k += 1
for D in (0.10, 0.20, 0.30): oat(D=D)                                # deficit alone
for TI in (0.03, 0.06, 0.10): oat(TI=TI)                             # turbulence alone
for dy in (0.5, 1.0, 2.0): oat(D=0.20, dy_c=dy)                      # wake above the wing (shear)
for h in (0.30, 0.40, 0.50): oat(D=0.20, hc=h)                       # ride height, same wake
lo = np.array([b[0] for b in BOUNDS.values()]); hi = np.array([b[1] for b in BOUNDS.values()])
X = qmc.scale(qmc.LatinHypercube(d=4, seed=7, optimization="random-cd").random(40), lo, hi)
for i, x in enumerate(X):
    add(f"cmp_l{i:02d}", "lhs", **{n: round(float(v), 4) for n, v in zip(BOUNDS, x)})
df = pd.DataFrame(rows)[["case", "set", "hc", "D", "TI", "dy_c", "sigma_c"]]
df.to_csv("campaign.csv", index=False)
print(df.groupby("set").size().to_string()); print(f"total {len(df)} cases -> campaign.csv")
