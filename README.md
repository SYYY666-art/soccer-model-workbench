# UPC 2026 Problem B · Penalty-Trajectory Prediction Workbench

[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)

An interactive, physics-based workbench for predicting a penalty-kick trajectory and its
goal-line crossing probability from two sparse observations of the ball center
(at $t_1 = 0.05$ s and $t_2 = 0.10$ s). Built for **UPC 2026, Problem B**.

> Live demo: https://<your-app>.streamlit.app (deployed via Streamlit Community Cloud)

## Overview

Given only the ball-center coordinates at two instants, the workbench inverts the
3-D flight dynamics and propagates observation and parameter uncertainty to the goal
plane. The pipeline follows the companion theory paper: data-diagnostic baselines (§2),
aerodynamic closures A/B/C (§4), constrained MAP inversion with SVD identifiability
diagnostics (§5), Monte Carlo event statistics and variance decomposition (§6), and
CFD-based model validation against COMSOL wind-tunnel data (§7).

### Model pipelines (shared interface, fair comparison)

| Pipeline | Aerodynamic closure | Inverted parameters |
|---|---|---|
| **A-1** | Fixed $C_D = 0.25$ + low-order effective spin $\Omega_\mathrm{eff}\times u$ | $v_0$ (3) + transverse $\Omega_\mathrm{eff}$ (2) |
| **A-2** | Same closure, $C_D$ inverted with lognormal prior | $v_0$ (3) + $\log C_D$ + transverse $\Omega_\mathrm{eff}$ (2) |
| **B** | Literature coefficient curves (Asai 2007 wind-tunnel fit; Goff & Carré 2009/2010) | $v_0$ (3) + transverse physical spin $\omega_\perp$ (2) |
| **C** | COMSOL anchor coefficient table (plateau-averaged from hand-off CFD data) | $v_0$ (3) + transverse physical spin $\omega_\perp$ (2) |

### Key features

- **Event-localized integration** — DOP853 with goal-plane and ground-contact events
  ($\mathrm{rtol}=10^{-8}$, $\mathrm{atol}=10^{-9}$)
- **Probabilistic prediction** — Monte Carlo + first-order sensitivity propagation;
  $P(\text{cross})$, $P(\text{goal}|\text{cross})$, $P(\text{ground})$ reported
  separately, no sample is silently discarded
- **Uncertainty visualization** — 95% joint confidence ellipse ($\chi^2_2 = 5.991$),
  50% joint region, highest-density region (HDR), possible-position cloud along the
  time axis
- **SVD identifiability diagnostics** — condition number $\kappa$ and parameter
  standard errors for every inversion
- **CFD cross-validation (§7)** — 2-D mesh-sensitivity analysis and 3-D zero/positive/
  negative-spin force histories from COMSOL, including a detected **reverse Magnus
  effect** and pressure-contribution decomposition
- **Bilingual UI** — rigorous academic phrasing in Chinese and English
- **Benchmark case library** — 6 presets (official data, in-swinging curve, knuckle
  drop, low drive, post-grazing limit case, straight power shot), freely editable

## Quick start (local)

```bat
:: Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app_main.py
```

or simply double-click `启动实验台.bat`.

## Repository layout

| Path | Content |
|---|---|
| `app_main.py` | Streamlit application |
| `physics_theory.py` | 3-D dynamics, A/B/C closures, MAP inversion, event integration |
| `uncertainty_engine.py` | Monte Carlo propagation, HDR/confidence ellipses, model envelope |
| `comsol_bridge.py` | COMSOL coefficient-map interface (pipeline C) |
| `comsol_lab.py` | Hand-off data parsing, CFD comparison, anchor-table generation |
| `visualizer_3d.py` | 3-D stadium and 2-D goal-plane rendering |
| `i18n.py` | Chinese/English interface text |
| `config.py` | Parameter specifications and benchmark cases |
| `validation_suite.py` | Synthetic-truth recovery tests (`python validation_suite.py`) |
| `data/` | COMSOL hand-off data and pipeline-C anchor table |
| `docs/` | Physics modeling notes, COMSOL delivery format, CFD comparison report |

## Deployment (Streamlit Community Cloud)

1. Push this repository to GitHub (public).
2. Visit [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. **New app** → select this repo → main file `app_main.py` → **Deploy**.
4. Share the generated `https://<app>.streamlit.app` link with reviewers.

## Data provenance

- `data/comsol_table.csv` — pipeline-C anchor table, plateau-averaged
  (0.024–0.040 s) from the COMSOL wind-tunnel force tables.
- `data/UPC2026_B_COMSOL_队友交接/` — COMSOL 6.4 exports (smooth sphere,
  $U_\infty = 31.46$ m/s, $\mathrm{Re} \approx 4.68\times10^5$, spin ratio
  $S = \pm 0.1748$).
- COMSOL force histories contain startup/restart artifacts at the first rows
  (Fx ≈ 204 N / 265 N); these are excluded before plateau averaging.

## Literature (pipeline B)

Pipeline B implements the aerodynamic coefficient curves from the literature:

- Asai, Seo, Kobayashi & Sakashita, *Sports Engineering* **10**, 101–110 (2007) —
  Teamgeist wind-tunnel drag data.
- Goff & Carré, *Am. J. Phys.* **77**, 1020–1027 (2009) — trajectory analysis,
  post-critical $C_D \approx 0.27$–0.30 for 32-panel balls.
- Goff & Carré, *Eur. J. Phys.* **31**, 775–784 (2010) — fitted
  $C_D(v) = a + b/[1 + \exp((v-v_c)/v_s)]$ with $a=0.155$, $b=0.346$,
  $v_c=12.19$ m/s, $v_s=1.309$ m/s ($\mathrm{Re}_c \approx 1.73\times10^5$);
  spin correction $C_D = c\,\mathrm{Sp}^d$ with $c=0.4127$, $d=0.3056$;
  $|C_L| \approx 0.8\,\mathrm{Sp}$ (linear region), saturating at 0.4 for
  $\mathrm{Sp} > 0.5$. Queries beyond the experimental domain
  ($\mathrm{Sp} > 0.3$ for $C_D$, $\mathrm{Sp} > 1$ overall) are flagged
  as extrapolation.

## Citation / team

UPC 2026 Problem B — team simulation bench. Theory companion document and COMSOL
wind-tunnel computations were produced by the team's theory and CFD members.
