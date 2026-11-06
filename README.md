# SnakeGuard AI

Uncertainty-aware snakebite triage research prototype. It predicts the venom syndrome
(and likely species) from symptom progression, bite location/time and optional images,
**without needing a photo of the snake**, and reports when it is unsure.

> **Not a medical device.** This is a research prototype. It outputs triage classes only
> and must never be used for antivenom dosing or treatment decisions.
> All results from `src/data/simulator.py` are **simulation results** on synthetic patients.

See `CLAUDE.md` for the full research design.

## Setup (Windows, Python 3.11)

```bash
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
.venv/Scripts/python -m pip install -r requirements-dev.txt   # runtime + pyflakes, matplotlib
.venv/Scripts/python -m pyflakes src tests
.venv/Scripts/python -m pytest
```

(On Linux/macOS use `.venv/bin/python`. Drop the `--index-url` line to get a GPU build of torch.)

## Layout

```
data/raw/            # downloaded, never edited (git-ignored)
data/processed/      # git-ignored
knowledge/           # clinical_table.csv + sources.bib (every number cited)
src/data/            # downloaders, simulator, datasets
src/models/          # encoders, fusion, heads
src/uncertainty/     # conformal prediction
configs/             # YAML configs per experiment
notebooks/           # exploration only
tests/
```

## Clinical knowledge table

The knowledge base in `knowledge/` (loaded by `src/data/knowledge.py`):

| file | one row per | main columns |
|---|---|---|
| `symptoms.csv` | symptom in the controlled vocabulary | `marker` (neurotoxic / haemotoxic / local / none) |
| `species.csv` | species | `group` (venomous / non-venomous), `dry_bite_rate` |
| `clinical_table.csv` | (species, symptom) | `onset_min_hours`, `onset_max_hours`, `frequency` |
| `context_table.csv` | (species, feature) | `feature` (night / indoor / asleep), `probability` |
| `context_joint.csv` | (species, night, indoor, asleep) | `count` (complete cases, Wijayasekara 2026 raw data) |
| `onset_order.csv` | (species or `*`, before, after) | cited order of onset; cycles are rejected |
| `presentation_delay.csv` | (profile, delay bin) | `min_hours`, `max_hours` (blank = open), `proportion` |

Every numeric row also has `source_key` (one or more BibTeX keys from `sources.bib`,
separated by `;`), `evidence` (locator + short verbatim quote) and `verified` (true only
after a human has checked the number against the source PDF). Draft literature extractions
with quotes live in `knowledge/extraction/`.

Rows with `source_key=TODO` or blank numbers are placeholders and are skipped with a warning.
`load_knowledge(..., require_citations=True)` refuses uncited or blank rows, and
`require_verified=True` refuses unverified ones.

## Simulated data

```bash
python -m src.data.validate                              # schema, citations, onset orders, delay bins
python -m src.data.generate --config configs/sim_v2.yaml # primary, evidence-only dataset
```

Writes `patients.csv`, `events.csv`, `meta.json`, a sanity `report.md` (with a rule-based
syndromic baseline) and `onset_diagnostics.md` to `data/processed/sim_v2/`. `sim_v2` is the
primary dataset: it uses cited onset windows only (`experiment_type: primary`). Symptoms with a
cited frequency but no cited onset are label-only (`unknown_onset: label_only`): they count toward
the venom-syndrome label but have no onset time and are never part of the model input. Filling unknown
onsets with an assumed window (`onset_fallback`) is refused unless a config says
`experiment_type: sensitivity` (e.g. `configs/sim_v1.yaml`, kept as a labelled sensitivity
dataset). `meta.json` records the git commit, knowledge-file hashes, verified/unverified rows
per table and every simulation assumption in force. The venom syndrome label comes from each
patient's full symptom course, while the model only sees events up to presentation. All of this
is **simulation data**. See `docs/phase1_plan.md`.

Knowledge rows are AI-assisted drafts until checked by a person. To list what still needs checking:

```bash
python -m src.data.checklist   # writes docs/verification_checklist.md
python -m src.data.quotecheck  # checks quotes against open full texts -> docs/quote_check.md
```

Robustness and realism checks (all output is simulation data):

```bash
python -m src.data.sensitivity --config configs/sensitivity_v2.yaml   # 17 variants x 5 seeds, 95% CIs
python -m src.data.vignettes --dataset data/processed/sim_v2 --n 40 --out data/processed/review_v2
```

See `docs/clinician_review_protocol.md` for the blinded review.

CI (`.github/workflows/tests.yml`) runs `python -m src.data.validate` and the test suite on
every push and pull request.

## Phase 2: symptom-only baselines

```bash
python -m src.train --config configs/phase2_sim_v2.yaml                  # all models, calibration, threshold tables
python -m src.ablation --config configs/phase2_ablation_sim_v2.yaml      # input ablations A-I
python -m src.robustness --config configs/phase2_robustness_sim_v2.yaml  # imperfect symptom reporting
python -m src.explain --config configs/phase2_explain_sim_v2.yaml        # XGBoost / RF explanations
python -m src.seed_variability --config configs/phase2_simseed_sim_v2.yaml  # 5 simulator seeds x 3 model seeds
python -m src.evaluate --run outputs/phase2/sim_v2                       # recompute metrics from saved predictions
python -m src.verify_runs outputs/phase2/sim_v2                          # split, leakage and regeneration checks
```

Models: prior, rule-based table, XGBoost (with and without context), logistic regression,
random forest and the symptom transformer, all through one registry (`src/models/registry.py`).
Every model input passes a strict allowlist (`src/data/features.py`): observed symptoms with
onset times, presentation time and, where asked for, hour of day / indoor / asleep. Targets,
simulator diagnostics, placeholders and label-only or post-presentation events are refused,
and `tests/test_leakage.py` checks this by perturbing them and requiring identical inputs.
Learned models train on the `train` split (minus a validation subset for early stopping) over
3 model seeds. The `calibration` split is never used to fit or select models; it only fits the
post-hoc calibrators (temperature, Platt, isotonic; `src/uncertainty/calibration.py`), which are
evaluated on test next to the raw probabilities. `src/decision_policy.py` lists research-only
threshold tables for P(envenomed); they are **not** clinical thresholds.

Every run writes `run.json` (status, deterministic run id, git commit and dirty flag, simulator
and model seeds, dataset and knowledge hashes, feature allowlist and input columns, split
distributions, package versions) and `attempts.jsonl` (failures included), and refuses to overwrite
a completed run without `--overwrite` (`src/artifacts.py`). Splits are random by default;
`split_strategy: stratified` in a dataset config stratifies by species and syndrome with a logged
fallback for rare strata (`src/data/splits.py`). Reports go to `outputs/phase2/<run>/report.md`
(SIMULATION results). See `docs/phase2_results.md`, the audit in `docs/phase2_audit.md` and the
evidence audit of the label-only local signs in `docs/evidence_audit_local_signs.md`.

## Status

- [x] Phase 0: repo, environment, tests
- [x] Phase 1: clinical knowledge table + simulator (engineering done; rows await human verification,
      see docs/verification_checklist.md). GPS and month are uniform placeholders until Phase 3.
- [x] Phase 2: symptom-only baselines, software-validated and simulation-evaluated only (see
      docs/phase2_results.md); not clinically validated. Early local-sign onsets remain an evidence gap.
- [ ] Phase 3: geographic prior (GBIF)
- [ ] Phase 4: image branch (SnakeCLEF)
- [ ] Phase 5: missing-modality fusion
- [ ] Phase 6: conformal uncertainty gate + evaluation
- [ ] Phase 7: offline mobile export
