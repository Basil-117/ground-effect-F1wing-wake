"""2D two-element front wing (Zerihan 2001 / Zhang & Zerihan 2003 geometry) above a moving ground.
Usage: python mesh2.py <h_over_c> <flap_deg> <out.msh> [dalpha_deg]
  h_over_c : ride height of the lowest point of the wing / overall chord (c = 380 mm)
  flap_deg : flap chord angle relative to the main-element chord; datum (Table 4) = 18.93 deg,
             Zhang & Zerihan's 'low flap' (datum - 8.5 deg) = 10.43 deg. Flap rotates about its leading edge.
  dalpha   : optional change of overall incidence (rotation of the whole wing, deg, + = trailing edge up)
Coordinates are read from ../geometry/zerihan_double_{main,flap}.csv (override with GEOMETRY_DIR)."""
import sys, os, math, numpy as np, pandas as pd, gmsh
hc, dflap, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
dalpha = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
C = 0.380                                         # overall chord [m]; tables are x/c, y/c with c = 380 mm
GEO = os.environ.get("GEOMETRY_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "geometry"))
FLAP_DATUM = 18.93                                # flap chord angle relative to main chord in Table 4 [deg]
def load(name):
    d = pd.read_csv(os.path.join(GEO, name), comment="#")
    su, pr = d[d.surface == "suction"], d[d.surface == "pressure"]
    return su[["x_c", "y_c"]].to_numpy(float), pr[["x_c", "y_c"]].to_numpy(float)
def rot(P, ang_deg, about):
    a = math.radians(ang_deg); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (P - about) @ R.T + about
ms, mp = load("zerihan_double_main.csv"); fs, fp = load("zerihan_double_flap.csv")
# flap deflection: rotate about the flap leading edge (positive = trailing edge up = more downforce)
fs, fp = rot(fs, dflap - FLAP_DATUM, fs[0]), rot(fp, dflap - FLAP_DATUM, fs[0])
# optional change of overall incidence: rotate the whole assembly about the main-element leading edge
if dalpha:
    ms, mp, fs, fp = (rot(P, dalpha, ms[0]) for P in (ms, mp, fs, fp))
ms, mp, fs, fp = (P * C for P in (ms, mp, fs, fp))
shift = hc * C - min(P[:, 1].min() for P in (ms, mp, fs, fp))
ms, mp, fs, fp = (P + [0, shift] for P in (ms, mp, fs, fp))
te = ms[-1]                                       # main-element trailing edge (suction side), for slot refinement
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); gmsh.model.add("fw")
g = gmsh.model.geo
def airfoil(su, pr):
    """closed loop: suction TE -> LE -> pressure TE -> (blunt base) -> suction TE"""
    ps = [g.addPoint(x, y, 0) for x, y in su[::-1]]            # TE ... LE
    pp = [ps[-1]] + [g.addPoint(x, y, 0) for x, y in pr[1:]]   # LE ... TE
    s1, s2 = g.addSpline(ps), g.addSpline(pp); s3 = g.addLine(pp[-1], ps[0])
    return [s1, s2, s3]
wm, wf = airfoil(ms, mp), airfoil(fs, fp)
lm, lf = g.addCurveLoop(wm), g.addCurveLoop(wf)
L0, L1, H = -5*C, 12*C, 5*C
q = [g.addPoint(L0,0,0), g.addPoint(L1,0,0), g.addPoint(L1,H,0), g.addPoint(L0,H,0)]
lines = [g.addLine(q[0],q[1]), g.addLine(q[1],q[2]), g.addLine(q[2],q[3]), g.addLine(q[3],q[0])]
surf = g.addPlaneSurface([g.addCurveLoop(lines), lm, lf]); g.synchronize()
# ---- mesh resolution: MESH_LEVEL=0 (default) is the original coarse wall-function mesh;
#      MESH_LEVEL=1,2,3 are wall-resolved (y+ ~ 1) meshes, each ~1.5x finer than the last (for a GCI study)
LV = int(os.environ.get("MESH_LEVEL", "0"))
if LV == 0: S = dict(surf=0.0022, gnd=0.006, box=0.016, slot=0.0018, y1=None)
else:
    r = 1.5 ** (LV - 1)
    S = dict(surf=0.0016 / r, gnd=0.004 / r, box=0.012 / r, slot=0.0010 / r, y1=1.5e-5 / r, ratio=1.2 ** (1 / r), blt=0.003)
F = gmsh.model.mesh.field
if S["y1"]:
    bl = F.add("BoundaryLayer"); F.setNumbers(bl, "CurvesList", wm + wf); F.setNumber(bl, "Size", S["y1"])
    F.setNumber(bl, "Ratio", S["ratio"]); F.setNumber(bl, "Thickness", S["blt"]); F.setNumber(bl, "Quads", 1)
    te_pts = [abs(b[1]) for w in (wm, wf) for b in gmsh.model.getBoundary([(1, w[2])])]   # ends of each blunt base
    F.setNumbers(bl, "FanPointsList", te_pts)     # fans at all four trailing-edge corners
    F.setAsBoundaryLayer(bl)
d = F.add("Distance"); F.setNumbers(d, "CurvesList", wm+wf); F.setNumber(d, "Sampling", 400)
t1 = F.add("Threshold"); F.setNumber(t1,"InField",d); F.setNumber(t1,"SizeMin",S["surf"]); F.setNumber(t1,"SizeMax",0.10)
F.setNumber(t1,"DistMin",0.003); F.setNumber(t1,"DistMax",1.5)
dg = F.add("Distance"); F.setNumbers(dg, "CurvesList", [lines[0]]); F.setNumber(dg, "Sampling", 800)
tg = F.add("Threshold"); F.setNumber(tg,"InField",dg); F.setNumber(tg,"SizeMin",S["gnd"]); F.setNumber(tg,"SizeMax",0.10)
F.setNumber(tg,"DistMin",0.004); F.setNumber(tg,"DistMax",0.3)
bx = F.add("Box"); F.setNumber(bx,"VIn",S["box"]); F.setNumber(bx,"VOut",0.10)
for k, v in dict(XMin=-0.05, XMax=2.0, YMin=0, YMax=hc*C+0.2).items(): F.setNumber(bx, k, v)
sl = F.add("Box"); F.setNumber(sl,"VIn",S["slot"]); F.setNumber(sl,"VOut",0.10)   # slot refinement
for k, v in dict(XMin=te[0]-0.03, XMax=te[0]+0.03, YMin=0, YMax=hc*C+0.12).items(): F.setNumber(sl, k, v)
mn = F.add("Min"); F.setNumbers(mn, "FieldsList", [t1, tg, bx, sl]); F.setAsBackgroundMesh(mn)
for k in ["MeshSizeExtendFromBoundary","MeshSizeFromPoints","MeshSizeFromCurvature"]: gmsh.option.setNumber("Mesh."+k, 0)
gmsh.option.setNumber("Mesh.Algorithm", 5)
ext = g.extrude([(2, surf)], 0, 0, 0.01, numElements=[1], recombine=True); g.synchronize()
top, vol = ext[0][1], ext[1][1]; sides = [e[1] for e in ext[2:]]
gmsh.model.addPhysicalGroup(3, [vol], name="fluid")
for tag, name in zip(sides[:4], ["ground","outlet","top","inlet"]): gmsh.model.addPhysicalGroup(2, [tag], name=name)
gmsh.model.addPhysicalGroup(2, sides[4:7], name="wing")       # main element (3 curves)
gmsh.model.addPhysicalGroup(2, sides[7:10], name="flap")
gmsh.model.addPhysicalGroup(2, [surf, top], name="frontAndBack")
gmsh.model.mesh.generate(3); gmsh.option.setNumber("Mesh.MshFileVersion", 2.2); gmsh.write(out); gmsh.finalize()
loop = lambda su, pr: np.r_[su[::-1], pr[1:], su[-1:]]
np.savetxt(out.replace(".msh", "_geom.txt"), np.r_[loop(ms, mp), [[np.nan, np.nan]], loop(fs, fp)])
print("wrote", out)
