"""Analysis of the single-element dirty-air campaign (results_campaign.csv from run_campaign.sh).

 1. Convergence: cases whose C_L changed > 0.5 % over the last 500 iterations are listed and left out.
 2. Clean-air baseline C_L0(h/c) from the 'clean' runs (same mesh), checked against the validation sweep.
 3. Downforce retention  R = C_L / C_L0(h/c).
 4. Dynamic-pressure test: if the wing kept its clean-air coefficient based on the dynamic pressure it
    actually meets, R would equal q_ratio (from the empty-domain probe).  Reports R / q_ratio and the
    share of the downforce loss that the dynamic-pressure drop explains, and regresses what is left on
    the wing-level turbulence, shear and ride height.
 5. Gaussian-process surrogate of R(D, TI, h/c, dy_c): leave-one-out accuracy, then first-order and total
    Sobol indices of R over the campaign ranges.
Outputs: campaign_figure.png, campaign_summary.json, campaign_table.csv
Usage:  python3 analyse_campaign.py [results_campaign.csv]"""
import sys, os, json, warnings, numpy as np, pandas as pd, matplotlib
warnings.filterwarnings("ignore"); matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel as Ck, WhiteKernel
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol
import statsmodels.api as sm
here = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "results_campaign.csv")
df = pd.read_csv(src)
FEATS = ["D", "TI", "hc", "dy_c"]
BOUNDS = {"D": (0.0, 0.30), "TI": (0.005, 0.10), "hc": (0.20, 0.50), "dy_c": (0.0, 2.0)}
S = {}
# ---- 1. convergence --------------------------------------------------------------------------------
df["change_pct"] = 100 * (df.CL - df.CL_prev).abs() / df.CL.abs()
bad = df[(df.change_pct >= 0.5) | df.CL.isna()]
print(f"{len(df)} cases read; {len(bad)} not settled (>0.5 % change over the last 500 iterations)" +
      (": " + ", ".join(bad.case) if len(bad) else ""))
d = df.drop(bad.index).copy(); S["n_cases"] = int(len(df)); S["n_unsettled"] = int(len(bad))
# ---- 2. clean-air baseline -------------------------------------------------------------------------
cl = d[d.set == "clean"].sort_values("hc")
if len(cl) >= 3:
    base = np.poly1d(np.polyfit(cl.hc, cl.CL, 2)); src_base = f"{len(cl)} clean runs, quadratic in h/c"
else:
    v = pd.read_csv(os.path.join(here, "..", "validation", "results_validation_L1.csv")).query("config == 'single'").sort_values("h_c")
    base = lambda h: np.interp(h, v.h_c, v.CL); src_base = "validation sweep (mesh level 1), interpolated"
print(f"Clean baseline from {src_base}:  C_L0(0.2)={base(0.2):.4f}  C_L0(0.35)={base(0.35):.4f}  C_L0(0.5)={base(0.5):.4f}")
vp = os.path.join(here, "..", "validation", "results_validation_L1.csv")
if os.path.exists(vp) and len(cl):
    v = pd.read_csv(vp).query("config == 'single'").sort_values("h_c")
    dev = 100 * (cl.CL.to_numpy() / np.interp(cl.hc, v.h_c, v.CL) - 1)
    print("  clean runs vs validation sweep (checks that the upstream refinement changes nothing): " +
          ", ".join(f"h/c {h:.2f}: {e:+.2f}%" for h, e in zip(cl.hc, dev)))
    S["clean_vs_validation_pct"] = [round(float(e), 3) for e in dev]
d["CL0"] = base(d.hc); d["R"] = d.CL / d.CL0
d.to_csv(os.path.join(here, "campaign_table.csv"), index=False)
# ---- 3/4. retention and the dynamic-pressure test -----------------------------------------------------
w = d[(d.set != "clean") & d.q_ratio.notna()].copy()
w["R_over_q"] = w.R / w.q_ratio
lossy = w[w.R < 0.98]
expl = ((1 - lossy.q_ratio) / (1 - lossy.R)).clip(0, 3)
print(f"\nRetention R over the wake runs: {w.R.min():.3f} - {w.R.max():.3f}")
print(f"R / q_ratio (1 = coefficient on local dynamic pressure unchanged): median {w.R_over_q.median():.3f}, "
      f"range {w.R_over_q.min():.3f} - {w.R_over_q.max():.3f}")
if len(lossy): print(f"Share of the downforce loss explained by the dynamic-pressure drop (cases with R < 0.98): "
                     f"median {100*expl.median():.0f} %, IQR {100*expl.quantile(.25):.0f}-{100*expl.quantile(.75):.0f} %")
S.update(R_min=float(w.R.min()), R_max=float(w.R.max()), R_over_q_median=float(w.R_over_q.median()),
         loss_explained_by_q_median=float(expl.median()) if len(lossy) else None)
if len(w) >= 8:
    Xr = sm.add_constant(w[["TI_wing", "shear", "hc"]]); fit = sm.OLS(w.R_over_q - 1, Xr).fit(cov_type="HC3")
    print("\nWhat the dynamic pressure does not explain:  R/q - 1  ~  TI_wing + shear + h/c   (robust SEs)")
    print(fit.summary2().tables[1][["Coef.", "Std.Err.", "P>|z|"]].round(4).to_string())
    print(f"  R^2 = {fit.rsquared:.3f}")
    S["residual_model"] = {k: dict(coef=float(fit.params[k]), p=float(fit.pvalues[k])) for k in fit.params.index}
# ---- 5. surrogate + Sobol -------------------------------------------------------------------------------
lo = np.array([BOUNDS[f][0] for f in FEATS]); hi = np.array([BOUNDS[f][1] for f in FEATS])
sc = lambda X: (np.asarray(X, float) - lo) / (hi - lo)
X = d[FEATS].to_numpy(); y = d.R.to_numpy(); HAVE_GP = len(y) >= 12
if not HAVE_GP: print(f"\nOnly {len(y)} settled cases: surrogate and Sobol indices need at least 12 (run the lhs set).")
else:
    def gp():
        k = Ck(1.0) * Matern([0.5] * 4, (1e-2, 1e2), nu=2.5) + WhiteKernel(1e-5, (1e-9, 1e-2))
        return GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=10, random_state=0)
    yloo = cross_val_predict(gp(), sc(X), y, cv=LeaveOneOut())
    r2 = 1 - np.sum((y - yloo) ** 2) / np.sum((y - y.mean()) ** 2); rmse = float(np.sqrt(np.mean((y - yloo) ** 2)))
    m = gp().fit(sc(X), y); ls = m.kernel_.k1.k2.length_scale
    print(f"\nGP surrogate of R: n = {len(y)}, leave-one-out R^2 = {r2:.3f}, RMSE = {rmse:.4f}")
    print("  ARD length scales (smaller = more influential): " + ", ".join(f"{f} {l:.2f}" for f, l in zip(FEATS, ls)))
    prob = {"num_vars": 4, "names": FEATS, "bounds": [list(BOUNDS[f]) for f in FEATS]}
    P = sobol_sample.sample(prob, 2048, calc_second_order=False, seed=1)
    Si = sobol.analyze(prob, m.predict(sc(P)), calc_second_order=False, seed=1)
    print("  Sobol indices of R      first-order   total")
    for f, a, b in zip(FEATS, Si["S1"], Si["ST"]): print(f"    {f:6}               {a:6.3f}      {b:6.3f}")
    S.update(gp_loo_r2=float(r2), gp_loo_rmse=rmse, sobol={f: dict(S1=float(a), ST=float(b)) for f, a, b in zip(FEATS, Si["S1"], Si["ST"])})
# ---- figure ---------------------------------------------------------------------------------------------
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e4e3de"})
fig, ax = plt.subplots(2, 2, figsize=(11, 8.5), gridspec_kw={"wspace": 0.28, "hspace": 0.38}); ax = ax.ravel()
o = w[w.set == "oat"]
oD = pd.concat([o[(o.TI == 0.005) & (o.dy_c == 0) & (o.hc == 0.224)]]).sort_values("D")
ax[0].plot(np.r_[0, oD.D], np.r_[1, oD.R], "o-", color="#2a78d6", label="C_L / C_L0  (CFD)")
ax[0].plot(np.r_[0, oD.D], np.r_[1, oD.q_ratio], "s--", color="#8a8983", mfc="white", label="q at wing / q_inf  (empty-domain probe)")
ax[0].plot(np.linspace(0, .3), (1 - np.linspace(0, .3)) ** 2, ":", color="#52514e", label="(1 - D)^2")
ax[0].set(title="a) Deficit alone, h/c = 0.224, wake centred", xlabel="imposed deficit D", ylabel="retention R")
ax[0].legend(frameon=False, fontsize=7)
sc_ = ax[1].scatter(w.q_ratio, w.R, c=w.hc, cmap="viridis", s=22, edgecolor="k", lw=0.3)
lim = [min(w.q_ratio.min(), w.R.min()) - 0.02, 1.02]; ax[1].plot(lim, lim, "--", color="#8a8983", lw=1)
ax[1].set(title="b) Retention vs dynamic pressure at the wing", xlabel="q_wing / q_inf", ylabel="R = C_L / C_L0")
plt.colorbar(sc_, ax=ax[1], label="h/c")
if HAVE_GP:
  ax[2].plot(y, yloo, "o", color="#2a78d6", ms=4); ax[2].plot([y.min(), y.max()], [y.min(), y.max()], "--", color="#8a8983")
  ax[2].set(title=f"c) Surrogate leave-one-out check (R^2 = {r2:.3f})", xlabel="R from CFD", ylabel="R predicted (case left out)")
  i = np.arange(4); ax[3].bar(i - 0.18, Si["S1"], 0.36, color="#2a78d6", label="first order")
  ax[3].bar(i + 0.18, Si["ST"], 0.36, color="#eb6834", label="total"); ax[3].set_xticks(i, ["deficit\nD", "turbulence\nTI", "ride height\nh/c", "wake offset\ndy/c"])
  ax[3].set(title="d) Sobol indices of retention", ylabel="index"); ax[3].legend(frameon=False)
else:
  for a_ in ax[2:]: a_.axis("off")
out = os.path.join(here, "campaign_figure.png"); fig.savefig(out, dpi=170, bbox_inches="tight")
json.dump(S, open(os.path.join(here, "campaign_summary.json"), "w"), indent=1)
print(f"\nwrote {out}, campaign_summary.json, campaign_table.csv")
