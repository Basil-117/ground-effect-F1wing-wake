"""2D single-element wing in ground effect (Zerihan 2001 thesis, Table 2 profile), one cell thick.
Usage: python mesh.py <h_over_c> <alpha_deg> <out.msh>
  h_over_c : ride height of the lowest point / chord (c = 223.4 mm)
  alpha    : Zerihan's reference incidence in degrees (the tabulated geometry is alpha = 1)
Options (environment):
  MESH_LEVEL=0|1|2|3  coarse wall-function mesh (0) or wall-resolved levels (1 = production)
  WAKE_REFINE=1       uniform 15 mm cells from the inlet to the wing over the full height, so an imposed
                      wake profile is carried to the wing without numerical smearing (dirty-air campaign)
  NO_WING=1           same domain and refinement but no wing: the "empty tunnel" run that measures the
                      flow the wing would see (probe.py)"""
import sys, os, math, numpy as np, pandas as pd, gmsh
hc = float(sys.argv[1]); alpha = float(sys.argv[2]); out = sys.argv[3]
c = 0.2234                                   # chord [m] (Zerihan & Zhang 2000)
GEO = os.environ.get("GEOMETRY_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "geometry"))
d = pd.read_csv(os.path.join(GEO, "zerihan_single_element.csv"), comment="#")
su = d[d.surface == "suction"][["x_c", "y_c"]].to_numpy(float)   # LE -> TE, faces the ground
pr = d[d.surface == "pressure"][["x_c", "y_c"]].to_numpy(float)  # LE -> TE
# Table 2 is at Zerihan's reference incidence of 1 deg; rotate by (alpha - 1) about the leading edge
a = math.radians(alpha - 1.0); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
su, pr = (su @ R.T) * c, (pr @ R.T) * c
shift = hc * c - min(su[:, 1].min(), pr[:, 1].min()); su[:, 1] += shift; pr[:, 1] += shift
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); gmsh.model.add("wig")
occ = gmsh.model.geo
L0, L1, H = -5*c, 12*c, 5*c
NO_WING = os.environ.get("NO_WING") == "1"
if not NO_WING:
    ps = [occ.addPoint(x, y, 0) for x, y in su[::-1]]              # TE ... LE (suction side)
    pp = [ps[-1]] + [occ.addPoint(x, y, 0) for x, y in pr[1:]]     # LE ... TE (pressure side)
    s1, s2 = occ.addSpline(ps), occ.addSpline(pp); s3 = occ.addLine(pp[-1], ps[0])   # blunt trailing edge
    wing_loop = occ.addCurveLoop([s1, s2, s3])
q = [occ.addPoint(L0,0,0), occ.addPoint(L1,0,0), occ.addPoint(L1,H,0), occ.addPoint(L0,H,0)]
lg, lo, lt, li = occ.addLine(q[0],q[1]), occ.addLine(q[1],q[2]), occ.addLine(q[2],q[3]), occ.addLine(q[3],q[0])
outer = occ.addCurveLoop([lg, lo, lt, li])
surf = occ.addPlaneSurface([outer] if NO_WING else [outer, wing_loop])
occ.synchronize()
# ---- mesh resolution: MESH_LEVEL=0 (default) is the original coarse wall-function mesh;
#      MESH_LEVEL=1,2,3 are wall-resolved (y+ ~ 1) meshes, each ~1.41x finer than the last (for a GCI study)
L = int(os.environ.get("MESH_LEVEL", "0"))
if L == 0: S = dict(y1=0.0006, ratio=1.2, blt=0.006, surf=0.0025, gnd=0.006, box=0.01, gy1=None)
else:
    r = 1.5 ** (L - 1)
    S = dict(y1=1.5e-5 / r, ratio=1.2 ** (1 / r), blt=0.006, surf=0.0016 / r, gnd=0.004 / r, box=0.008 / r, gy1=3e-5 / r)
f = gmsh.model.mesh.field
if not NO_WING:
    bl = f.add("BoundaryLayer"); f.setNumbers(bl, "CurvesList", [s1, s2, s3]); f.setNumber(bl, "Size", S["y1"])
    f.setNumber(bl, "Ratio", S["ratio"]); f.setNumber(bl, "Thickness", S["blt"]); f.setNumber(bl, "Quads", 1)
    f.setNumbers(bl, "FanPointsList", [ps[0], pp[-1]])   # fans at both corners of the blunt trailing edge
    f.setAsBoundaryLayer(bl)
if S["gy1"] and os.environ.get("GROUND_BL") == "1":   # optional resolved layer on the moving ground (off: wall functions there)
    bg = f.add("BoundaryLayer"); f.setNumbers(bg, "CurvesList", [lg]); f.setNumber(bg, "Size", S["gy1"])
    f.setNumber(bg, "Ratio", S["ratio"]); f.setNumber(bg, "Thickness", 0.004); f.setNumber(bg, "Quads", 1)
    f.setAsBoundaryLayer(bg)
fields = []
if not NO_WING:
    d = f.add("Distance"); f.setNumbers(d, "CurvesList", [s1, s2, s3]); f.setNumber(d, "Sampling", 400)
    th1 = f.add("Threshold"); f.setNumber(th1, "InField", d); f.setNumber(th1, "SizeMin", S["surf"])
    f.setNumber(th1, "SizeMax", 0.08); f.setNumber(th1, "DistMin", 0.005); f.setNumber(th1, "DistMax", 1.2)
    fields.append(th1)
dg = f.add("Distance"); f.setNumbers(dg, "CurvesList", [lg]); f.setNumber(dg, "Sampling", 800)
thg = f.add("Threshold"); f.setNumber(thg, "InField", dg); f.setNumber(thg, "SizeMin", S["gnd"])
f.setNumber(thg, "SizeMax", 0.08); f.setNumber(thg, "DistMin", 0.004); f.setNumber(thg, "DistMax", 0.3)
box = f.add("Box"); f.setNumber(box,"VIn",S["box"]); f.setNumber(box,"VOut",0.08)
for k,v in dict(XMin=-0.05,XMax=1.5,YMin=0,YMax=hc*c+0.12).items(): f.setNumber(box,k,v)
fields += [thg, box]
if os.environ.get("WAKE_REFINE") == "1" or NO_WING:   # carry the imposed wake from the inlet to the wing
    wb = f.add("Box"); f.setNumber(wb, "VIn", 0.015); f.setNumber(wb, "VOut", 0.08)
    for k, v in dict(XMin=L0, XMax=0.0, YMin=0, YMax=H).items(): f.setNumber(wb, k, v)
    fields.append(wb)
mn = f.add("Min"); f.setNumbers(mn, "FieldsList", fields); f.setAsBackgroundMesh(mn)
for k in ["MeshSizeExtendFromBoundary","MeshSizeFromPoints","MeshSizeFromCurvature"]:
    gmsh.option.setNumber("Mesh."+k, 0)
gmsh.option.setNumber("Mesh.Algorithm", 5)
ext = occ.extrude([(2, surf)], 0, 0, 0.01, numElements=[1], recombine=True); occ.synchronize()
# ext: [top surf, volume, side surfaces in curve order: lg, lo, lt, li, s1, s2]
top, vol = ext[0][1], ext[1][1]; sides = [e[1] for e in ext[2:]]
gmsh.model.addPhysicalGroup(3, [vol], name="fluid")
for tag, name in zip(sides[:4], ["ground","outlet","top","inlet"]):
    gmsh.model.addPhysicalGroup(2, [tag], name=name)
if not NO_WING: gmsh.model.addPhysicalGroup(2, sides[4:7], name="wing")
gmsh.model.addPhysicalGroup(2, [surf, top], name="frontAndBack")
gmsh.model.mesh.generate(3)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2); gmsh.write(out); gmsh.finalize()
print("wrote", out)
