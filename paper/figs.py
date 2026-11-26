import sys, os, json, warnings, numpy as np, pandas as pd, matplotlib
warnings.filterwarnings("ignore"); matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import foamread as fr
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # repository root
RES, V, OUT = f"{ROOT}/results", f"{ROOT}/validation", f"{ROOT}/paper/figs"
FL = os.environ.get("FLOW_DIR", f"{ROOT}/flow_cases")   # OpenFOAM cases for Figs 1(b,c) and 3 (see README)
HAVE_FLOW = os.path.isdir(f"{FL}/val_single_h0.224_L1")
C, UINF = 0.2234, 30.0
BLUE, GREY, DARK, ORANGE, LIGHT = "#2a78d6", "#8a8983", "#3d3c38", "#d9732f", "#c9c8c2"
plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "mathtext.fontset": "dejavuserif",
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": "#e8e7e3", "grid.linewidth": 0.6, "axes.linewidth": 0.7, "savefig.dpi": 300})
def save(fig, name): fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight"); fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight"); plt.close(fig)
ld = lambda f: pd.read_csv(f, comment="#").sort_values("h_c")
tab = pd.read_csv(f"{RES}/campaign_table.csv"); w = tab[tab.set != "clean"]
# ---------------------------------------------------------------- Fig 1 set-up and mesh
geo = pd.read_csv(f"{ROOT}/geometry/zerihan_single_element.csv", comment="#")
if HAVE_FLOW: polys, cells, walls = fr.slice2d(f"{FL}/val_single_h0.224_L1")
else: polys, walls = [], {"wing": []}; print("flow_cases/ not found: Fig. 1(b,c) without mesh, Fig. 3 skipped")
fig = plt.figure(figsize=(7.0, 4.3)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], hspace=0.38, wspace=0.18)
a = fig.add_subplot(gs[0, :]); a.grid(False)
L0, L1, H = -5, 12, 5
a.add_patch(plt.Rectangle((L0, 0), L1 - L0, H, fill=False, lw=0.8, ec=DARK))
xw = geo.x_c.values; yw = geo.y_c.values - geo.y_c.min() + 0.224
a.fill(np.r_[xw[geo.surface == "suction"], xw[geo.surface == "pressure"][::-1]], np.r_[yw[geo.surface == "suction"], yw[geo.surface == "pressure"][::-1]], color=DARK)
yy = np.linspace(0, H, 200); yc = 0.224 + 0.071; U = 1 - 0.2 * np.exp(-0.5 * (yy - yc) ** 2)
a.plot(L0 + 1.6 * U, yy, color=BLUE, lw=1.2); a.plot([L0, L0 + 1.6], [0, 0], lw=0)
for yv in np.linspace(0.3, 4.7, 9):
    u = 1 - 0.2 * np.exp(-0.5 * (yv - yc) ** 2); a.annotate("", (L0 + 1.6 * u, yv), (L0, yv), arrowprops=dict(arrowstyle="-|>", lw=0.6, color=BLUE, mutation_scale=6))
a.add_patch(plt.Rectangle((L0, 0), 5, H, color=BLUE, alpha=0.06, lw=0))
a.add_patch(plt.Rectangle((0, 0.224), 1, 0.142, fill=False, ec=ORANGE, lw=0.8, ls="--"))
a.text(L0 + 2.0, 4.45, "inlet: Gaussian deficit $D$, turbulence $TI$,\ncentre $y_c$, half-width $\\sigma$", color=BLUE, fontsize=7.5, va="top")
a.text(-1.3, 2.75, "uniform 15 mm cells\n(wake transport zone)", color=BLUE, fontsize=7, ha="center")
a.text(1.25, 0.9, "probe box\n(empty-domain run)", color=ORANGE, fontsize=7)
a.text(3.5, 0.18, "moving ground, $U_\\infty$ = 30 m/s", fontsize=7.5, color=DARK); a.text(3.5, H - 0.45, "slip", fontsize=7.5, color=DARK)
a.text(L1 - 0.15, 2.5, "outlet\n$p$ = 0", fontsize=7.5, color=DARK, ha="right", va="center")
TEY = float(yw[(geo.surface == "pressure").values][-1])
a.set(xlim=(L0 - 0.2, L1 + 0.2), ylim=(-0.2, H + 0.2), xlabel="$x/c$", ylabel="$y/c$", aspect="equal", title="(a) Domain and wake inlet (wing at $h/c$ = 0.224; drawn to scale)")
for ax, (x0, x1, y0, y1), t in [(fig.add_subplot(gs[1, 0]), (-0.1, 1.1, 0.0, 0.42), "(b) Production mesh (level 1) around the wing"),
                                 (fig.add_subplot(gs[1, 1]), (0.975, 1.012, TEY - 0.012, TEY + 0.01), "(c) Trailing edge: boundary-layer fans")]:
    sel = [p / C for p in polys if (p[:, 0].max() / C > x0 - 0.02 and p[:, 0].min() / C < x1 + 0.02 and p[:, 1].max() / C > y0 - 0.02 and p[:, 1].min() / C < y1 + 0.02)]
    ax.add_collection(PolyCollection(sel, facecolor="none", edgecolor=GREY, lw=0.15 if x1 - x0 > 0.5 else 0.3))
    for pw in walls["wing"]: pass
    wing = np.r_[np.c_[xw[geo.surface == "suction"], yw[geo.surface == "suction"]], np.c_[xw[geo.surface == "pressure"], yw[geo.surface == "pressure"]][::-1]]
    ax.fill(wing[:, 0], wing[:, 1], color=DARK, lw=0)
    ax.set(xlim=(x0, x1), ylim=(y0, y1), aspect="equal", title=t, xlabel="$x/c$"); ax.grid(False)
save(fig, "fig1_setup")
# ---------------------------------------------------------------- Fig 2 validation
val = pd.read_csv(f"{RES}/results_validation_L1.csv"); val = val[val.config == "single"]
fig, ax = plt.subplots(figsize=(4.6, 3.2))
ax.axvspan(0.2, 0.5, color=BLUE, alpha=0.06, lw=0); ax.text(0.35, 0.80, "study range", color=BLUE, ha="center", fontsize=7)
for f, m, c, l in [("experiment_single_centre.csv", "s", ORANGE, "Experiment, wing centre (pressures)"), ("experiment_single.csv", "^", "#7a5cc2", "Experiment, whole wing, free transition"), ("experiment_single_fixed.csv", "D", "#3c9a6e", "Experiment, whole wing, fixed transition")]:
    d = ld(f"{V}/{f}"); ax.plot(d.h_c, d.CL, m, color=c, mfc="white", mew=1, ms=3.6, ls="-", lw=0.5, label=l)
for f, ls, l in [("reference_cfd_single_kw.csv", "--", "Zerihan 2D CFD, $k$-$\\omega$"), ("reference_cfd_single_sa.csv", ":", "Zerihan 2D CFD, S-A")]:
    d = ld(f"{V}/{f}"); ax.plot(d.h_c, d.CL, ls, color=DARK, lw=1.1, label=l)
ax.plot(val.h_c, val.CL, "o-", color=BLUE, lw=1.6, ms=4, label="Present, 2D $k$-$\\omega$ SST, level-1 mesh", zorder=5)
nc = val[val.h_c < 0.07]; ax.plot(nc.h_c, nc.CL, "o", mfc="white", mec=BLUE, ms=4, zorder=6)
ax.annotate("not converged", (nc.h_c.iloc[0], nc.CL.iloc[0]), (0.022, 1.43), fontsize=6.5, color=BLUE, arrowprops=dict(arrowstyle="-", lw=0.5, color=BLUE))
ax.set(xlabel="$h/c$", ylabel="$C_L$ (downforce)", ylim=(0.77, 1.85), xlim=(0.015, 0.7)); ax.legend(frameon=False, loc="upper right", fontsize=6.6)
save(fig, "fig2_validation")
# ---------------------------------------------------------------- Fig 3 flow fields
if HAVE_FLOW:
    cases = [("val_single_h0.224_L1", "2000", "(a) Clean air"), ("cmp_o01", "2000", "(b) 20 % wake deficit, centred on the wing"), ("chk_TI10_L05_4k", "4000", "(c) 10 % inlet turbulence, no deficit")]
    fig, axs = plt.subplots(3, 1, figsize=(6.6, 6.4), gridspec_kw={"hspace": 0.32}); x0, x1, y0, y1 = -0.35, 1.9, 0.0, 0.75
    cmap = plt.get_cmap("viridis")
    for ax, (cn, tm, ttl) in zip(axs, cases):
        cp = f"{FL}/{cn}"; polys, cells, walls = fr.slice2d(cp); Uc = fr.field(cp, tm, "U", True)
        mag = np.linalg.norm(Uc[:, :2], axis=1) / UINF
        keep = [i for i, p in enumerate(polys) if p[:, 0].max() / C > x0 and p[:, 0].min() / C < x1 and p[:, 1].min() / C < y1]
        pc = PolyCollection([polys[i] / C for i in keep], array=mag[cells[keep]], cmap=cmap, clim=(0.0, 1.45), edgecolor="face", lw=0.05)
        ax.add_collection(pc)
        wing = np.r_[np.c_[xw[geo.surface == "suction"], yw[geo.surface == "suction"]], np.c_[xw[geo.surface == "pressure"], yw[geo.surface == "pressure"]][::-1]]
        ax.fill(wing[:, 0], wing[:, 1], color="white", lw=0.4, ec="k")
        cl = tab.loc[tab.case == cn, "CL"]; clv = float(cl.iloc[0]) if len(cl) else (1.4131 if "val" in cn else 1.5312)
        ax.set(xlim=(x0, x1), ylim=(y0, y1), aspect="equal", title=f"{ttl}:  $C_L$ = {clv:.3f}"); ax.grid(False)
        ax.set_ylabel("$y/c$")
    axs[-1].set_xlabel("$x/c$")
    cb = fig.colorbar(pc, ax=axs, shrink=0.6, pad=0.02); cb.set_label("$|U|/U_\\infty$")
    save(fig, "fig3_flow")
# ---------------------------------------------------------------- Fig 4 retention vs q
fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.32})
ax = axs[0]; dw = w[w.D > 0]; ti = w[w.D == 0]
ax.plot([0.45, 1.06], [0.45, 1.06], "--", color=GREY, lw=0.8); ax.text(0.5, 0.95, "$R = q_{wing}/q_\\infty$", color=GREY, fontsize=7.5)
s = ax.scatter(dw.q_ratio, dw.R, c=dw.hc, cmap="Greys", vmin=0.05, vmax=0.55, s=16, edgecolor=DARK, lw=0.4, label="wake cases (shade = $h/c$)")
ax.scatter(ti.q_ratio, ti.R, color=BLUE, s=20, zorder=5, label="turbulence only")
ax.set(xlabel="$q_{wing}/q_\\infty$ (empty-domain probe)", ylabel="retention $R = C_L/C_{L0}(h)$", title="(a) All 52 wake cases", xlim=(0.45, 1.05), ylim=(0.45, 1.1))
ax.legend(frameon=False, loc="lower right"); cb = fig.colorbar(s, ax=ax, pad=0.01, shrink=0.85); cb.set_label("$h/c$")
ax = axs[1]; o = w[w.set == "oat"]; rq = lambda r: r.R / r.q_ratio
groups = [("deficit $D$ (centred)", o[(o.TI == 0.005) & (o.dy_c == 0) & (o.hc == 0.224)], "D", "{:.1f}"),
          ("ride height $h/c$ ($D$ = 0.2)", o[(o.D == 0.2) & (o.dy_c == 0) & (o.TI == 0.005)], "hc", "{:.3g}"),
          ("wake offset $dy/c$ ($D$ = 0.2)", o[(o.D == 0.2) & (o.hc == 0.224) & (o.TI == 0.005)], "dy_c", "{:.1f}")]
ck = pd.read_csv(f"{RES}/results_checks.csv"); ck = ck[ck.set == "width"].copy(); c0 = float(np.poly1d(np.polyfit(*tab[tab.set == "clean"][["hc", "CL"]].values.T, 2))(0.224))
ck["R"] = ck.CL / c0; ck = pd.concat([ck, o[(o.case == "cmp_o01")].assign(sigma_c=1.0)])
groups.append(("wake half-width $\\sigma/c$ ($D$ = 0.2)", ck, "sigma_c", "{:.1f}"))
yb = 0; ticks, labels = [], []
for gi, (name, g, col, fmt) in enumerate(groups):
    g = g.sort_values(col); ys = yb + 0.6 + np.arange(len(g)) * 0.55
    ax.plot(rq(g), ys, "o", color=BLUE if gi == 0 else DARK, ms=3.8)
    for yv, (_, r) in zip(ys, g.iterrows()): ticks.append(yv); labels.append(fmt.format(r[col]))
    ax.text(0.9605, yb + 0.05, name, fontsize=6.8, va="center", color=GREY)
    yb = ys.max() + 0.7
ax.axvline(1, color=GREY, lw=0.8, ls="--"); ax.set_yticks(ticks, labels); ax.set_ylim(max(ticks) + 0.4, -0.5)
ax.set(xlim=(0.96, 1.005), xlabel="$R/(q_{wing}/q_\\infty)$", title="(b) Residual after dynamic pressure"); ax.grid(axis="y", visible=False)
save(fig, "fig4_retention")
# ---------------------------------------------------------------- Fig 5 turbulence
c2 = pd.read_csv(f"{RES}/results_checks2.csv"); cl0 = c0
tt = pd.concat([w[(w.D == 0)][["case", "TI", "TI_wing", "CL", "CD_p"]].assign(L=0.05), ck.iloc[0:0]])
lsrows = pd.read_csv(f"{RES}/results_checks.csv"); lsrows = lsrows[lsrows.set == "lengthscale"].assign(L=[0.01, 0.10])
lsrows = lsrows[lsrows.case == "chk_L010"]
c2 = c2.assign(L=[0.05, 0.10])
pts = pd.concat([tt[tt.case != "cmp_o05"], lsrows[["case", "TI", "TI_wing", "CL", "CD_p", "L"]], c2[["case", "TI", "TI_wing", "CL", "CD_p", "L"]]])
pts["gain"] = 100 * (pts.CL / cl0 - 1)
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.7), gridspec_kw={"wspace": 0.3})
mk = {0.01: ("v", "$\\ell$ = 0.01 m"), 0.05: ("o", "$\\ell$ = 0.05 m"), 0.10: ("s", "$\\ell$ = 0.10 m")}
for L_, (m, lab) in mk.items():
    g = pts[np.isclose(pts.L, L_)]
    axs[0].plot(100 * g.TI_wing, g.gain, m, color=BLUE if L_ == 0.05 else DARK, mfc=BLUE if L_ == 0.05 else "white", ms=5, label=lab)
    axs[1].plot(100 * g.TI_wing, g.CD_p, m, color=BLUE if L_ == 0.05 else DARK, mfc=BLUE if L_ == 0.05 else "white", ms=5)
cleanCD = float(np.interp(0.224, *tab[tab.set == "clean"][["hc", "CD_p"]].values.T))
axs[0].plot([0.5], [0], "o", color=GREY, ms=5); axs[1].plot([0.5], [0.0188], "o", color=GREY, ms=5)
axs[0].annotate("clean", (0.5, 0), (0.75, 0.6), fontsize=7, color=GREY); axs[1].annotate("clean", (0.5, 0.0188), (1.0, 0.0193), fontsize=7, color=GREY)
axs[0].set(xlabel="turbulence intensity at the wing [%]", ylabel="change in $C_L$ vs clean air [%]", title="(a) Downforce, no velocity deficit, $h/c$ = 0.224")
axs[1].set(xlabel="turbulence intensity at the wing [%]", ylabel="$C_{D,p}$", title="(b) Pressure drag")
axs[0].legend(frameon=False, loc="upper left")
save(fig, "fig5_turbulence")
pts.to_csv(f"{OUT}/turbulence_points.csv", index=False)
# ---------------------------------------------------------------- Fig 6 models + Sobol
mc = pd.read_csv(f"{RES}/model_comparison.csv"); sm_ = json.load(open(f"{RES}/campaign_summary.json"))
names = {"P0  physics: R = q (no fit)": "Physics: $R=q$ (no fit)", "P1  physics: q + turbulence (2 constants)": "Physics: $q$ + turbulence (2 const.)",
         "Quadratic ridge regression": "Quadratic ridge", "Random forest": "Random forest", "Gradient boosting": "Gradient boosting",
         "Neural network (MLP, tuned)": "Neural network (nested tuning)", "Gaussian process (Matern 5/2, ARD)": "Gaussian process"}
mc["lab"] = mc.model.map(names); mc = mc.sort_values("LOO_RMSE", ascending=False)
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.6), gridspec_kw={"width_ratios": [1.35, 1], "wspace": 0.75})
cols = [BLUE if "Gaussian" in l else (LIGHT if l.startswith("Physics") else GREY) for l in mc.lab]
axs[0].barh(mc.lab, mc.LOO_RMSE, color=cols, height=0.62)
for y_, v in enumerate(mc.LOO_RMSE): axs[0].text(v + 0.0006, y_, f"{v:.4f}", va="center", fontsize=6.8)
axs[0].set(xlabel="leave-one-out RMSE of $R$", title="(a) Surrogate accuracy (56 cases)", xlim=(0, 0.047)); axs[0].grid(axis="y", visible=False)
f_ = ["D", "dy_c", "TI", "hc"]; lab = ["deficit\n$D$", "offset\n$dy/c$", "turbulence\n$TI$", "ride height\n$h/c$"]
x = np.arange(4); axs[1].bar(x - 0.2, [sm_["sobol"][k]["S1"] for k in f_], 0.4, color=BLUE, label="first order")
axs[1].bar(x + 0.2, [sm_["sobol"][k]["ST"] for k in f_], 0.4, color=GREY, label="total")
axs[1].set_xticks(x, lab); axs[1].set(ylabel="Sobol index of $R$", title="(b) Global sensitivity (GP)"); axs[1].legend(frameon=False)
save(fig, "fig6_models")
print("figures written:", sorted(os.listdir(OUT)))
print(pts[["case", "L", "TI_wing", "gain", "CD_p"]].round(4).to_string(index=False)); print("clean CL0(0.224)", round(c0, 4), "clean CD interp", round(cleanCD, 4))
