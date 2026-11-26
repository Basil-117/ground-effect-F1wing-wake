"""Plot CFD clean-air lift against ride height, with every wind-tunnel / reference dataset found.

Data files (columns h_c, CL; first line '# label: ...' is used for the legend):
  experiment_<case>*.csv      wind-tunnel data (case = single, double_datum, double_low, double_plus)
  reference_cfd_<case>*.csv   other people's CFD (e.g. Zerihan 2001 Fig. 75)
Empty files are skipped.  Output: validation_CL.png and a printed table of your CFD results."""
import os, sys, glob, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
here = os.path.dirname(os.path.abspath(__file__))
cfd_path = sys.argv[1] if len(sys.argv) > 1 else next((os.path.join(here, f) for f in
            ("results_validation_L1.csv", "results_validation.csv") if os.path.exists(os.path.join(here, f))), "results_validation.csv")
mesh_note = os.path.basename(cfd_path).replace("results_validation", "").replace(".csv", "").strip("_") or "L0"
cfd = pd.read_csv(cfd_path) if os.path.exists(cfd_path) else pd.DataFrame(columns=["config", "h_c", "CL"])
panels = [("single", "single", "Single element, reference incidence 1°", "h/c  (c = 223.4 mm)"),
          ("datum", "double_datum", "Two-element, datum (= high) flap", "h/c  (c = 380 mm)"),
          ("low", "double_low", "Two-element, low flap (datum - 8.5°)", "h/c  (c = 380 mm)"),
          ("plus", "double_plus", "Two-element, flap datum + 9.5°", "h/c  (c = 380 mm)")]
EXP_STYLE = [("s", "#eb6834"), ("^", "#4a3aa7"), ("D", "#1baf7a"), ("v", "#e87ba4")]
REF_STYLE = [("--", "#8a8983"), (":", "#52514e")]
def label_of(path):
    with open(path) as f:
        for line in f:
            if line.startswith("# label:"): return line.split(":", 1)[1].strip()
    return os.path.basename(path)
def load(path):
    d = pd.read_csv(path, comment="#").dropna()
    return d.sort_values("h_c") if len(d) else d
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e4e3de"})
fig, axs = plt.subplots(2, 2, figsize=(11, 8), gridspec_kw={"wspace": 0.25, "hspace": 0.35}); axs = axs.ravel()
for ax, (cfg, stem, title, xl) in zip(axs, panels):
    exps = sorted(glob.glob(os.path.join(here, f"experiment_{stem}*.csv")))
    exps.sort(key=lambda p: (p.count("_"), p))                       # main file first
    i = 0
    for p in exps:
        d = load(p)
        if not len(d): continue
        m, c = EXP_STYLE[i % len(EXP_STYLE)]; i += 1
        ax.plot(d.h_c, d.CL, m, color=c, ms=4.5, mfc="white", mew=1.3, ls="-", lw=0.6, label=label_of(p))
    for j, p in enumerate(sorted(glob.glob(os.path.join(here, f"reference_cfd_{stem}*.csv")))):
        d = load(p)
        if len(d):
            ls, c = REF_STYLE[j % len(REF_STYLE)]
            ax.plot(d.h_c, d.CL, ls, color=c, lw=1.4, label=label_of(p))
    d = cfd[cfd.config == cfg].sort_values("h_c")
    if len(d): ax.plot(d.h_c, d.CL, "o-", color="#2a78d6", ms=5, lw=2, label=f"This study, 2D CFD (mesh {mesh_note})", zorder=5)
    ax.set_title(title, fontsize=9.5, loc="left"); ax.set_xlabel(xl); ax.set_ylabel("Downforce coefficient C_L")
    if ax.has_data(): ax.legend(frameon=False, fontsize=7, loc="best")
out = os.path.join(here, "validation_CL.png"); fig.savefig(out, dpi=170, bbox_inches="tight"); print("wrote", out)
if len(cfd): print(cfd.sort_values(["config", "h_c"]).to_string(index=False))
