# Ground-effect wing in a wake: validated 2D CFD and surrogate models

Code, inputs and results for the preprint *"Downforce loss of a ground-effect wing in a wake is a dynamic-pressure
effect: validated 2D CFD and a comparison of surrogate models"* (Mehmood, 2026), preprint doi:[10.5281/zenodo.24552176](https://doi.org/10.5281/zenodo.24552176).

**Main result.** A ground-effect wing in a wake keeps its clean-air lift coefficient based on the dynamic pressure it
actually meets (median retention / dynamic-pressure ratio 0.995 over 52 wake cases). Ride height (h/c 0.2-0.5) and
wake width hardly matter; wake turbulence adds 4-9 % downforce. A Gaussian-process surrogate predicts retention with a
leave-one-out RMSE of 0.007.

Everything runs on a laptop (4 cores): OpenFOAM (native or in Docker) + Python.

## Layout
| folder | contents |
|---|---|
| `geometry/` | how to supply the Zerihan (2001) wing coordinates (not redistributed; see `geometry/README.md`) |
| `cfd2d/` | single-element wing: gmsh mesh (`mesh.py`), case writer with the parametric wake inlet (`make_case.py`), runner (`run_case.sh`), pressure-force integration (`forces.py`), empty-domain probe (`probe.py`), campaign design / runner / analysis (`doe_campaign.py`, `run_campaign.sh`, `analyse_campaign.py`), surrogate comparison (`compare_models.py`) |
| `validation/` | clean-air validation sweep, convergence check, mesh-independence (GCI) study. The comparison data digitised from Zerihan (2001) are not redistributed; `plot_validation.py` uses any `experiment_*.csv` / `reference_cfd_*.csv` you place here (columns `h_c,CL`) |
| `frontwing2d/` | two-element wing (used only for the trend check reported in the limitations) |
| `results/` | the result tables behind every number in the paper |
| `paper/` | LaTeX source, figures, and `figs.py`, which rebuilds every figure from `results/` |

## Quick start (Ubuntu or WSL)
```bash
bash setup_wsl.sh        # Python environment + gmsh libraries; finds an OpenFOAM Docker image or native install
bash smoke_test.sh       # one short CFD case: checks the tool chain
./foam.sh --info         # shows which OpenFOAM is used
```

## Reproducing the paper
```bash
cd validation && MESH_LEVEL=1 NPAR=3 bash run_validation.sh single && python3 plot_validation.py   # ~2 h
bash run_mesh_study.sh single && python3 gci.py                                                     # ~6-10 h
cd ../cfd2d && bash run_campaign.sh all                                                             # 56 cases, ~16 h
DESIGN=checks.csv  OUT=results_checks.csv  bash run_campaign.sh all                                 # wake width, length scale
DESIGN=checks2.csv OUT=results_checks2.csv ITERS=4000 bash run_campaign.sh all                      # 4000-iteration check
python3 analyse_campaign.py && python3 compare_models.py
cd ../paper && python3 figs.py
```
`figs.py` reads `results/`; Figures 1(b,c) and 3 also need the three OpenFOAM cases `val_single_h0.224_L1`,
`cmp_o01` and `chk_TI10_L05_4k` (copy them into `flow_cases/`, or set `FLOW_DIR`).

## Notes
- Forces are integrated from wall pressure (pressure drag only). Downforce is reported as positive C_L.
- The wing coordinates and the comparison data come from Zerihan's thesis (eprints.soton.ac.uk/426058), which is
  under the University of Southampton Thesis Licence, so they are not included. Figure 2 of the paper therefore
  cannot be rebuilt from this repository alone; all CFD results are included.
- Tested with OpenFOAM v2512 (opencfd Docker image) and Ubuntu's openfoam 1912 package.

## Citation
See `CITATION.cff`. Please also cite Zerihan (2001) and Zerihan & Zhang (2000) when using the geometry or the
experimental data.

## Licence
Code: MIT (see `LICENSE`). CFD result tables: CC BY 4.0. Figures that show Zerihan's data reproduce digitised
values from his thesis for comparison, with citation.
