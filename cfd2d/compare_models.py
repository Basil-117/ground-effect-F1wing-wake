"""Which model predicts downforce retention best?  Leave-one-out comparison on the campaign data.

Physics models (use the empty-domain probe, which costs ~2 min of CFD per wake but no wing run):
  P0  R = q_wing/q_inf                                   no fitted constants
  P1  R = a*q + b*q*(TI_wing - 0.005)                    two constants
Data-driven models (use only the four wake/design inputs D, TI, h/c, dy/c):
  quadratic ridge regression, random forest, gradient boosting, small neural network (MLP; size and weight decay
  tuned by an inner 5-fold search inside every leave-one-out fold), Gaussian process
Every model is scored the same way: each case is predicted by a model fitted to the other cases.
Reads campaign_table.csv (written by analyse_campaign.py).  Output: printed table, model_comparison.csv/.png
Usage:  python3 compare_models.py [campaign_table.csv]"""
import sys, os, warnings, numpy as np, pandas as pd, matplotlib
warnings.filterwarnings("ignore"); matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import LeaveOneOut, cross_val_predict, GridSearchCV, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler, MinMaxScaler
from sklearn.linear_model import RidgeCV, LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel as Ck, WhiteKernel
here = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "campaign_table.csv")).dropna(subset=["R"])
FEATS = ["D", "TI", "hc", "dy_c"]; X = d[FEATS].to_numpy(); y = d.R.to_numpy()
tiw = d["TI_wing"].to_numpy() if "TI_wing" in d else d.TI.to_numpy()
Xp = np.c_[d.q_ratio, d.q_ratio * (tiw - 0.005)]
loo = LeaveOneOut()
models = {
    "P0  physics: R = q (no fit)": None,
    "P1  physics: q + turbulence (2 constants)": (LinearRegression(fit_intercept=False), Xp),
    "Quadratic ridge regression": (make_pipeline(StandardScaler(), PolynomialFeatures(2), RidgeCV(alphas=np.logspace(-6, 2, 30))), X),
    "Random forest": (RandomForestRegressor(n_estimators=500, min_samples_leaf=2, random_state=0), X),
    "Gradient boosting": (GradientBoostingRegressor(n_estimators=400, learning_rate=0.05, max_depth=2, subsample=0.8, random_state=0), X),
    # the network's size and weight decay are tuned INSIDE each leave-one-out fold (nested), so its score is not flattered
    "Neural network (MLP, tuned)": (GridSearchCV(make_pipeline(StandardScaler(), MLPRegressor(solver="lbfgs", activation="tanh",
        max_iter=5000, random_state=0)), {"mlpregressor__hidden_layer_sizes": [(8,), (16, 16)], "mlpregressor__alpha": [1e-4, 1e-2, 1e-1]},
        cv=KFold(5, shuffle=True, random_state=0), scoring="neg_root_mean_squared_error"), X),
    "Gaussian process (Matern 5/2, ARD)": (make_pipeline(MinMaxScaler(), GaussianProcessRegressor(
        Ck(1.0) * Matern([0.5] * 4, (1e-2, 1e2), nu=2.5) + WhiteKernel(1e-5, (1e-9, 1e-2)), normalize_y=True,
        n_restarts_optimizer=10, random_state=0)), X),
}
rows, preds = [], {}
for name, spec in models.items():
    p = d.q_ratio.to_numpy() if spec is None else cross_val_predict(spec[0], spec[1], y, cv=loo)
    e = p - y; preds[name] = p
    rows.append(dict(model=name, LOO_RMSE=np.sqrt(np.mean(e ** 2)), LOO_MAE=np.mean(np.abs(e)),
                     max_error=np.abs(e).max(), LOO_R2=1 - np.sum(e ** 2) / np.sum((y - y.mean()) ** 2)))
res = pd.DataFrame(rows)
print(f"n = {len(y)} cases, retention range {y.min():.3f}-{y.max():.3f}\n")
print(res.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
res.to_csv(os.path.join(here, "model_comparison.csv"), index=False)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e4e3de"})
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"wspace": 0.55})
o = res.sort_values("LOO_RMSE", ascending=False)
ax[0].barh(o.model, o.LOO_RMSE, color=["#8a8983" if m.startswith("P") else "#2a78d6" for m in o.model])
ax[0].set(xlabel="leave-one-out RMSE of retention R", title="a) Prediction error (grey = physics, blue = data-driven)")
best = res.loc[res.LOO_RMSE.idxmin(), "model"]
ax[1].plot(y, preds["P0  physics: R = q (no fit)"], "s", mfc="white", color="#8a8983", ms=4, label="R = q (physics, no fit)")
ax[1].plot(y, preds[best], "o", color="#2a78d6", ms=4, label=best)
ax[1].plot([y.min(), y.max()], [y.min(), y.max()], "--", color="#52514e", lw=1)
ax[1].set(xlabel="R from CFD", ylabel="R predicted (case left out)", title="b) Physics baseline vs best model"); ax[1].legend(frameon=False, fontsize=7.5)
fig.savefig(os.path.join(here, "model_comparison.png"), dpi=170, bbox_inches="tight")
print("\nwrote model_comparison.csv, model_comparison.png")
