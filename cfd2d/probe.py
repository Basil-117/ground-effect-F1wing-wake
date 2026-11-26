"""What does the wing actually see?  Reads an empty-domain run (NO_WING=1, same inlet wake, same domain)
and averages the flow over the box the wing would occupy: x from the leading edge to the trailing edge,
y from the ride height h to h + 0.142c (the profile's vertical extent at 1 deg).

Prints one line:  q_ratio=... u_ratio=... angle_deg=... TI_wing=... shear=...
  q_ratio   mean |U|^2 / U_inf^2            (dynamic-pressure ratio the wing sees)
  u_ratio   mean U_x / U_inf
  angle_deg mean flow angle, + = upwash     (reduces an inverted wing's effective incidence)
  TI_wing   sqrt(2k/3) / |U| at the wing     (the inlet value decays on the way)
  shear     dU_x/dy * c / U_inf across the wing box (+ = faster air above the wing)
Usage: python probe.py <empty_case> <h_over_c> [alpha_deg] [--csv]   (--csv: q,u,angle,TI,shear only)"""
import sys, os, re, math, numpy as np
CSV = '--csv' in sys.argv; argv = [a for a in sys.argv if a != '--csv']
case, hc = argv[1], float(argv[2]); alpha = float(argv[3]) if len(argv) > 3 else 1.0
Uinf, c = 30.0, 0.2234
def body(path):
    t = open(path).read(); t = re.sub(r'/\*.*?\*/', '', t, flags=re.S); t = re.sub(r'//.*', '', t)
    return t[t.index('}', t.index('FoamFile')) + 1:]
def lst(t, start=0):
    m = re.search(r'(\d+)\s*\(', t[start:]); i = start + m.end(); depth = 1; j = i
    while depth: j += 1; depth += {'(': 1, ')': -1}.get(t[j], 0)
    return int(m.group(1)), t[i:j]
pm = os.path.join(case, 'constant/polyMesh')
_, s = lst(body(pm + '/points')); P = np.array([list(map(float, p.split())) for p in re.findall(r'\(([^()]+)\)', s)])
_, s = lst(body(pm + '/faces')); F = [list(map(int, f.split())) for f in re.findall(r'\d+\s*\(([^()]+)\)', s)]
_, s = lst(body(pm + '/owner')); own = np.array(s.split(), int)
_, s = lst(body(pm + '/neighbour')); nei = np.array(s.split(), int)
fc = np.array([P[f].mean(0) for f in F])                         # face centres
nc = own.max() + 1; C = np.zeros((nc, 3)); n = np.zeros(nc)
np.add.at(C, own, fc); np.add.at(n, own, 1); np.add.at(C, nei, fc[:len(nei)]); np.add.at(n, nei, 1)
C /= n[:, None]                                                   # cell centres (mean of face centres)
tm = max((d for d in os.listdir(case) if re.fullmatch(r'\d+(\.\d+)?', d) and d != '0'), key=float)
def field(name, vector):
    b = body(os.path.join(case, tm, name)); k = b.index('internalField')
    if re.match(r'\s*uniform', b[k + 13:]):
        v = np.array(re.search(r'uniform\s+\(?([^;)]*)', b[k:]).group(1).split(), float)
        return np.tile(v, (nc, 1)) if vector else np.full(nc, v[0])
    _, s = lst(b, k)
    return np.array([list(map(float, x.split())) for x in re.findall(r'\(([^()]+)\)', s)]) if vector else np.array(s.split(), float)
U, k = field('U', True), field('k', False)
h = hc * c; ext = 0.142 * c * math.cos(math.radians(alpha - 1))   # the wing box
sel = (C[:, 0] >= 0) & (C[:, 0] <= c) & (C[:, 1] >= h) & (C[:, 1] <= h + ext)
if sel.sum() < 3:                                                 # coarse cells: widen the box a little
    sel = (C[:, 0] >= -0.02) & (C[:, 0] <= c + 0.02) & (C[:, 1] >= h - 0.01) & (C[:, 1] <= h + ext + 0.01)
u, k_, y = U[sel], k[sel], C[sel, 1]
mag = np.linalg.norm(u[:, :2], axis=1)
q = np.mean(mag ** 2) / Uinf ** 2
ang = math.degrees(math.atan2(u[:, 1].mean(), u[:, 0].mean()))
ti = np.mean(np.sqrt(2 * k_ / 3)) / mag.mean()
shear = np.polyfit(y, u[:, 0], 1)[0] * c / Uinf if np.ptp(y) > 0 else 0.0
if CSV: print(f"{q:.4f},{u[:, 0].mean() / Uinf:.4f},{ang:.3f},{ti:.4f},{shear:.4f}"); sys.exit()
print(f"{tm} q_ratio={q:.4f} u_ratio={u[:, 0].mean() / Uinf:.4f} angle_deg={ang:.3f} TI_wing={ti:.4f} shear={shear:.4f} cells={int(sel.sum())}")
